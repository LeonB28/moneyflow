"""
Unit tests for retry logic with exponential backoff.

These tests ensure that the retry mechanism handles:
- Successful retries after transient failures
- User cancellation with Ctrl-C (asyncio.CancelledError)
- All retries exhausted scenario
- Exponential backoff timing
- Auth error detection and session refresh
"""

import asyncio

import pytest

from moneyflow.retry_logic import RetryAborted, retry_with_backoff


class TestRetryLogic:
    """Test retry_with_backoff function with various failure scenarios."""

    @pytest.mark.asyncio
    async def test_successful_on_first_attempt(self):
        """Test operation succeeds on first try (no retry needed)."""
        call_count = [0]

        async def successful_operation():
            call_count[0] += 1
            return "success"

        result = await retry_with_backoff(
            operation=successful_operation,
            operation_name="Test operation",
            max_retries=3,
            initial_wait=0.1,  # Fast for testing
        )

        assert result == "success"
        assert call_count[0] == 1  # Only called once

    @pytest.mark.asyncio
    async def test_retry_after_transient_failure(self):
        """Test successful retry after one transient failure."""
        call_count = [0]

        async def flaky_operation():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Transient failure")
            return "success after retry"

        result = await retry_with_backoff(
            operation=flaky_operation,
            operation_name="Flaky operation",
            max_retries=3,
            initial_wait=0.01,  # Fast for testing
        )

        assert result == "success after retry"
        assert call_count[0] == 2  # Called twice (1 failure + 1 success)

    @pytest.mark.asyncio
    async def test_retry_after_multiple_failures(self):
        """Test successful retry after multiple transient failures."""
        call_count = [0]

        async def very_flaky_operation():
            call_count[0] += 1
            if call_count[0] <= 3:
                raise Exception(f"Failure {call_count[0]}")
            return "finally succeeded"

        result = await retry_with_backoff(
            operation=very_flaky_operation,
            operation_name="Very flaky operation",
            max_retries=5,
            initial_wait=0.01,  # Fast for testing
        )

        assert result == "finally succeeded"
        assert call_count[0] == 4  # 3 failures + 1 success

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        """Test that exception is raised when all retries are exhausted."""
        call_count = [0]

        async def always_failing_operation():
            call_count[0] += 1
            raise Exception(f"Permanent failure (attempt {call_count[0]})")

        with pytest.raises(Exception, match="Permanent failure"):
            await retry_with_backoff(
                operation=always_failing_operation,
                operation_name="Always failing",
                max_retries=3,
                initial_wait=0.01,
            )

        assert call_count[0] == 3  # All 3 attempts made

    @pytest.mark.asyncio
    async def test_user_cancellation(self):
        """Test that user can cancel retry with Ctrl-C (raises RetryAborted)."""
        call_count = [0]

        async def operation_that_gets_cancelled():
            call_count[0] += 1
            if call_count[0] == 1:
                # First attempt fails
                raise Exception("Initial failure")
            # Should never get here - will be cancelled during wait
            return "shouldn't happen"

        async def cancelling_operation():
            """Simulate user pressing Ctrl-C during retry wait."""
            # Start the retry operation
            task = asyncio.create_task(
                retry_with_backoff(
                    operation=operation_that_gets_cancelled,
                    operation_name="Operation",
                    max_retries=5,
                    initial_wait=0.5,  # Long enough to cancel
                )
            )

            # Give it time to fail once and start waiting
            await asyncio.sleep(0.05)

            # Simulate Ctrl-C
            task.cancel()

            # Wait for the task
            await task

        # Should raise RetryAborted when cancelled
        with pytest.raises(RetryAborted, match="User cancelled Operation"):
            await cancelling_operation()

        # Should have called once, failed, then been cancelled during wait
        assert call_count[0] == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that wait times increase exponentially."""
        call_count = [0]
        retry_times = []

        async def failing_operation():
            call_count[0] += 1
            if call_count[0] <= 3:
                raise Exception("Keep failing")
            return "done"

        def on_retry_callback(attempt: int, wait_seconds: float):
            """Record retry timing."""
            retry_times.append((attempt, wait_seconds))

        await retry_with_backoff(
            operation=failing_operation,
            operation_name="Backoff test",
            max_retries=5,
            initial_wait=0.05,  # 50ms for faster tests
            on_retry=on_retry_callback,
        )

        # Should have 3 retries (attempts 1, 2, 3)
        assert len(retry_times) == 3

        # Check exponential backoff: 0.05s, 0.1s, 0.2s
        assert retry_times[0] == (1, 0.05)  # 0.05 * 2^0 = 0.05
        assert retry_times[1] == (2, 0.1)  # 0.05 * 2^1 = 0.1
        assert retry_times[2] == (3, 0.2)  # 0.05 * 2^2 = 0.2

    @pytest.mark.asyncio
    async def test_on_retry_callback_invoked(self):
        """Test that on_retry callback is called for each retry."""
        call_count = [0]
        callback_invocations = []

        async def failing_twice():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise Exception(f"Failure {call_count[0]}")
            return "success"

        def callback(attempt: int, wait_seconds: float):
            callback_invocations.append((attempt, wait_seconds))

        await retry_with_backoff(
            operation=failing_twice,
            operation_name="Test",
            max_retries=5,
            initial_wait=0.1,
            on_retry=callback,
        )

        # Should have been called twice (after first and second failures)
        assert len(callback_invocations) == 2
        assert callback_invocations[0][0] == 1  # First retry
        assert callback_invocations[1][0] == 2  # Second retry

    @pytest.mark.asyncio
    async def test_on_retry_callback_not_called_on_first_success(self):
        """Test that callback is NOT called if operation succeeds immediately."""
        callback_called = [False]

        async def immediate_success():
            return "success"

        def callback(attempt: int, wait_seconds: float):
            callback_called[0] = True

        await retry_with_backoff(
            operation=immediate_success,
            operation_name="Test",
            max_retries=3,
            initial_wait=0.1,
            on_retry=callback,
        )

        assert not callback_called[0]  # Should never be called

    @pytest.mark.asyncio
    async def test_auth_error_detection(self):
        """Test that 401/unauthorized errors are properly detected."""
        call_count = [0]

        async def auth_error_operation():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("401 Unauthorized")
            return "success after auth"

        result = await retry_with_backoff(
            operation=auth_error_operation,
            operation_name="Auth test",
            max_retries=3,
            initial_wait=0.01,
        )

        assert result == "success after auth"
        assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_max_retries_configurable(self):
        """Test that max_retries parameter is respected."""
        call_count = [0]

        async def always_fail():
            call_count[0] += 1
            raise Exception("Fail")

        # Test with max_retries=1
        with pytest.raises(Exception):
            await retry_with_backoff(
                operation=always_fail, operation_name="Test", max_retries=1, initial_wait=0.01
            )

        assert call_count[0] == 1

        # Test with max_retries=7
        call_count[0] = 0
        with pytest.raises(Exception):
            await retry_with_backoff(
                operation=always_fail, operation_name="Test", max_retries=7, initial_wait=0.01
            )

        assert call_count[0] == 7

    @pytest.mark.asyncio
    async def test_initial_wait_configurable(self):
        """Test that initial_wait parameter is respected."""
        retry_waits = []

        async def failing_operation():
            raise Exception("Fail")

        def callback(attempt: int, wait_seconds: float):
            retry_waits.append(wait_seconds)

        # Custom initial wait of 0.05 seconds (50ms)
        with pytest.raises(Exception):
            await retry_with_backoff(
                operation=failing_operation,
                operation_name="Test",
                max_retries=2,
                initial_wait=0.05,
                on_retry=callback,
            )

        # Should have 1 retry (attempt 1)
        assert len(retry_waits) == 1
        assert retry_waits[0] == 0.05  # 0.05 * 2^0 = 0.05

    @pytest.mark.asyncio
    async def test_actual_wait_occurs(self):
        """Test that retry actually waits (not just calculates wait time)."""
        import time

        call_count = [0]
        start_time = time.time()

        async def failing_operation():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Fail once")
            return "success"

        result = await retry_with_backoff(
            operation=failing_operation,
            operation_name="Wait test",
            max_retries=2,
            initial_wait=0.1,  # 100ms wait
        )

        elapsed = time.time() - start_time

        assert result == "success"
        # Should have waited at least 100ms
        assert elapsed >= 0.1
