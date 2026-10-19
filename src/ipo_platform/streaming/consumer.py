"""
Idempotent CDC Kafka Consumer Pipeline for Indian IPO Platform.
Processes Debezium change data capture streams with strict deduplication,
transient retry mechanics, poison message quarantine, and graceful shutdown.
"""

from collections import deque
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set

from ipo_platform.streaming.cdc_event import (
    CDCEvent,
    CDCEventOperation,
    CDCPayloadError,
    parse_cdc_event,
)

logger = logging.getLogger(__name__)


class DeduplicationStore:
    """Interface for idempotency state tracking."""

    def exists_and_add(self, key: str, ttl_seconds: int = 86400) -> bool:
        """Returns True if key was already seen, otherwise adds it and returns False."""
        raise NotImplementedError


class InMemoryDeduplicationStore(DeduplicationStore):
    """Sliding-window in-memory deduplication store for event deduplication."""

    def __init__(self, capacity: int = 10000) -> None:
        self.capacity = capacity
        self._keys: Set[str] = set()
        self._queue: deque[str] = deque()

    def exists_and_add(self, key: str, ttl_seconds: int = 86400) -> bool:
        if key in self._keys:
            return True
        if len(self._keys) >= self.capacity:
            oldest = self._queue.popleft()
            self._keys.discard(oldest)
        self._keys.add(key)
        self._queue.append(key)
        return False

    def clear(self) -> None:
        self._keys.clear()
        self._queue.clear()


class IdempotentCDCConsumer:
    """
    Idempotent CDC Consumer that processes MySQL Debezium events from Kafka topics.
    Guarantees:
    - At-least-once to effectively exactly-once transformation via idempotency keying
    - Poison message quarantine to Dead-Letter Queue (DLQ)
    - Automatic exponential backoff retries for transient failures
    - Table-level handler routing (ipo_master, gmp, subscription, financials)
    """

    def __init__(
        self,
        dedup_store: Optional[DeduplicationStore] = None,
        max_retries: int = 3,
        base_retry_delay_seconds: float = 0.05,
    ) -> None:
        self.dedup_store = dedup_store or InMemoryDeduplicationStore()
        self.max_retries = max_retries
        self.base_retry_delay = base_retry_delay_seconds

        # Dispatch table for table handlers
        self._handlers: Dict[str, List[Callable[[CDCEvent], None]]] = {}

        # Quarantine / DLQ store for diagnostics
        self.quarantined_messages: List[Dict[str, Any]] = []

        # Metrics
        self.processed_count = 0
        self.duplicate_count = 0
        self.quarantine_count = 0
        self.retry_count = 0

        # Running state
        self._is_running = True

    def register_handler(self, table: str, handler: Callable[[CDCEvent], None]) -> None:
        """Registers a custom downstream handler for changes to a specific table."""
        self._handlers.setdefault(table, []).append(handler)

    def stop(self) -> None:
        """Signals the consumer to gracefully stop."""
        self._is_running = False

    def process_raw_message(
        self,
        value: Any,
        key: Any = None,
    ) -> bool:
        """
        Ingests and processes a single raw Kafka message (key + value).
        Returns True if event was successfully applied or deduplicated; False if quarantined.
        """
        # Step 1: Parse and validate envelope
        try:
            event = parse_cdc_event(message_value=value, message_key=key)
        except CDCPayloadError as err:
            logger.error(f"Malformed CDC message rejected to DLQ: {err}")
            self.quarantined_messages.append({
                "error": str(err),
                "payload": value,
                "timestamp": time.time(),
            })
            self.quarantine_count += 1
            return False

        # Step 2: Idempotency check
        if self.dedup_store.exists_and_add(event.idempotency_key):
            logger.debug(f"Duplicate event ignored: {event.idempotency_key}")
            self.duplicate_count += 1
            return True

        # Step 3: Dispatch to table handlers with retry
        success = self._dispatch_with_retry(event)
        if success:
            self.processed_count += 1
            return True
        else:
            self.quarantined_messages.append({
                "error": "Max retries exceeded during downstream processing",
                "event": event,
                "payload": value,
                "timestamp": time.time(),
            })
            self.quarantine_count += 1
            return False

    def _dispatch_with_retry(self, event: CDCEvent) -> bool:
        """Executes table handlers with exponential backoff on transient errors."""
        handlers = self._handlers.get(event.table, [])
        if not handlers:
            # No registered handler is a successful no-op
            return True

        for handler in handlers:
            attempt = 0
            while attempt < self.max_retries:
                try:
                    handler(event)
                    break
                except Exception as exc:
                    attempt += 1
                    self.retry_count += 1
                    if attempt >= self.max_retries:
                        logger.error(
                            f"Fatal error handling event for table {event.table} after {attempt} attempts: {exc}"
                        )
                        return False
                    sleep_time = self.base_retry_delay * (2 ** (attempt - 1))
                    logger.warning(
                        f"Transient failure in handler for {event.table}: {exc}. Retrying in {sleep_time:.3f}s (attempt {attempt}/{self.max_retries})"
                    )
                    time.sleep(sleep_time)

        return True


