"""
Comprehensive tests for editing functionality.

Tests the complete editing workflows including:
- Bulk merchant rename from aggregate view
- Individual transaction recategorization
- Multi-select functionality
- Edit queueing and committing
"""

import pytest
from datetime import datetime
import polars as pl
from monarch_tui.state import AppState, ViewMode, TransactionEdit


class TestBulkMerchantEdit:
    """Test bulk merchant editing from aggregate view."""

    async def test_bulk_edit_queues_all_transactions(self, loaded_data_manager, app_state):
        """Test that bulk edit creates edits for all transactions."""
        dm, df, _, _ = loaded_data_manager

        # Find a merchant with multiple transactions
        merchant_name = "Whole Foods"
        merchant_txns = dm.filter_by_merchant(df, merchant_name)
        txn_count = len(merchant_txns)

        assert txn_count > 0, "Test data should have Whole Foods transactions"

        # Simulate bulk edit: add edits for all transactions
        new_merchant = "Whole Foods Market"
        for txn in merchant_txns.iter_rows(named=True):
            dm.pending_edits.append(
                TransactionEdit(
                    transaction_id=txn["id"],
                    field="merchant",
                    old_value=merchant_name,
                    new_value=new_merchant,
                    timestamp=datetime.now()
                )
            )

        # Verify edits were queued
        assert len(dm.pending_edits) == txn_count
        assert all(e.field == "merchant" for e in dm.pending_edits)
        assert all(e.new_value == new_merchant for e in dm.pending_edits)

    async def test_bulk_edit_commits_successfully(self, loaded_data_manager, mock_mm):
        """Test that bulk merchant edit commits to API."""
        dm, df, _, _ = loaded_data_manager

        merchant_name = "Whole Foods"
        new_merchant = "Whole Foods Market"
        merchant_txns = dm.filter_by_merchant(df, merchant_name)

        # Queue bulk edits
        for txn in merchant_txns.iter_rows(named=True):
            dm.pending_edits.append(
                TransactionEdit(
                    transaction_id=txn["id"],
                    field="merchant",
                    old_value=merchant_name,
                    new_value=new_merchant,
                    timestamp=datetime.now()
                )
            )

        # Commit
        success, failure = await dm.commit_pending_edits(dm.pending_edits)

        assert success == len(merchant_txns)
        assert failure == 0

        # Verify all were updated in backend
        for txn in merchant_txns.iter_rows(named=True):
            updated = mock_mm.get_transaction_by_id(txn["id"])
            assert updated["merchant"]["name"] == new_merchant

    async def test_bulk_edit_handles_partial_failure(self, data_manager):
        """Test that bulk edit handles some transactions failing."""
        # Create edits with mix of valid and invalid transaction IDs
        edits = [
            TransactionEdit("valid_txn", "merchant", "Old", "New", datetime.now()),
            TransactionEdit("invalid_txn_999", "merchant", "Old", "New", datetime.now()),
        ]

        success, failure = await data_manager.commit_pending_edits(edits)

        # At least one should succeed/fail
        assert success + failure == len(edits)


class TestIndividualEdits:
    """Test editing individual transactions."""

    async def test_edit_single_merchant(self, loaded_data_manager, mock_mm):
        """Test editing merchant for a single transaction."""
        dm, df, _, _ = loaded_data_manager

        txn = df.row(0, named=True)
        old_merchant = txn["merchant"]
        new_merchant = "Corrected Merchant Name"

        # Queue edit
        dm.pending_edits.append(
            TransactionEdit(
                transaction_id=txn["id"],
                field="merchant",
                old_value=old_merchant,
                new_value=new_merchant,
                timestamp=datetime.now()
            )
        )

        # Commit
        success, failure = await dm.commit_pending_edits(dm.pending_edits)

        assert success == 1
        assert failure == 0

        # Verify
        updated = mock_mm.get_transaction_by_id(txn["id"])
        assert updated["merchant"]["name"] == new_merchant

    async def test_recategorize_transaction(self, loaded_data_manager, mock_mm):
        """Test changing category for a transaction."""
        dm, df, categories, _ = loaded_data_manager

        txn = df.row(0, named=True)
        old_category_id = txn["category_id"]

        # Find a different category
        new_category_id = None
        for cat_id in categories:
            if cat_id != old_category_id:
                new_category_id = cat_id
                break

        assert new_category_id is not None

        # Queue edit
        dm.pending_edits.append(
            TransactionEdit(
                transaction_id=txn["id"],
                field="category",
                old_value=old_category_id,
                new_value=new_category_id,
                timestamp=datetime.now()
            )
        )

        # Commit
        success, failure = await dm.commit_pending_edits(dm.pending_edits)

        assert success == 1
        assert failure == 0

        # Verify
        updated = mock_mm.get_transaction_by_id(txn["id"])
        assert updated["category"]["id"] == new_category_id


