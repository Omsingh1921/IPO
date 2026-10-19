"""
Unit and Contract Tests for Kafka / Debezium CDC Pipeline.
Validates event serialization, key extraction, idempotency deduplication,
transient retry mechanisms, poison message quarantine, and connector configuration.
"""

import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from ipo_platform.streaming.cdc_event import (
    CDCEvent,
    CDCEventOperation,
    CDCPayloadError,
    parse_cdc_event,
)
from ipo_platform.streaming.consumer import (
    IdempotentCDCConsumer,
    InMemoryDeduplicationStore,
)
from ipo_platform.streaming.cdc_manager import (
    DebeziumConnectorManager,
    DebeziumManagerError,
)


class TestKafkaCDC(unittest.TestCase):
    def setUp(self):
        self.sample_debezium_insert = {
            "schema": {"type": "struct", "fields": []},
            "payload": {
                "before": None,
                "after": {
                    "id": 101,
                    "ipo_id": "TEST-CDC-001",
                    "company_name": "CDC Enterprise Ltd",
                    "status": "Currently Open",
                    "issue_size": 500.0,
                },
                "source": {
                    "version": "2.5.4.Final",
                    "connector": "mysql",
                    "name": "ipo_cdc",
                    "ts_ms": 1728900000000,
                    "db": "ipo_db",
                    "table": "ipo_master",
                    "server_id": 101,
                    "file": "mysql-bin.000003",
                    "pos": 15420,
                    "row": 0,
                },
                "op": "c",
                "ts_ms": 1728900000100,
                "transaction": None,
            },
        }

        self.sample_debezium_update = {
            "payload": {
                "before": {
                    "id": 101,
                    "ipo_id": "TEST-CDC-001",
                    "status": "Currently Open",
                },
                "after": {
                    "id": 101,
                    "ipo_id": "TEST-CDC-001",
                    "status": "Closed",
                },
                "source": {
                    "db": "ipo_db",
                    "table": "ipo_master",
                    "file": "mysql-bin.000003",
                    "pos": 15990,
                    "ts_ms": 1728900010000,
                },
                "op": "u",
            }
        }

        self.sample_debezium_delete = {
            "payload": {
                "before": {
                    "id": 101,
                    "ipo_id": "TEST-CDC-001",
                },
                "after": None,
                "source": {
                    "db": "ipo_db",
                    "table": "ipo_master",
                    "file": "mysql-bin.000003",
                    "pos": 16500,
                    "ts_ms": 1728900020000,
                },
                "op": "d",
            }
        }

    def test_parse_cdc_insert_event(self):
        event = parse_cdc_event(self.sample_debezium_insert)
        self.assertEqual(event.operation, CDCEventOperation.CREATE)
        self.assertEqual(event.table, "ipo_master")
        self.assertEqual(event.database, "ipo_db")
        self.assertEqual(event.business_key, "TEST-CDC-001")
        self.assertTrue(event.is_create)
        self.assertFalse(event.is_update)
        self.assertFalse(event.is_delete)
        self.assertEqual(event.current_data["company_name"], "CDC Enterprise Ltd")
        self.assertIn("mysql-bin.000003:15420", event.idempotency_key)

    def test_parse_cdc_update_event(self):
        event = parse_cdc_event(self.sample_debezium_update)
        self.assertEqual(event.operation, CDCEventOperation.UPDATE)
        self.assertTrue(event.is_update)
        self.assertEqual(event.before["status"], "Currently Open")
        self.assertEqual(event.after["status"], "Closed")
        self.assertEqual(event.current_data["status"], "Closed")

    def test_parse_cdc_delete_event(self):
        event = parse_cdc_event(self.sample_debezium_delete)
        self.assertEqual(event.operation, CDCEventOperation.DELETE)
        self.assertTrue(event.is_delete)
        self.assertIsNone(event.after)
        self.assertEqual(event.current_data["ipo_id"], "TEST-CDC-001")

    def test_parse_cdc_json_string(self):
        json_str = json.dumps(self.sample_debezium_insert)
        event = parse_cdc_event(json_str)
        self.assertEqual(event.business_key, "TEST-CDC-001")

    def test_parse_malformed_cdc_payload_raises(self):
        with self.assertRaises(CDCPayloadError):
            parse_cdc_event(None)

        with self.assertRaises(CDCPayloadError):
            parse_cdc_event("{malformed json string:")

        with self.assertRaises(CDCPayloadError):
            parse_cdc_event({"missing_op": True})

        with self.assertRaises(CDCPayloadError):
            parse_cdc_event({"op": "invalid_operation_code"})

    def test_idempotent_consumer_deduplication(self):
        dedup_store = InMemoryDeduplicationStore(capacity=100)
        consumer = IdempotentCDCConsumer(dedup_store=dedup_store)

        handled_events = []
        consumer.register_handler("ipo_master", lambda ev: handled_events.append(ev))

        # First consumption -> handled
        result1 = consumer.process_raw_message(self.sample_debezium_insert)
        self.assertTrue(result1)
        self.assertEqual(len(handled_events), 1)
        self.assertEqual(consumer.processed_count, 1)
        self.assertEqual(consumer.duplicate_count, 0)

        # Duplicate consumption (same binlog coordinates) -> deduplicated, no duplicate handler call
        result2 = consumer.process_raw_message(self.sample_debezium_insert)
        self.assertTrue(result2)
        self.assertEqual(len(handled_events), 1)
        self.assertEqual(consumer.processed_count, 1)
        self.assertEqual(consumer.duplicate_count, 1)

    def test_poison_message_quarantine_to_dlq(self):
        consumer = IdempotentCDCConsumer()
        poison_payload = {"invalid": "missing_op_and_fields"}

        result = consumer.process_raw_message(poison_payload)
        self.assertFalse(result)
        self.assertEqual(consumer.quarantine_count, 1)
        self.assertEqual(len(consumer.quarantined_messages), 1)
        self.assertIn("missing required 'op'", consumer.quarantined_messages[0]["error"])

    def test_transient_retry_and_eventual_success(self):
        consumer = IdempotentCDCConsumer(max_retries=3, base_retry_delay_seconds=0.01)

        attempts = 0

        def flaky_handler(event: CDCEvent):
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ConnectionError("Transient database lock timeout")

        consumer.register_handler("ipo_master", flaky_handler)

        result = consumer.process_raw_message(self.sample_debezium_insert)
        self.assertTrue(result)
        self.assertEqual(attempts, 2)
        self.assertEqual(consumer.retry_count, 1)
        self.assertEqual(consumer.processed_count, 1)

    def test_max_retries_exhaustion_quarantines(self):
        consumer = IdempotentCDCConsumer(max_retries=3, base_retry_delay_seconds=0.01)

        def perpetually_failing_handler(event: CDCEvent):
            raise RuntimeError("Irrecoverable downstream error")

        consumer.register_handler("ipo_master", perpetually_failing_handler)

        result = consumer.process_raw_message(self.sample_debezium_insert)
        self.assertFalse(result)
        self.assertEqual(consumer.quarantine_count, 1)
        self.assertEqual(consumer.retry_count, 3)

    def test_connector_config_file_validity(self):
        cfg_path = Path("config/debezium-mysql-connector.json")
        self.assertTrue(cfg_path.exists(), "Connector configuration file must exist")

        loaded = DebeziumConnectorManager.load_connector_config(str(cfg_path))
        self.assertEqual(loaded["name"], "ipo-mysql-cdc-connector")
        cfg = loaded["config"]
        self.assertEqual(cfg["connector.class"], "io.debezium.connector.mysql.MySqlConnector")
        self.assertEqual(cfg["topic.prefix"], "ipo_cdc")
        self.assertIn("ipo_db.ipo_master", cfg["table.include.list"])
        self.assertEqual(cfg["snapshot.mode"], "initial")
        self.assertEqual(cfg["schema.history.internal.kafka.bootstrap.servers"], "kafka:9092")

    @patch("urllib.request.urlopen")
    def test_debezium_connector_manager_mock_health(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps(["ipo-mysql-cdc-connector"]).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        mgr = DebeziumConnectorManager("http://localhost:8083")
        health = mgr.check_health()
        self.assertEqual(health["status"], "HEALTHY")
        self.assertIn("ipo-mysql-cdc-connector", health["connectors"])


if __name__ == "__main__":
    unittest.main()
