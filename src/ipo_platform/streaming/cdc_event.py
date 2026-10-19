"""
Debezium MySQL CDC Event Envelope and Parsing Models.
Normalizes Debezium row change events into standardized domain envelopes.
"""

from dataclasses import dataclass, field
from enum import Enum
import json
from typing import Any, Dict, Optional, Union


class CDCPayloadError(Exception):
    """Raised when a CDC message envelope is malformed or invalid."""
    pass


class CDCEventOperation(str, Enum):
    """Debezium CDC operation codes."""
    READ = "r"      # Initial snapshot read
    CREATE = "c"    # Insert
    UPDATE = "u"    # Update
    DELETE = "d"    # Delete
    TRUNCATE = "t"  # Truncate


@dataclass
class CDCEvent:
    """Standardized representation of a Debezium CDC change event."""
    operation: CDCEventOperation
    table: str
    database: str
    before: Optional[Dict[str, Any]]
    after: Optional[Dict[str, Any]]
    source_timestamp_ms: int
    binlog_file: Optional[str]
    binlog_pos: Optional[int]
    business_key: str
    idempotency_key: str
    raw_payload: Dict[str, Any] = field(repr=False, default_factory=dict)

    @property
    def is_create(self) -> bool:
        return self.operation in (CDCEventOperation.CREATE, CDCEventOperation.READ)

    @property
    def is_update(self) -> bool:
        return self.operation == CDCEventOperation.UPDATE

    @property
    def is_delete(self) -> bool:
        return self.operation == CDCEventOperation.DELETE

    @property
    def current_data(self) -> Dict[str, Any]:
        """Returns the current state (after for creates/updates, before for deletes)."""
        if self.is_delete:
            return self.before or {}
        return self.after or {}


def parse_cdc_event(
    message_value: Union[str, bytes, Dict[str, Any]],
    message_key: Optional[Union[str, bytes, Dict[str, Any]]] = None,
) -> CDCEvent:
    """
    Parses a Debezium Kafka message into a structured CDCEvent instance.
    Handles un-wrapped JSONConverter payloads and schema-wrapped Debezium envelopes.
    """
    if message_value is None:
        raise CDCPayloadError("Empty or tombstone CDC event payload")

    if isinstance(message_value, (str, bytes)):
        try:
            payload = json.loads(message_value)
        except Exception as err:
            raise CDCPayloadError(f"Malformed JSON in CDC event: {err}") from err
    elif isinstance(message_value, dict):
        payload = message_value
    else:
        raise CDCPayloadError(f"Unsupported payload type: {type(message_value)}")

    # Handle Debezium wrapper {"schema": ..., "payload": ...} if present
    data = payload.get("payload", payload) if isinstance(payload, dict) else payload

    if not isinstance(data, dict):
        raise CDCPayloadError(f"Expected dict data in CDC payload, got {type(data)}")

    op_raw = data.get("op")
    if not op_raw:
        raise CDCPayloadError("CDC payload missing required 'op' field")

    try:
        operation = CDCEventOperation(str(op_raw).lower())
    except ValueError:
        raise CDCPayloadError(f"Unrecognized CDC operation code: '{op_raw}'")

    source_info = data.get("source") or {}
    table = source_info.get("table", "unknown_table")
    database = source_info.get("db", "unknown_db")
    binlog_file = source_info.get("file")
    binlog_pos = source_info.get("pos")
    source_ts = source_info.get("ts_ms", 0)

    before = data.get("before")
    after = data.get("after")

    # Extract business key
    key_dict: Dict[str, Any] = {}
    if message_key is not None:
        if isinstance(message_key, (str, bytes)):
            try:
                key_dict = json.loads(message_key)
            except Exception:
                pass
        elif isinstance(message_key, dict):
            key_dict = message_key.get("payload", message_key)

    # Resolve business key: priority to ipo_id, then id, then message key
    business_key = ""
    candidate_record = after or before or {}
    if isinstance(candidate_record, dict):
        if "ipo_id" in candidate_record:
            business_key = str(candidate_record["ipo_id"])
        elif "id" in candidate_record:
            business_key = str(candidate_record["id"])

    if not business_key and key_dict:
        business_key = str(key_dict.get("ipo_id") or key_dict.get("id") or "unknown_key")

    if not business_key:
        business_key = "anonymous"

    # Monotonic idempotency key: database:table:binlog_file:binlog_pos:op:key
    idempotency_key = f"{database}:{table}:{binlog_file or 'nofile'}:{binlog_pos or 0}:{operation.value}:{business_key}"

    return CDCEvent(
        operation=operation,
        table=table,
        database=database,
        before=before,
        after=after,
        source_timestamp_ms=source_ts,
        binlog_file=binlog_file,
        binlog_pos=binlog_pos,
        business_key=business_key,
        idempotency_key=idempotency_key,
        raw_payload=payload,
    )
