"""
Streaming and Change Data Capture (CDC) package for Indian IPO Platform.
Provides Debezium MySQL CDC event modeling, idempotent consumer pipeline,
and Kafka Connect management client.
"""

from ipo_platform.streaming.cdc_event import (
    CDCEvent,
    CDCEventOperation,
    CDCPayloadError,
    parse_cdc_event,
)
from ipo_platform.streaming.consumer import (
    IdempotentCDCConsumer,
    InMemoryDeduplicationStore,
    KafkaCDCWorker,
)
from ipo_platform.streaming.cdc_manager import (
    DebeziumConnectorManager,
)

__all__ = [
    "CDCEvent",
    "CDCEventOperation",
    "CDCPayloadError",
    "parse_cdc_event",
    "IdempotentCDCConsumer",
    "InMemoryDeduplicationStore",
    "KafkaCDCWorker",
    "DebeziumConnectorManager",
]
