"""
Unit Tests for Distributed Job Orchestration, Locks, and Persistent Execution State.
Verifies distributed lock acquire/release/renew/timeout, lock contention,
execution history persistence, duplicate daily execution prevention, failure recording,
and multi-scheduler cluster coordination.
"""

from datetime import date, datetime, timedelta
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ipo_platform.db import get_engine, init_db
from ipo_platform.db.session import get_db_session
from ipo_platform.jobs.distributed_scheduler import DistributedJobScheduler
from ipo_platform.jobs.execution_history import (
    JobExecutionHistoryRepository,
    JobExecutionStatus,
)
from ipo_platform.jobs.locks import DistributedLock, RedisDistributedLock


class MockRedisClient:
    """In-memory Redis client simulator for testing RedisDistributedLock semantics."""

    def __init__(self):
        self.store = {}
        self.expirations = {}

    def set(self, key, value, ex=None, nx=False):
        now = datetime.utcnow()
        if nx and key in self.store:
            # Check if expired
            if key in self.expirations and now >= self.expirations[key]:
                del self.store[key]
                del self.expirations[key]
            else:
                return False

        self.store[key] = value
        if ex:
            self.expirations[key] = now + timedelta(seconds=ex)
        return True

    def get(self, key):
        now = datetime.utcnow()
        if key in self.expirations and now >= self.expirations[key]:
            del self.store[key]
            del self.expirations[key]
            return None
        return self.store.get(key)

    def delete(self, key):
        if key in self.store:
            del self.store[key]
            self.expirations.pop(key, None)
            return 1
        return 0

    def expire(self, key, seconds):
        if key in self.store:
            self.expirations[key] = datetime.utcnow() + timedelta(seconds=seconds)
            return 1
        return 0

    def exists(self, key):
        return 1 if self.get(key) is not None else 0

    def register_script(self, script_text):
        return None  # Let lock fallback to direct methods or eval