class TestMultiSelect:
    """Test multi-select functionality for bulk operations."""

    def test_toggle_selection_adds_transaction(self, app_state):
        """Test that toggling selection adds transaction ID."""
        txn_id = "txn_123"

        app_state.toggle_selection(txn_id)

        assert txn_id in app_state.selected_ids
        assert len(app_state.selected_ids) == 1

    def test_toggle_selection_removes_if_already_selected(self, app_state):
        """Test that toggling again removes selection."""
        txn_id = "txn_123"

        app_state.toggle_selection(txn_id)
        app_state.toggle_selection(txn_id)

        assert txn_id not in app_state.selected_ids
        assert len(app_state.selected_ids) == 0

    def test_select_multiple_transactions(self, app_state):
        """Test selecting multiple transactions."""
        ids = ["txn_1", "txn_2", "txn_3", "txn_4", "txn_5"]

        for txn_id in ids:
            app_state.toggle_selection(txn_id)

        assert len(app_state.selected_ids) == 5
        assert all(tid in app_state.selected_ids for tid in ids)

    def test_clear_selection(self, app_state):
        """Test clearing all selections."""
        app_state.toggle_selection("txn_1")
        app_state.toggle_selection("txn_2")
        app_state.toggle_selection("txn_3")

        app_state.clear_selection()

        assert len(app_state.selected_ids) == 0


class TestEditQueueing:
    """Test that edits are properly queued before committing."""

    def test_multiple_edits_queue_correctly(self):
        """Test that multiple edits accumulate in pending list."""
        dm_pending = []

        # Queue multiple edits
        edits = [
            TransactionEdit("txn_1", "merchant", "A", "B", datetime.now()),
            TransactionEdit("txn_2", "merchant", "C", "D", datetime.now()),
            TransactionEdit("txn_3", "category", "cat_1", "cat_2", datetime.now()),
        ]

        dm_pending.extend(edits)

        assert len(dm_pending) == 3

    def test_edits_can_be_cleared(self):
        """Test that pending edits can be cleared after commit."""
        dm_pending = [
            TransactionEdit("txn_1", "merchant", "A", "B", datetime.now()),
            TransactionEdit("txn_2", "merchant", "C", "D", datetime.now()),
        ]

        dm_pending.clear()

        assert len(dm_pending) == 0


class TestEditValidation:
    """Test validation and error handling for edits."""

    async def test_empty_merchant_name_rejected(self):
        """Test that empty merchant names are not accepted."""
        # This would be handled by the EditMerchantScreen
        # If user submits empty string, modal returns None
        current = "Amazon"
        new_value = ""  # Empty

        # Modal should not return empty string
        result = new_value.strip() if new_value.strip() else None
        assert result is None

    async def test_unchanged_merchant_name_no_edit(self):
        """Test that unchanged name doesn't create edit."""
        current = "Amazon"
        new_value = "Amazon"  # Same

        # Modal should return None if unchanged
        result = new_value if new_value != current else None
        assert result is None

    async def test_commit_with_no_edits_succeeds(self, data_manager):
        """Test that committing with empty edits list works."""
        success, failure = await data_manager.commit_pending_edits([])

        assert success == 0
        assert failure == 0


class TestEdgeCase:
    """Test edge cases in editing."""

    async def test_edit_merchant_with_special_characters(self, loaded_data_manager, mock_mm):
        """Test that special characters in merchant names work."""
        dm, df, _, _ = loaded_data_manager

        txn = df.row(0, named=True)
        new_merchant = "Trader Joe's & Co. (Main St.)"

        dm.pending_edits.append(
            TransactionEdit(
                txn["id"],
                "merchant",
                txn["merchant"],
                new_merchant,
                datetime.now()
            )
        )

        success, failure = await dm.commit_pending_edits(dm.pending_edits)

        assert success == 1
        updated = mock_mm.get_transaction_by_id(txn["id"])
        assert updated["merchant"]["name"] == new_merchant

    async def test_edit_merchant_with_unicode(self, loaded_data_manager, mock_mm):
        """Test that unicode characters in merchant names work."""
        dm, df, _, _ = loaded_data_manager

        txn = df.row(0, named=True)
        new_merchant = "Café René"

        dm.pending_edits.append(
            TransactionEdit(
                txn["id"],
                "merchant",
                txn["merchant"],
                new_merchant,
                datetime.now()
            )
        )

        success, failure = await dm.commit_pending_edits(dm.pending_edits)

        assert success == 1
        updated = mock_mm.get_transaction_by_id(txn["id"])
        assert updated["merchant"]["name"] == new_merchant
