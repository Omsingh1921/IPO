"""
Base Contracts, Resiliency Primitives, and Data Structures for Upstream IPO Data Source Adapters.
Defines abstract BaseSourceAdapter, CircuitBreaker, TokenBucketRateLimiter, and AdapterSyncResult.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from ipo_platform.models.schema import GMPData, MasterIPORecord

logger = logging.getLogger(__name__)


@dataclass
class AdapterSyncResult:
    """Standardized summary of an adapter synchronization run."""
    source_name: str
    records_fetched: int = 0
    records_parsed: int = 0
    records_valid: int = 0
    errors: List[str] = field(default_factory=list)
    master_records: List[MasterIPORecord] = field(default_factory=list)
    gmp_quotes: List[Tuple[str, GMPData]] = field(default_factory=list)  # (ipo_id, GMPData)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    @property
    def is_successful(self) -> bool:
        return len(self.errors) == 0 or self.records_valid > 0


class CircuitBreakerState(Enum):
    """Operational states of the circuit breaker."""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenError(Exception):
    """Raised when an execution is attempted while the circuit breaker is OPEN."""
    pass


class CircuitBreaker:
    """
    Thread-safe Circuit Breaker protection for external upstream data calls.
    Prevents cascading service degradation by fast-failing during outages.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 30.0,
        expected_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.expected_exceptions = expected_exceptions
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    def can_execute(self) -> bool:
        """Determines if a request should be allowed through."""
        with self._lock:
            if self.state == CircuitBreakerState.CLOSED:
                return True
            now = time.time()
            if self.state == CircuitBreakerState.OPEN:
                if self.last_failure_time and (now - self.last_failure_time >= self.recovery_timeout_seconds):
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info("Circuit breaker transitioning to HALF_OPEN probe state.")
                    return True
                return False
            if self.state == CircuitBreakerState.HALF_OPEN:
                return True
            return False

    def record_success(self) -> None:
        """Resets the breaker to CLOSED upon successful probe/execution."""
        with self._lock:
            self.failure_count = 0
            self.state = CircuitBreakerState.CLOSED
            self.last_failure_time = None

    def record_failure(self) -> None:
        """Increments failure count and trips to OPEN if threshold reached."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold or self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.OPEN
                logger.warning(
                    "Circuit breaker TRIPPED to OPEN state. Failures: %d, Threshold: %d",
                    self.failure_count,
                    self.failure_threshold,
                )

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Executes a callable under circuit breaker surveillance."""
        if not self.can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit breaker is OPEN. Fast-failing upstream call (last failure: {self.last_failure_time})."
            )
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exceptions as exc:
            self.record_failure()
            raise exc


class TokenBucketRateLimiter:
    """In-memory rate limiter using token bucket algorithm."""

    def __init__(self, requests_per_second: float = 2.0, max_tokens: float = 5.0) -> None:
        self.rate = requests_per_second
        self.capacity = max_tokens
        self.tokens = max_tokens
        self.last_update = time.time()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

            if self.tokens < 1.0:
                sleep_time = (1.0 - self.tokens) / self.rate
                time.sleep(sleep_time)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0


