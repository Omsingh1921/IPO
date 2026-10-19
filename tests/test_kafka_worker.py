"""
Unit tests for KafkaCDCWorker daemon and polling loop.
"""

import unittest
from ipo_platform.streaming.consumer import IdempotentCDCConsumer, KafkaCDCWorker


class TestKafkaCDCWorker(unittest.TestCase):
    """Test suite validating Kafka CDC background polling worker."""

    def test_worker_initialization(self):
        worker = KafkaCDCWorker(
            bootstrap_servers="localhost:9092",
            group_id="test-group",
            topics=["ipo_cdc.ipo_db.ipo_master"],
        )
        self.assertEqual(worker.bootstrap_servers, "localhost:9092")
        self.assertEqual(worker.group_id, "test-group")
        self.assertEqual(worker.topics, ["ipo_cdc.ipo_db.ipo_master"])
        # Should initialize gracefully even when Kafka broker is offline
        self.assertFalse(worker._is_running)

    def test_worker_custom_poll_fn_dispatch(self):
        consumer = IdempotentCDCConsumer()
        received_events = []
        consumer.register_handler("ipo_master", lambda ev: received_events.append(ev))

        sample_message = {
            "value": {
                "before": None,
                "after": {"ipo_id": "IPO-KAFKA-WORKER-001", "company_name": "Worker Tech Ltd"},
                "source": {
                    "version": "2.5.4.Final",
                    "connector": "mysql",
                    "name": "ipo_cdc",
                    "ts_ms": 1729000000000,
                    "db": "ipo_db",
                    "table": "ipo_master",
                    "server_id": 101,
                    "file": "mysql-bin.000001",
                    "pos": 10500,
                    "row": 0,
                },
                "op": "c",
                "ts_ms": 1729000000000,
            },
            "key": {"ipo_id": "IPO-KAFKA-WORKER-001"},
        }

        worker = KafkaCDCWorker(
            consumer=consumer,
            custom_poll_fn=lambda timeout: [sample_message],
        )

        processed = worker.poll_once(timeout_seconds=0.1)
        self.assertEqual(processed, 1)
        self.assertEqual(consumer.processed_count, 1)
        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].after["company_name"], "Worker Tech Ltd")

        # Re-polling same message triggers deduplication
        dup_processed = worker.poll_once(timeout_seconds=0.1)
        self.assertEqual(dup_processed, 1)
        self.assertEqual(consumer.duplicate_count, 1)
        self.assertEqual(len(received_events), 1)  # handler not re-executed

    def test_worker_run_loop_max_iterations(self):
        counter = {"polls": 0}

        def mock_poll(timeout):
            counter["polls"] += 1
            return []

        worker = KafkaCDCWorker(custom_poll_fn=mock_poll)
        worker.run_loop(max_iterations=3)
        self.assertEqual(counter["polls"], 3)
        self.assertFalse(worker._is_running)


if __name__ == "__main__":
    unittest.main()
