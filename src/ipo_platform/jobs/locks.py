"""
Distributed Locking Infrastructure for Indian IPO Platform.
Provides abstract DistributedLock interface, in-memory fallback lock for standalone testing,
and RedisDistributedLock for multi-node production deployments.
"""

from abc import ABC, abstractmethod
import logging
import os
import threading
import time
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


class DistributedLock(ABC):
    """Abstract interface for distributed mutex locking."""

    @abstractmethod
    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Attempts to acquire the distributed lock.

        Args:
            blocking: If True, blocks until lock is acquired or timeout expires.
            timeout: Maximum duration in seconds to wait when blocking.

        Returns:
            True if lock was acquired, False otherwise.
        """
        pass

    @abstractmethod
    def release(self) -> bool:
        """
        Releases the lock if held by the current owner.

        Returns:
            True if release was successful, False otherwise.
        """
        pass

    @abstractmethod
    def renew(self, extension_seconds: Optional[int] = None) -> bool:
        """
        Renews lock lease duration.

        Returns:
            True if renewed, False otherwise.
        """
        pass

    @property
    @abstractmethod
    def is_locked(self) -> bool:
        """Returns True if the lock is currently held."""
        pass

    def __enter__(self) -> bool:
        acquired = self.acquire()
        if not acquired:
            raise TimeoutError("Failed to acquire distributed lock within timeout.")
        return acquired

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


class RedisDistributedLock(DistributedLock):
    """
    Redis-backed distributed lock utilizing atomic SET NX EX semantics
    and Lua script evaluation for safe owner-only release.
    """

    # Lua script for safe atomic unlock: verifies token matches before deleting key
    UNLOCK_LUA_SCRIPT = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """

    # Lua script for safe atomic renew
    RENEW_LUA_SCRIPT = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("expire", KEYS[1], ARGV[2])
    else
        return 0
    end
    """

    def __init__(
        self,
        lock_name: str,
        redis_url: Optional[str] = None,
        lease_seconds: int = 60,
        owner_id: Optional[str] = None,
        redis_client=None,
    ) -> None:
        """
        Initializes RedisDistributedLock.

        Args:
            lock_name: Unique lock resource identifier.
            redis_url: Redis connection string (defaults to REDIS_URL env var or redis://localhost:6379/0).
            lease_seconds: Time-to-live expiration in seconds for stale lock recovery.
            owner_id: Unique caller identifier token (auto-generated UUID if None).
            redis_client: Optional pre-configured redis.Redis instance (for DI / mocking).
        """
        self.lock_key = f"ipo:lock:{lock_name}"
        self.lease_seconds = lease_seconds
        self.owner_id = owner_id or f"{os.uname().nodename if hasattr(os, 'uname') else 'node'}-{uuid.uuid4()}"
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")

        if redis_client is not None:
            self._redis = redis_client
        else:
            try:
                import redis
                self._redis = redis.Redis.from_url(self.redis_url, decode_responses=True)
            except Exception as err:
                logger.warning("Could not connect to Redis at %s (%s). Falling back to in-memory lock.", self.redis_url, err)
                self._redis = None

        self._unlock_script = None
        self._renew_script = None
        if self._redis:
            try:
                self._unlock_script = self._redis.register_script(self.UNLOCK_LUA_SCRIPT)
                self._renew_script = self._redis.register_script(self.RENEW_LUA_SCRIPT)
            except Exception:
                pass

        # Fallback in-memory state if Redis is unreachable in test environments
        self._memory_lock = threading.Lock()
        self._memory_owner: Optional[str] = None
        self._memory_expires_at: float = 0.0

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        start_time = time.time()
        timeout = timeout or (10.0 if blocking else 0.0)

        while True:
            if self._redis is not None:
                try:
                    # Atomic SET with NX (not exists) and EX (expire seconds)
                    acquired = bool(self._redis.set(self.lock_key, self.owner_id, ex=self.lease_seconds, nx=True))
                    if acquired:
                        logger.debug("Redis lock '%s' acquired by owner '%s'", self.lock_key, self.owner_id)
                        return True
                except Exception as err:
                    logger.error("Redis error acquiring lock '%s': %s", self.lock_key, err)
                    return False
            else:
                # In-memory fallback
                with self._memory_lock:
                    now = time.time()
                    if self._memory_owner is None or now >= self._memory_expires_at:
                        self._memory_owner = self.owner_id
                        self._memory_expires_at = now + self.lease_seconds
                        return True

            if not blocking:
                return False

            if time.time() - start_time >= timeout:
                logger.warning("Timed out after %.2fs waiting for lock '%s'", timeout, self.lock_key)
                return False

            time.sleep(0.1)

    def release(self) -> bool:
        if self._redis is not None:
            try:
                if self._unlock_script:
                    result = self._unlock_script(keys=[self.lock_key], args=[self.owner_id])
                    return bool(result)
                else:
                    # Fallback Lua eval
                    val = self._redis.get(self.lock_key)
                    if val == self.owner_id:
                        return bool(self._redis.delete(self.lock_key))
                    return False
            except Exception as err:
                logger.error("Redis error releasing lock '%s': %s", self.lock_key, err)
                return False
        else:
            with self._memory_lock:
                if self._memory_owner == self.owner_id:
                    self._memory_owner = None
                    self._memory_expires_at = 0.0
                    return True
                return False

    def renew(self, extension_seconds: Optional[int] = None) -> bool:
        ext = extension_seconds or self.lease_seconds
        if self._redis is not None:
            try:
                if self._renew_script:
                    result = self._renew_script(keys=[self.lock_key], args=[self.owner_id, ext])
                    return bool(result)
                else:
                    val = self._redis.get(self.lock_key)
                    if val == self.owner_id:
                        return bool(self._redis.expire(self.lock_key, ext))
                    return False
            except Exception as err:
                logger.error("Redis error renewing lock '%s': %s", self.lock_key, err)
                return False
        else:
            with self._memory_lock:
                if self._memory_owner == self.owner_id:
                    self._memory_expires_at = time.time() + ext
                    return True
                return False

    @property
    def is_locked(self) -> bool:
        if self._redis is not None:
            try:
                return bool(self._redis.exists(self.lock_key))
            except Exception:
                return False
        else:
            with self._memory_lock:
                return self._memory_owner is not None and time.time() < self._memory_expires_at
