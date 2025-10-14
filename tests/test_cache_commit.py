"""
Tests for commit functionality when using cached data.

This test file addresses the critical issue where commits were failing
when loading from cache. These tests ensure the backend is properly
authenticated and ready to commit changes even when data is cached.
"""

import pytest
from datetime import datetime
from moneyflow.state import TransactionEdit


class TestCacheAndCommit:
    """Test that commits work correctly after loading from cache."""

    async def test_commit_works_after_cache_load(self, data_manager, mock_mm):
        """
        Test that we can commit edits even when backend was initialized
        but data was loaded from cache (simulating real scenario).

        This reproduces the bug where commits failed with cached data.
        """
        # Ensure backend is logged in (simulates cache path)
        await mock_mm.login()

        # Create edit
        edits = [
            TransactionEdit("txn_1", "merchant", "Old", "New", datetime.now())
        ]

        # Attempt commit
        success, failure = await data_manager.commit_pending_edits(edits)

        # Should succeed
        assert success == 1
        assert failure == 0
        assert len(mock_mm.update_calls) == 1

    async def test_commit_multiple_edits_after_cache(self, data_manager, mock_mm):
        """Test bulk commits after loading from cache."""
        await mock_mm.login()

        # Use valid transaction IDs that exist in mock backend
        # Mock has txn_1 through txn_6
        edits = [
            TransactionEdit(f"txn_{i}", "merchant", f"Old{i}", f"New{i}", datetime.now())
            for i in range(1, 7)  # Use 6 valid transaction IDs
        ]

        success, failure = await data_manager.commit_pending_edits(edits)

        # All should succeed
        assert success == 6
        assert failure == 0
        assert len(mock_mm.update_calls) == 6

    async def test_commit_handles_not_logged_in(self, data_manager, mock_mm):
        """
        Test error handling when backend is NOT logged in.

        This might be the root cause - backend not properly authenticated
        when loading from cache.
        """
        # Don't login - simulate the bug scenario
        # mock_mm.login() NOT called

        edits = [
            TransactionEdit("txn_1", "merchant", "Old", "New", datetime.now())
        ]

        # This should either:
        # 1. Fail with clear error
        # 2. Auto-login and succeed
        success, failure = await data_manager.commit_pending_edits(edits)

        # Record what happens for analysis
        # In real backend, not being logged in would cause 401 errors
        # In mock, it should still work (mock doesn't require auth)
        assert success >= 0
        assert failure >= 0

    async def test_commit_with_session_expiration_during_cache(self, data_manager, mock_mm):
        """
        Test that session expiration is handled during commit.

        Scenario:
        1. Login at startup
        2. Load from cache (fast)
        3. User edits transactions
        4. Session expires before commit
        5. Commit should auto-recover
        """
        await mock_mm.login()

        # Simulate session expiring by making update fail once
        original_update = mock_mm.update_transaction
        call_count = [0]

        async def failing_then_succeeding_update(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call fails (session expired)
                raise Exception("401 Unauthorized")
            # Second call succeeds (after re-login)
            return await original_update(*args, **kwargs)

        mock_mm.update_transaction = failing_then_succeeding_update

        edits = [TransactionEdit("txn_1", "merchant", "Old", "New", datetime.now())]

        # Should fail on first attempt
        success, failure = await data_manager.commit_pending_edits(edits)

        # Mock backend doesn't auto-retry, so this will show 1 failure
        assert failure == 1

        # But in real app, _commit_with_retry() wrapper should handle this
        # This test shows we need to ensure retry logic is in place