def execute_with_retry(
    func: Callable[..., Any],
    max_retries: int = 3,
    initial_delay: float = 0.05,
    backoff_factor: float = 2.0,
    circuit_breaker: Optional[CircuitBreaker] = None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Executes a callable with exponential backoff retries and optional circuit breaker surveillance.
    """
    attempt = 0
    delay = initial_delay

    while True:
        try:
            if circuit_breaker:
                return circuit_breaker.call(func, *args, **kwargs)
            return func(*args, **kwargs)
        except CircuitBreakerOpenError:
            # Circuit breaker fast-fails immediately without retries
            raise
        except Exception as exc:
            attempt += 1
            if attempt > max_retries:
                logger.error("Exceeded maximum retries (%d) for operation: %s", max_retries, exc)
                raise
            logger.warning(
                "Attempt %d/%d failed with error: %s. Retrying in %.3fs...",
                attempt,
                max_retries,
                exc,
                delay,
            )
            time.sleep(delay)
            delay *= backoff_factor


class BaseSourceAdapter(ABC):
    """
    Abstract Base Class for external exchange and market data adapters.
    Implements rate limiting, retry semantics, timeout handling, circuit breaking,
    and standardized fetch(), validate(), transform(), and health_check() contracts.
    """

    def __init__(
        self,
        source_name: str,
        base_url: str = "",
        timeout_seconds: float = 10.0,
        requests_per_second: float = 2.0,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self.source_name = source_name
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.rate_limiter = TokenBucketRateLimiter(requests_per_second=requests_per_second)
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=3,
            recovery_timeout_seconds=30.0,
        )

    @abstractmethod
    def fetch(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieves raw data items from the upstream source."""
        pass

    @abstractmethod
    def validate(self, raw_item: Dict[str, Any]) -> bool:
        """Validates payload schema, required fields, and boundary constraints."""
        pass

    @abstractmethod
    def transform(self, raw_item: Dict[str, Any]) -> Optional[Union[MasterIPORecord, Tuple[str, GMPData]]]:
        """Transforms a validated raw dictionary into a domain model."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Checks upstream availability, reachability, and readiness."""
        pass

    # --- Backward compatibility aliases ---

    def test_connectivity(self) -> bool:
        """Alias for health_check() maintaining Phase 8 compatibility."""
        return self.health_check()

    def fetch_raw_data(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Alias for fetch() maintaining backward compatibility."""
        return self.fetch(from_date=from_date, to_date=to_date, limit=limit)

    def parse_item_to_domain(self, item: Dict[str, Any]) -> Optional[Any]:
        """Validates and transforms a single item maintaining backward compatibility."""
        if not self.validate(item):
            return None
        return self.transform(item)

    def fetch_with_resilience(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Executes fetch() protected by rate limiting, retries, and circuit breaker."""
        self.rate_limiter.acquire()
        return execute_with_retry(
            self.fetch,
            max_retries=self.max_retries,
            initial_delay=0.05,
            backoff_factor=self.backoff_factor,
            circuit_breaker=self.circuit_breaker,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
        )

    def sync(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50,
    ) -> AdapterSyncResult:
        """
        Executes resilient fetch, validation, and domain transformation.
        """
        result = AdapterSyncResult(source_name=self.source_name)
        try:
            raw_items = self.fetch_with_resilience(from_date=from_date, to_date=to_date, limit=limit)
            result.records_fetched = len(raw_items)

            for item in raw_items:
                try:
                    result.records_parsed += 1
                    if not self.validate(item):
                        logger.debug("Validation filter discarded item in %s: %s", self.source_name, item)
                        continue

                    domain_obj = self.transform(item)
                    if isinstance(domain_obj, MasterIPORecord):
                        result.master_records.append(domain_obj)
                        result.records_valid += 1
                    elif isinstance(domain_obj, tuple) and len(domain_obj) == 2 and isinstance(domain_obj[1], GMPData):
                        result.gmp_quotes.append(domain_obj)
                        result.records_valid += 1
                    elif domain_obj is not None:
                        result.records_valid += 1
                except Exception as parse_err:
                    err_msg = f"Failed to transform item from {self.source_name}: {parse_err}"
                    logger.warning(err_msg)
                    result.errors.append(err_msg)

        except CircuitBreakerOpenError as cb_err:
            err_msg = f"Circuit breaker open for {self.source_name}: {cb_err}"
            logger.error(err_msg)
            result.errors.append(err_msg)
        except Exception as fetch_err:
            err_msg = f"Fatal fetch error in {self.source_name}: {fetch_err}"
            logger.error(err_msg, exc_info=True)
            result.errors.append(err_msg)
        finally:
            result.completed_at = datetime.utcnow()

        return result