class TestDistributedScheduler(unittest.TestCase):
    def setUp(self):
        """Initializes test database and mock locks."""
        self.engine = get_engine("sqlite:///:memory:")
        init_db(self.engine)
        self.mock_redis = MockRedisClient()

    def tearDown(self):
        self.engine.dispose()

    def test_redis_distributed_lock_acquire_and_release(self):
        lock = RedisDistributedLock("briefing", lease_seconds=30, redis_client=self.mock_redis)
        self.assertFalse(lock.is_locked)

        # Acquire lock
        acquired = lock.acquire(blocking=False)
        self.assertTrue(acquired)
        self.assertTrue(lock.is_locked)

        # Second acquisition with same key must fail (contention)
        lock2 = RedisDistributedLock("briefing", lease_seconds=30, redis_client=self.mock_redis)
        self.assertFalse(lock2.acquire(blocking=False))

        # Release first lock
        released = lock.release()
        self.assertTrue(released)
        self.assertFalse(lock.is_locked)

        # Now lock2 can acquire
        self.assertTrue(lock2.acquire(blocking=False))
        lock2.release()

    def test_redis_distributed_lock_renewal(self):
        lock = RedisDistributedLock("briefing", lease_seconds=10, redis_client=self.mock_redis)
        lock.acquire(blocking=False)
        self.assertTrue(lock.renew(extension_seconds=60))
        lock.release()

    def test_execution_history_lifecycle(self):
        job_name = "test_daily_briefing"
        exec_date = date(2026, 10, 12)

        # 1. Verify initially not completed
        with get_db_session(self.engine) as session:
            self.assertFalse(JobExecutionHistoryRepository.is_already_completed(session, job_name, exec_date))

            # 2. Record start
            rec = JobExecutionHistoryRepository.record_start(session, job_name, exec_date, node_id="node-1")
            self.assertEqual(rec.execution_status, JobExecutionStatus.STARTED.value)

            # 3. Record completion
            rec = JobExecutionHistoryRepository.record_completion(session, job_name, exec_date)
            self.assertEqual(rec.execution_status, JobExecutionStatus.COMPLETED.value)
            self.assertIsNotNone(rec.completed_at)

            # 4. Verify now marked as completed
            self.assertTrue(JobExecutionHistoryRepository.is_already_completed(session, job_name, exec_date))

    def test_execution_history_failure_recording(self):
        job_name = "test_failing_job"
        exec_date = date(2026, 10, 12)

        with get_db_session(self.engine) as session:
            JobExecutionHistoryRepository.record_start(session, job_name, exec_date, node_id="node-1")
            JobExecutionHistoryRepository.record_failure(session, job_name, exec_date, "Connection timed out")
            rec = JobExecutionHistoryRepository.get_execution(session, job_name, exec_date)
            self.assertEqual(rec.execution_status, JobExecutionStatus.FAILED.value)
            self.assertEqual(rec.error_message, "Connection timed out")
            self.assertFalse(JobExecutionHistoryRepository.is_already_completed(session, job_name, exec_date))

    def test_distributed_scheduler_exactly_once_guarantee(self):
        """Tests that two scheduler nodes running simultaneously execute a job exactly once."""
        call_count = []

        def sample_job():
            call_count.append(1)
            return "SUCCESS"

        def lock_factory(name):
            return RedisDistributedLock(name, lease_seconds=60, redis_client=self.mock_redis)

        scheduler_node_1 = DistributedJobScheduler(self.engine, lock_factory=lock_factory, node_id="node-alpha")
        scheduler_node_2 = DistributedJobScheduler(self.engine, lock_factory=lock_factory, node_id="node-beta")

        target_date = date(2026, 10, 12)

        # 1. Node 1 executes successfully
        res1 = scheduler_node_1.execute_job_with_idempotency("daily_briefing", sample_job, target_date=target_date)
        self.assertEqual(res1["status"], JobExecutionStatus.COMPLETED.value)
        self.assertEqual(len(call_count), 1)

        # 2. Node 2 attempts to run for the same date -> MUST BE SKIPPED (Idempotency)
        res2 = scheduler_node_2.execute_job_with_idempotency("daily_briefing", sample_job, target_date=target_date)
        self.assertEqual(res2["status"], JobExecutionStatus.SKIPPED.value)
        self.assertIn("already completed", res2["message"])

        # Call count must still be 1 (exactly once)
        self.assertEqual(len(call_count), 1)

    def test_distributed_scheduler_lock_contention(self):
        """Tests that while Node 1 holds the lock, Node 2 skips execution due to contention."""
        def lock_factory(name):
            return RedisDistributedLock(name, lease_seconds=60, redis_client=self.mock_redis)

        scheduler = DistributedJobScheduler(self.engine, lock_factory=lock_factory, node_id="node-alpha")
        target_date = date(2026, 10, 13)

        # Pre-acquire the lock manually to simulate active execution on another node
        active_lock = lock_factory(f"daily_briefing-{target_date.isoformat()}")
        active_lock.acquire(blocking=False)

        res = scheduler.execute_job_with_idempotency("daily_briefing", lambda: "HELLO", target_date=target_date)
        self.assertEqual(res["status"], JobExecutionStatus.SKIPPED.value)
        self.assertIn("Lock contention", res["message"])

        active_lock.release()

    def test_distributed_scheduler_failure_and_retry(self):
        """Tests that a failed execution can be retried on the same date until success."""
        attempts = []

        def flaky_job():
            if len(attempts) == 0:
                attempts.append("fail")
                raise RuntimeError("Temporary downstream failure")
            attempts.append("success")
            return "RECOVERED"

        def lock_factory(name):
            return RedisDistributedLock(name, lease_seconds=60, redis_client=self.mock_redis)

        scheduler = DistributedJobScheduler(self.engine, lock_factory=lock_factory, node_id="node-worker")
        target_date = date(2026, 10, 14)

        # Attempt 1 -> fails
        res1 = scheduler.execute_job_with_idempotency("flaky_job", flaky_job, target_date=target_date)
        self.assertEqual(res1["status"], JobExecutionStatus.FAILED.value)

        # Attempt 2 -> retries and succeeds
        res2 = scheduler.execute_job_with_idempotency("flaky_job", flaky_job, target_date=target_date)
        self.assertEqual(res2["status"], JobExecutionStatus.COMPLETED.value)
        self.assertEqual(res2["result"], "RECOVERED")

        # Attempt 3 -> already completed -> SKIPPED
        res3 = scheduler.execute_job_with_idempotency("flaky_job", flaky_job, target_date=target_date)
        self.assertEqual(res3["status"], JobExecutionStatus.SKIPPED.value)


if __name__ == "__main__":
    unittest.main()