class KafkaCDCWorker:
    """
    Background worker daemon that subscribes to Kafka CDC topics, polls incoming messages,
    and dispatches them to an IdempotentCDCConsumer with offset tracking.
    Works with confluent-kafka, kafka-python, or mock test polling providers.
    """

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "ipo-platform-cdc-worker",
        topics: Optional[List[str]] = None,
        consumer: Optional[IdempotentCDCConsumer] = None,
        auto_offset_reset: str = "earliest",
        custom_poll_fn: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.topics = topics or [
            "ipo_cdc.ipo_db.ipo_master",
            "ipo_cdc.ipo_db.gmp",
            "ipo_cdc.ipo_db.subscription",
            "ipo_cdc.ipo_db.financials",
        ]
        self.consumer = consumer or IdempotentCDCConsumer()
        self.auto_offset_reset = auto_offset_reset
        self.custom_poll_fn = custom_poll_fn
        self._is_running = False
        self._raw_kafka_consumer: Any = None

    def initialize_client(self) -> bool:
        """
        Initializes underlying Kafka consumer client if library is installed.
        Returns True if a real client was initialized, False otherwise.
        """
        if self.custom_poll_fn:
            return True

        # Try confluent_kafka
        try:
            from confluent_kafka import Consumer as ConfluentConsumer
            conf = {
                "bootstrap.servers": self.bootstrap_servers,
                "group.id": self.group_id,
                "auto.offset.reset": self.auto_offset_reset,
                "enable.auto.commit": False,
            }
            self._raw_kafka_consumer = ConfluentConsumer(conf)
            self._raw_kafka_consumer.subscribe(self.topics)
            logger.info("Initialized confluent-kafka consumer for topics: %s", self.topics)
            return True
        except ImportError:
            pass

        # Try kafka-python
        try:
            import json
            from kafka import KafkaConsumer
            self._raw_kafka_consumer = KafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=False,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )
            logger.info("Initialized kafka-python consumer for topics: %s", self.topics)
            return True
        except ImportError:
            pass
        except Exception as exc:
            logger.warning(
                "Could not establish connection to Kafka brokers (%s): %s. Operating in simulated mode.",
                self.bootstrap_servers,
                exc,
            )
            self._raw_kafka_consumer = None
            return False

        logger.warning(
            "Neither confluent-kafka nor kafka-python is installed. "
            "KafkaCDCWorker will operate in simulated poll mode."
        )
        return False

    def poll_once(self, timeout_seconds: float = 1.0) -> int:
        """
        Polls a batch or single message and dispatches it through the IdempotentCDCConsumer.
        Returns the number of messages processed in this poll cycle.
        """
        if self.custom_poll_fn:
            items = self.custom_poll_fn(timeout_seconds)
            count = 0
            for item in (items if isinstance(items, list) else [items]):
                if item is not None:
                    val = item.get("value") if isinstance(item, dict) else item
                    k = item.get("key") if isinstance(item, dict) else None
                    if self.consumer.process_raw_message(val, key=k):
                        count += 1
            return count

        if self._raw_kafka_consumer is None:
            self.initialize_client()

        if self._raw_kafka_consumer is None:
            return 0

        # Confluent consumer path
        if hasattr(self._raw_kafka_consumer, "poll"):
            msg = self._raw_kafka_consumer.poll(timeout=timeout_seconds)
            if msg is None:
                return 0
            if msg.error():
                logger.error("Kafka consumer error: %s", msg.error())
                return 0
            try:
                import json
                val = json.loads(msg.value().decode("utf-8"))
                k = msg.key().decode("utf-8") if msg.key() else None
                success = self.consumer.process_raw_message(val, key=k)
                if success:
                    self._raw_kafka_consumer.commit(msg, asynchronous=False)
                return 1
            except Exception as exc:
                logger.error("Error processing confluent kafka message: %s", exc)
                return 0

        return 0

    def run_loop(self, max_iterations: Optional[int] = None) -> None:
        """
        Runs the continuous consumption loop until stop() is called or max_iterations reached.
        """
        self._is_running = True
        iterations = 0
        logger.info("Starting KafkaCDCWorker polling loop on topics %s", self.topics)
        try:
            while self._is_running:
                self.poll_once(timeout_seconds=0.5)
                iterations += 1
                if max_iterations and iterations >= max_iterations:
                    break
        finally:
            self._is_running = False

    def stop(self) -> None:
        """Stops the worker polling loop and closes the underlying consumer connection."""
        self._is_running = False
        if self._raw_kafka_consumer:
            try:
                self._raw_kafka_consumer.close()
            except Exception as err:
                logger.debug("Note during Kafka consumer close: %s", err)
            self._raw_kafka_consumer = None
