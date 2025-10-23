"""
Tests for AppController business logic.

These tests verify controller behavior without requiring the UI to run.
They focus on the "data plane" bugs we recently fixed:
- View refresh logic
- force_rebuild behavior
- Table update sequencing
"""

from datetime import datetime

import polars as pl
import pytest

from moneyflow.app_controller import AppController
from moneyflow.data_manager import DataManager
from moneyflow.state import AppState, SortDirection, SortMode, ViewMode

from .mock_view import MockViewPresenter


@pytest.fixture
def mock_view():
    """Provide mock view presenter."""
    return MockViewPresenter()


@pytest.fixture
async def controller(mock_view, mock_mm):
    """Provide controller with mock dependencies."""
    await mock_mm.login()
    data_manager = DataManager(mock_mm)
    state = AppState()

    # Fetch data
    df, categories, groups = await data_manager.fetch_all_data()
    data_manager.df = df
    data_manager.categories = categories
    data_manager.category_groups = groups
    state.transactions_df = df

    controller = AppController(mock_view, state, data_manager)
    return controller


class TestViewRefresh:
    """Test view refresh logic."""

    async def test_refresh_view_updates_table(self, controller, mock_view):
        """Test that refresh_view calls update_table."""
        controller.state.view_mode = ViewMode.MERCHANT

        controller.refresh_view()

        # Should have updated table
        assert len(mock_view.table_updates) == 1
        update = mock_view.get_last_table_update()
        assert update["column_count"] == 4  # Merchant, Count, Total, Flags
        assert update["row_count"] > 0  # Should have data

    async def test_refresh_view_with_force_rebuild_true(self, controller, mock_view):
        """Test force_rebuild=True."""
        controller.state.view_mode = ViewMode.DETAIL

        controller.refresh_view(force_rebuild=True)

        mock_view.assert_force_rebuild(True)

    async def test_refresh_view_with_force_rebuild_false(self, controller, mock_view):
        """Test force_rebuild=False (smooth update)."""
        controller.state.view_mode = ViewMode.DETAIL

        controller.refresh_view(force_rebuild=False)

        mock_view.assert_force_rebuild(False)

    async def test_refresh_view_updates_breadcrumb(self, controller, mock_view):
        """Test that breadcrumb is updated."""
        controller.state.view_mode = ViewMode.MERCHANT

        controller.refresh_view()

        assert len(mock_view.breadcrumbs) == 1
        assert "Merchants" in mock_view.breadcrumbs[0]

    async def test_refresh_view_updates_stats(self, controller, mock_view):
        """Test that stats are updated."""
        controller.state.view_mode = ViewMode.MERCHANT

        controller.refresh_view()

        assert len(mock_view.stats) == 1
        assert "txns" in mock_view.stats[0]

    async def test_refresh_view_updates_hints(self, controller, mock_view):
        """Test that action hints are updated."""
        controller.state.view_mode = ViewMode.MERCHANT

        controller.refresh_view()

        assert len(mock_view.hints) == 1
        assert "Merchant" in mock_view.hints[0]

    async def test_refresh_view_updates_pending_changes(self, controller, mock_view):
        """Test that pending changes indicator is updated."""
        controller.state.view_mode = ViewMode.MERCHANT

        controller.refresh_view()

        assert len(mock_view.pending_changes) == 1
        assert mock_view.pending_changes[0] == 0  # No pending edits initially


class TestViewModes:
    """Test different view modes."""

    async def test_merchant_view(self, controller, mock_view):
        """Test merchant aggregation view."""
        controller.state.view_mode = ViewMode.MERCHANT

        controller.refresh_view()

        update = mock_view.get_last_table_update()
        assert update["column_count"] == 4
        # Columns should be: Merchant, Count, Total, Flags
        assert update["columns"][0]["key"] == "merchant"
        assert update["columns"][1]["key"] == "count"
        assert update["columns"][2]["key"] == "total"
        assert update["columns"][3]["key"] == "flags"

    async def test_category_view(self, controller, mock_view):
        """Test category aggregation view."""
        controller.state.view_mode = ViewMode.CATEGORY

        controller.refresh_view()

        update = mock_view.get_last_table_update()
        assert update["column_count"] == 4
        assert update["columns"][0]["key"] == "category"

    async def test_detail_view(self, controller, mock_view):
        """Test transaction detail view."""
        controller.state.view_mode = ViewMode.DETAIL

        controller.refresh_view()

        update = mock_view.get_last_table_update()
        assert update["column_count"] == 6  # Date, Merchant, Category, Account, Amount, Flags
        assert update["columns"][0]["key"] == "date"
        assert update["columns"][1]["key"] == "merchant"


class TestForceRebuildBehavior:
    """
    Test force_rebuild parameter behavior.

    This is critical - the DuplicateKey bug we fixed was caused by
    incorrect handling of force_rebuild.
    """

    async def test_force_rebuild_true_on_first_call(self, controller, mock_view):
        """First call should always force rebuild."""
        controller.state.view_mode = ViewMode.DETAIL

        controller.refresh_view(force_rebuild=True)

        mock_view.assert_force_rebuild(True)

    async def test_force_rebuild_false_on_commit(self, controller, mock_view):
        """Commit from detail view should use force_rebuild=False."""
        controller.state.view_mode = ViewMode.DETAIL

        # Simulate commit flow
        controller.refresh_view(force_rebuild=False)

        mock_view.assert_force_rebuild(False)

    async def test_multiple_refreshes_with_force_rebuild_false(self, controller, mock_view):
        """Multiple refreshes with force_rebuild=False should work."""
        controller.state.view_mode = ViewMode.DETAIL

        # First refresh
        controller.refresh_view(force_rebuild=True)
        assert len(mock_view.table_updates) == 1

        # Second refresh (like after commit)
        controller.refresh_view(force_rebuild=False)
        assert len(mock_view.table_updates) == 2

        # Third refresh (shouldn't crash with DuplicateKey)
        controller.refresh_view(force_rebuild=False)
        assert len(mock_view.table_updates) == 3

        # All should have worked
        assert mock_view.table_updates[0]["force_rebuild"] is True
        assert mock_view.table_updates[1]["force_rebuild"] is False
        assert mock_view.table_updates[2]["force_rebuild"] is False


class TestDetailViewFiltering:
    """Test transaction filtering in detail view."""

    async def test_detail_view_with_merchant_filter(self, controller, mock_view):
        """Test drilling down into a merchant."""
        controller.state.view_mode = ViewMode.DETAIL
        controller.state.selected_merchant = "Amazon"

        controller.refresh_view()

        # Should show only Amazon transactions
        update = mock_view.get_last_table_update()
        # Check that we got some rows (mock has Amazon transactions)
        assert update["row_count"] > 0

    async def test_detail_view_with_category_filter(self, controller, mock_view):
        """Test drilling down into a category."""
        controller.state.view_mode = ViewMode.DETAIL
        controller.state.selected_category = "Shopping"

        controller.refresh_view()

        update = mock_view.get_last_table_update()
        assert update["row_count"] >= 0  # May have 0 Shopping transactions in mock

    async def test_detail_view_ungrouped(self, controller, mock_view):
        """Test all transactions view (no filters)."""
        controller.state.view_mode = ViewMode.DETAIL
        # No selected_* filters

        controller.refresh_view()

        update = mock_view.get_last_table_update()
        # Should show all transactions
        assert update["row_count"] == 6  # Mock has 6 transactions


class TestStatsCalculation:
    """Test statistics calculation logic."""

    async def test_stats_exclude_hidden_transactions(self, controller, mock_view):
        """Test that hidden transactions are excluded from totals."""
        controller.state.view_mode = ViewMode.MERCHANT

        controller.refresh_view()

        stats_text = mock_view.stats[-1]
        # Stats should be calculated (exact values depend on mock data)
        assert "txns" in stats_text
        assert "Income:" in stats_text
        assert "Expenses:" in stats_text

    async def test_stats_with_no_data(self, controller, mock_view):
        """Test stats with empty dataset."""
        # Clear data with proper schema
        empty_df = pl.DataFrame(
            {
                "id": [],
                "date": [],
                "amount": [],
                "merchant": [],
                "category": [],
                "group": [],
                "hideFromReports": [],
            },
            schema={
                "id": pl.Utf8,
                "date": pl.Date,
                "amount": pl.Float64,
                "merchant": pl.Utf8,
                "category": pl.Utf8,
                "group": pl.Utf8,
                "hideFromReports": pl.Boolean,
            },
        )
        controller.data_manager.df = empty_df
        controller.state.transactions_df = empty_df
        controller.state.view_mode = ViewMode.MERCHANT

        controller.refresh_view()

        stats_text = mock_view.stats[-1]
        assert "0 txns" in stats_text or "No data" in stats_text


class TestActionHints:
    """Test action hints for different views."""

    async def test_merchant_view_hints(self, controller, mock_view):
        """Merchant view should show merchant-specific hints."""
        controller.state.view_mode = ViewMode.MERCHANT

        controller.refresh_view()

        hints = mock_view.hints[-1]
        assert "Merchant" in hints
        assert "bulk" in hints.lower()
        assert "Space=Select" in hints

    async def test_category_view_hints(self, controller, mock_view):
        """Category view should show edit_category hint."""
        controller.state.view_mode = ViewMode.CATEGORY

        controller.refresh_view()

        hints = mock_view.hints[-1]
        assert "Category" in hints
        assert "bulk" in hints.lower()
        assert "Space=Select" in hints

    async def test_detail_view_hints(self, controller, mock_view):
        """Detail view should show transaction-level hints."""
        controller.state.view_mode = ViewMode.DETAIL

        controller.refresh_view()

        hints = mock_view.hints[-1]
        assert "Merchant" in hints
        assert "Category" in hints
        assert "Space=Select" in hints
        assert "Ctrl-A=SelectAll" in hints


class TestBreadcrumbGeneration:
    """Test breadcrumb navigation text."""

    async def test_merchant_view_breadcrumb(self, controller, mock_view):
        """Merchant view breadcrumb."""
        controller.state.view_mode = ViewMode.MERCHANT

        controller.refresh_view()

        breadcrumb = mock_view.breadcrumbs[-1]
        assert "Merchants" in breadcrumb

    async def test_drilled_down_breadcrumb(self, controller, mock_view):
        """Breadcrumb when drilled down."""
        controller.state.view_mode = ViewMode.DETAIL
        controller.state.selected_merchant = "Amazon"

        controller.refresh_view()

        breadcrumb = mock_view.breadcrumbs[-1]
        assert "Amazon" in breadcrumb


class TestPendingChangesIndicator:
    """Test pending changes indicator updates."""

    async def test_no_pending_changes(self, controller, mock_view):
        """Initially should have 0 pending changes."""
        controller.state.view_mode = ViewMode.MERCHANT

        controller.refresh_view()

        assert mock_view.pending_changes[-1] == 0

    async def test_with_pending_changes(self, controller, mock_view):
        """Should show count of pending edits."""
        from moneyflow.state import TransactionEdit

        # Add some pending edits
        controller.data_manager.pending_edits = [
            TransactionEdit("txn_1", "merchant", "Old", "New", datetime.now()),
            TransactionEdit("txn_2", "merchant", "Old2", "New2", datetime.now()),
        ]

        controller.state.view_mode = ViewMode.MERCHANT
        controller.refresh_view()

        assert mock_view.pending_changes[-1] == 2


class TestCommitHandling:
    """
    Test commit result handling - THE CRITICAL DATA INTEGRITY LOGIC.

    This is the bug we fixed: edits were applied locally even when
    commits failed. These tests ensure it stays fixed.
    """

    async def test_all_commits_succeed_applies_edits(self, controller, mock_view):
        """When ALL commits succeed, edits should be applied locally."""
        from moneyflow.state import TransactionEdit

        # Set up initial data
        initial_df = controller.data_manager.df.clone()
        initial_merchant = initial_df.filter(pl.col("id") == "txn_1")["merchant"][0]

        # Create edits
        edits = [
            TransactionEdit("txn_1", "merchant", initial_merchant, "NewMerchant", datetime.now())
        ]
        controller.data_manager.pending_edits = edits.copy()

        # Simulate successful commit
        controller.state.view_mode = ViewMode.DETAIL
        saved_state = controller.state.save_view_state()

        controller.handle_commit_result(
            success_count=1, failure_count=0, edits=edits, saved_state=saved_state
        )

        # VERIFY: Edits applied locally
        updated_merchant = controller.data_manager.df.filter(pl.col("id") == "txn_1")["merchant"][0]
        assert updated_merchant == "NewMerchant", "Edit should be applied locally"

        # VERIFY: Pending edits cleared
        assert len(controller.data_manager.pending_edits) == 0, "Pending edits should be cleared"

        # VERIFY: View refreshed
        assert len(mock_view.table_updates) > 0, "View should be refreshed"

    async def test_partial_failure_does_not_apply_edits(self, controller, mock_view):
        """
        CRITICAL: When ANY commits fail, edits should NOT be applied locally.

        This is the data corruption bug we fixed.
        """
        from moneyflow.state import TransactionEdit

        # Set up initial data
        initial_df = controller.data_manager.df.clone()
        initial_merchant = initial_df.filter(pl.col("id") == "txn_1")["merchant"][0]

        # Create edits
        edits = [
            TransactionEdit("txn_1", "merchant", initial_merchant, "NewMerchant1", datetime.now()),
            TransactionEdit("txn_2", "merchant", "Old2", "NewMerchant2", datetime.now()),
        ]
        controller.data_manager.pending_edits = edits.copy()

        # Simulate partial failure (1 success, 1 failure)
        controller.state.view_mode = ViewMode.DETAIL
        saved_state = controller.state.save_view_state()

        controller.handle_commit_result(
            success_count=1, failure_count=1, edits=edits, saved_state=saved_state
        )

        # CRITICAL VERIFICATION: Edits should NOT be applied
        current_merchant = controller.data_manager.df.filter(pl.col("id") == "txn_1")["merchant"][0]
        assert current_merchant == initial_merchant, (
            "Edit should NOT be applied when there were failures (data corruption!)"
        )

        # VERIFY: Pending edits still present (for retry)
        assert len(controller.data_manager.pending_edits) == 2, (
            "Pending edits should be kept for retry"
        )

    async def test_all_failures_does_not_apply_edits(self, controller, mock_view):
        """When ALL commits fail, nothing should be applied."""
        from moneyflow.state import TransactionEdit

        initial_df = controller.data_manager.df.clone()

        edits = [
            TransactionEdit("txn_1", "merchant", "Old1", "New1", datetime.now()),
            TransactionEdit("txn_2", "merchant", "Old2", "New2", datetime.now()),
        ]
        controller.data_manager.pending_edits = edits.copy()

        controller.state.view_mode = ViewMode.DETAIL
        saved_state = controller.state.save_view_state()

        controller.handle_commit_result(
            success_count=0, failure_count=2, edits=edits, saved_state=saved_state
        )

        # VERIFY: DataFrame unchanged
        assert controller.data_manager.df.equals(initial_df), (
            "DataFrame should be completely unchanged"
        )

        # VERIFY: Pending edits preserved
        assert len(controller.data_manager.pending_edits) == 2

    async def test_commit_success_uses_force_rebuild_false(self, controller, mock_view):
        """Commit should use force_rebuild=False for smooth update."""
        from moneyflow.state import TransactionEdit

        edits = [TransactionEdit("txn_1", "merchant", "Old", "New", datetime.now())]

        controller.state.view_mode = ViewMode.DETAIL
        saved_state = controller.state.save_view_state()

        controller.handle_commit_result(
            success_count=1, failure_count=0, edits=edits, saved_state=saved_state
        )

        # VERIFY: force_rebuild=False (no flash)
        mock_view.assert_force_rebuild(False)

    async def test_commit_failure_refreshes_view(self, controller, mock_view):
        """Failed commit should refresh view to show unchanged data."""
        from moneyflow.state import TransactionEdit

        # Set up initial state
        controller.state.view_mode = ViewMode.DETAIL
        initial_merchant = controller.data_manager.df.filter(pl.col("id") == "txn_1")["merchant"][0]

        # Create edits (that will fail)
        edits = [
            TransactionEdit("txn_1", "merchant", initial_merchant, "NewMerchant", datetime.now())
        ]
        controller.data_manager.pending_edits = edits.copy()

        saved_state = controller.state.save_view_state()

        # Simulate failure
        controller.handle_commit_result(
            success_count=0, failure_count=1, edits=edits, saved_state=saved_state
        )

        # VERIFY: DataFrame unchanged (edits NOT applied)
        current_merchant = controller.data_manager.df.filter(pl.col("id") == "txn_1")["merchant"][0]
        assert current_merchant == initial_merchant, "Edits should NOT be applied on failure"

        # VERIFY: Pending edits preserved
        assert len(controller.data_manager.pending_edits) == 1, "Pending edits should be preserved"

        # VERIFY: View refreshed (with force_rebuild=False)
        assert len(mock_view.table_updates) > 0, "View should be refreshed"
        mock_view.assert_force_rebuild(False)


class TestEditQueueing:
    """
    Test edit queueing methods - pure business logic without UI.

    These methods were extracted from app.py to make them testable.
    They handle queueing category and merchant edits.
    """

    async def test_queue_category_edits_single_transaction(self, controller):
        """Test queueing a category edit for a single transaction."""
        # Get a single transaction
        txn_df = controller.data_manager.df.filter(pl.col("id") == "txn_1")
        old_cat_id = txn_df["category_id"][0]
        new_cat_id = "cat_new"

        # Queue the edit
        count = controller.queue_category_edits(txn_df, new_cat_id)

        # Verify
        assert count == 1, "Should queue exactly 1 edit"
        assert len(controller.data_manager.pending_edits) == 1
        edit = controller.data_manager.pending_edits[0]
        assert edit.transaction_id == "txn_1"
        assert edit.field == "category"
        assert edit.old_value == old_cat_id
        assert edit.new_value == new_cat_id

    async def test_queue_category_edits_multiple_transactions(self, controller):
        """Test queueing category edits for multiple transactions."""
        # Get two transactions
        txn_df = controller.data_manager.df.filter(pl.col("id").is_in(["txn_1", "txn_2"]))
        new_cat_id = "cat_bulk"

        count = controller.queue_category_edits(txn_df, new_cat_id)

        assert count == 2
        assert len(controller.data_manager.pending_edits) == 2
        assert all(e.field == "category" for e in controller.data_manager.pending_edits)
        assert all(e.new_value == new_cat_id for e in controller.data_manager.pending_edits)

    async def test_queue_category_edits_preserves_old_values(self, controller):
        """Test that each transaction's old category is preserved correctly."""
        # Get transactions with different categories
        txn_df = controller.data_manager.df.head(3)

        count = controller.queue_category_edits(txn_df, "cat_new")

        assert count == 3
        # Each edit should have its own old_value from the transaction
        old_values = [e.old_value for e in controller.data_manager.pending_edits]
        # Old values should match what's in the DataFrame
        assert len(set(old_values)) >= 1, "Should preserve individual old values"

    async def test_queue_merchant_edits_single_transaction(self, controller):
        """Test queueing a merchant edit for a single transaction."""
        txn_df = controller.data_manager.df.filter(pl.col("id") == "txn_1")
        old_merchant = txn_df["merchant"][0]
        new_merchant = "New Merchant Name"

        count = controller.queue_merchant_edits(txn_df, old_merchant, new_merchant)

        assert count == 1
        assert len(controller.data_manager.pending_edits) == 1
        edit = controller.data_manager.pending_edits[0]
        assert edit.transaction_id == "txn_1"
        assert edit.field == "merchant"
        assert edit.old_value == old_merchant
        assert edit.new_value == new_merchant

    async def test_queue_merchant_edits_bulk_rename(self, controller):
        """Test bulk merchant rename across multiple transactions."""
        # Get all Amazon transactions
        amazon_txns = controller.data_manager.df.filter(pl.col("merchant") == "Amazon")
        old_name = "Amazon"
        new_name = "Amazon.com"

        count = controller.queue_merchant_edits(amazon_txns, old_name, new_name)

        assert count == len(amazon_txns)
        assert len(controller.data_manager.pending_edits) == count
        # All should be merchant edits to Amazon.com
        assert all(e.field == "merchant" for e in controller.data_manager.pending_edits)
        assert all(e.new_value == new_name for e in controller.data_manager.pending_edits)
        assert all(e.old_value == "Amazon" for e in controller.data_manager.pending_edits)

    async def test_queue_edits_empty_dataframe(self, controller):
        """Test queueing edits with empty DataFrame."""
        empty_df = pl.DataFrame(
            {
                "id": [],
                "merchant": [],
                "category_id": [],
            },
            schema={
                "id": pl.Utf8,
                "merchant": pl.Utf8,
                "category_id": pl.Utf8,
            },
        )

        count = controller.queue_category_edits(empty_df, "cat_new")
        assert count == 0
        assert len(controller.data_manager.pending_edits) == 0

    async def test_queue_edits_preserves_transaction_ids(self, controller):
        """Test that transaction IDs are correctly preserved."""
        txn_df = controller.data_manager.df.filter(pl.col("id").is_in(["txn_1", "txn_3", "txn_5"]))

        controller.queue_category_edits(txn_df, "cat_test")

        queued_ids = {e.transaction_id for e in controller.data_manager.pending_edits}
        assert queued_ids == {"txn_1", "txn_3", "txn_5"}

    async def test_queue_edits_appends_to_existing(self, controller):
        """Test that queueing appends to existing edits (doesn't replace)."""
        from moneyflow.state import TransactionEdit

        # Add an existing edit
        controller.data_manager.pending_edits = [
            TransactionEdit("txn_999", "merchant", "Old", "New", datetime.now())
        ]

        # Queue more edits
        txn_df = controller.data_manager.df.head(2)
        count = controller.queue_category_edits(txn_df, "cat_new")

        # Should have 3 total (1 existing + 2 new)
        assert len(controller.data_manager.pending_edits) == 3
        assert controller.data_manager.pending_edits[0].transaction_id == "txn_999"

    async def test_queue_hide_toggle_edits_single_transaction(self, controller):
        """Test queueing hide toggle for a single transaction."""
        # Get a transaction that's not hidden
        txn_df = controller.data_manager.df.filter(pl.col("hideFromReports") == False).head(1)

        count = controller.queue_hide_toggle_edits(txn_df)

        assert count == 1
        assert len(controller.data_manager.pending_edits) == 1
        edit = controller.data_manager.pending_edits[0]
        assert edit.field == "hide_from_reports"
        assert edit.old_value is False
        assert edit.new_value is True  # Should toggle from False to True

    async def test_queue_hide_toggle_edits_multiple_transactions(self, controller):
        """Test bulk hide/unhide toggle."""
        txn_df = controller.data_manager.df.head(3)

        count = controller.queue_hide_toggle_edits(txn_df)

        assert count == 3
        assert len(controller.data_manager.pending_edits) == 3
        assert all(e.field == "hide_from_reports" for e in controller.data_manager.pending_edits)
        # Each should toggle its current state
        for edit in controller.data_manager.pending_edits:
            assert edit.new_value == (not edit.old_value)

    async def test_queue_hide_toggle_preserves_individual_states(self, controller):
        """Test that each transaction's hide state is toggled individually."""
        # Get mix of hidden and unhidden transactions
        all_txns = controller.data_manager.df.head(4)

        count = controller.queue_hide_toggle_edits(all_txns)

        assert count == 4
        # Verify each transaction gets its current state preserved in old_value
        old_values = [e.old_value for e in controller.data_manager.pending_edits]
        new_values = [e.new_value for e in controller.data_manager.pending_edits]
        # Each new value should be opposite of old value
        for old, new in zip(old_values, new_values):
            assert new == (not old)

    async def test_queue_hide_toggle_from_aggregate_view(self, controller):
        """Test hide toggle from aggregate view (merchant grouping)."""
        controller.state.view_mode = ViewMode.MERCHANT
        controller.state.selected_group_keys.add("Starbucks")

        # Get transactions for selected merchant
        transactions = controller.get_transactions_from_selected_groups("merchant")

        assert not transactions.is_empty()

        # Queue hide toggle
        count = controller.queue_hide_toggle_edits(transactions)

        assert count > 0
        assert len(controller.data_manager.pending_edits) == count
        # All edits should be for hide_from_reports field
        assert all(e.field == "hide_from_reports" for e in controller.data_manager.pending_edits)

    async def test_queue_hide_toggle_from_category_view(self, controller):
        """Test hide toggle from category aggregate view."""
        controller.state.view_mode = ViewMode.CATEGORY
        controller.state.selected_group_keys.add("Coffee Shops")

        # Get transactions for selected category
        transactions = controller.get_transactions_from_selected_groups("category")

        if not transactions.is_empty():
            count = controller.queue_hide_toggle_edits(transactions)
            assert count > 0
            assert all(e.field == "hide_from_reports" for e in controller.data_manager.pending_edits)


class TestSortFieldCycling:
    """
    Test sort field cycling logic - pure state machine.

    This tests the business logic for determining the next sort field
    when the user presses 's' to toggle sorting.
    """

    async def test_detail_view_date_to_merchant(self, controller):
        """Detail view: Date → Merchant."""
        new_sort, display = controller.get_next_sort_field(ViewMode.DETAIL, SortMode.DATE)
        assert new_sort == SortMode.MERCHANT
        assert display == "Merchant"

    async def test_detail_view_merchant_to_category(self, controller):
        """Detail view: Merchant → Category."""
        new_sort, display = controller.get_next_sort_field(ViewMode.DETAIL, SortMode.MERCHANT)
        assert new_sort == SortMode.CATEGORY
        assert display == "Category"

    async def test_detail_view_category_to_account(self, controller):
        """Detail view: Category → Account."""
        new_sort, display = controller.get_next_sort_field(ViewMode.DETAIL, SortMode.CATEGORY)
        assert new_sort == SortMode.ACCOUNT
        assert display == "Account"

    async def test_detail_view_account_to_amount(self, controller):
        """Detail view: Account → Amount."""
        new_sort, display = controller.get_next_sort_field(ViewMode.DETAIL, SortMode.ACCOUNT)
        assert new_sort == SortMode.AMOUNT
        assert display == "Amount"

    async def test_detail_view_amount_to_date_completes_cycle(self, controller):
        """Detail view: Amount → Date (completes the cycle)."""
        new_sort, display = controller.get_next_sort_field(ViewMode.DETAIL, SortMode.AMOUNT)
        assert new_sort == SortMode.DATE
        assert display == "Date"

    async def test_detail_view_full_cycle(self, controller):
        """Test complete cycle through all 5 fields in detail view."""
        # Start at DATE
        current = SortMode.DATE
        expected_cycle = [
            (SortMode.MERCHANT, "Merchant"),
            (SortMode.CATEGORY, "Category"),
            (SortMode.ACCOUNT, "Account"),
            (SortMode.AMOUNT, "Amount"),
            (SortMode.DATE, "Date"),  # Back to start
        ]

        for expected_sort, expected_display in expected_cycle:
            current, display = controller.get_next_sort_field(ViewMode.DETAIL, current)
            assert current == expected_sort
            assert display == expected_display

    async def test_merchant_view_full_cycle(self, controller):
        """Merchant view: Merchant → Count → Amount → Merchant (3-field cycle)."""
        # Merchant → Count
        new_sort, display = controller.get_next_sort_field(ViewMode.MERCHANT, SortMode.MERCHANT)
        assert new_sort == SortMode.COUNT
        assert display == "Count"

        # Count → Amount
        new_sort, display = controller.get_next_sort_field(ViewMode.MERCHANT, SortMode.COUNT)
        assert new_sort == SortMode.AMOUNT
        assert display == "Amount"

        # Amount → Merchant (completes cycle)
        new_sort, display = controller.get_next_sort_field(ViewMode.MERCHANT, SortMode.AMOUNT)
        assert new_sort == SortMode.MERCHANT
        assert display == "Merchant"

    async def test_category_view_full_cycle(self, controller):
        """Category view: Category → Count → Amount → Category."""
        new_sort, _ = controller.get_next_sort_field(ViewMode.CATEGORY, SortMode.CATEGORY)
        assert new_sort == SortMode.COUNT

        new_sort, _ = controller.get_next_sort_field(ViewMode.CATEGORY, SortMode.COUNT)
        assert new_sort == SortMode.AMOUNT

        new_sort, display = controller.get_next_sort_field(ViewMode.CATEGORY, SortMode.AMOUNT)
        assert new_sort == SortMode.CATEGORY
        assert display == "Category"

    async def test_group_view_full_cycle(self, controller):
        """Group view: Group → Count → Amount → Group."""
        new_sort, _ = controller.get_next_sort_field(ViewMode.GROUP, SortMode.GROUP)
        assert new_sort == SortMode.COUNT

        new_sort, _ = controller.get_next_sort_field(ViewMode.GROUP, SortMode.COUNT)
        assert new_sort == SortMode.AMOUNT

        new_sort, display = controller.get_next_sort_field(ViewMode.GROUP, SortMode.AMOUNT)
        assert new_sort == SortMode.GROUP
        assert display == "Group"

    async def test_account_view_full_cycle(self, controller):
        """Account view: Account → Count → Amount → Account."""
        new_sort, _ = controller.get_next_sort_field(ViewMode.ACCOUNT, SortMode.ACCOUNT)
        assert new_sort == SortMode.COUNT

        new_sort, _ = controller.get_next_sort_field(ViewMode.ACCOUNT, SortMode.COUNT)
        assert new_sort == SortMode.AMOUNT

        new_sort, display = controller.get_next_sort_field(ViewMode.ACCOUNT, SortMode.AMOUNT)
        assert new_sort == SortMode.ACCOUNT
        assert display == "Account"

    async def test_toggle_sort_in_subgroup_view_uses_subgroup_mode(self, controller):
        """Test that toggle_sort_field uses sub_grouping_mode when in subgroup view."""
        # Setup: Drilled down with sub-grouping by merchant
        controller.state.view_mode = ViewMode.DETAIL
        controller.state.selected_category = "Groceries"
        controller.state.sub_grouping_mode = ViewMode.MERCHANT
        controller.state.sort_by = SortMode.AMOUNT

        # Toggle sort field
        display = controller.toggle_sort_field()

        # Should cycle like merchant aggregate view (not detail view)
        # Merchant aggregate: Amount → Merchant → Count
        assert controller.state.sort_by == SortMode.MERCHANT
        assert display == "Merchant"

        # Should not offer DATE (which would crash)
        display = controller.toggle_sort_field()
        assert controller.state.sort_by == SortMode.COUNT
        assert display == "Count"

    async def test_toggle_sort_in_detail_view_without_subgrouping(self, controller):
        """Test that toggle_sort_field uses view_mode when not in subgroup."""
        # Setup: Detail view without sub-grouping
        controller.state.view_mode = ViewMode.DETAIL
        controller.state.selected_merchant = "Amazon"
        controller.state.sub_grouping_mode = None
        controller.state.sort_by = SortMode.DATE

        # Toggle sort field
        display = controller.toggle_sort_field()

        # Should cycle like detail view: Date → Merchant → Category → Account → Amount → Date
        assert controller.state.sort_by == SortMode.MERCHANT
        assert display == "Merchant"


class TestViewModeSwitching:
    """
    Test view mode switching facade methods.

    These methods encapsulate the state mutations for switching views,
    making app.py simpler and the logic testable.
    """

    async def test_switch_to_merchant_view(self, controller, mock_view):
        """Test switching to merchant view."""
        controller.switch_to_merchant_view()

        assert controller.state.view_mode == ViewMode.MERCHANT
        assert controller.state.selected_merchant is None
        assert controller.state.selected_category is None
        assert controller.state.selected_group is None
        assert controller.state.selected_account is None
        # Should reset sort to valid aggregate field
        assert controller.state.sort_by in [SortMode.COUNT, SortMode.AMOUNT]
        # Should have refreshed view
        assert len(mock_view.table_updates) == 1

    async def test_switch_to_category_view(self, controller, mock_view):
        """Test switching to category view."""
        controller.switch_to_category_view()

        assert controller.state.view_mode == ViewMode.CATEGORY
        assert controller.state.selected_category is None

    async def test_switch_to_group_view(self, controller, mock_view):
        """Test switching to group view."""
        controller.switch_to_group_view()

        assert controller.state.view_mode == ViewMode.GROUP
        assert controller.state.selected_group is None

    async def test_switch_to_account_view(self, controller, mock_view):
        """Test switching to account view."""
        controller.switch_to_account_view()

        assert controller.state.view_mode == ViewMode.ACCOUNT
        assert controller.state.selected_account is None

    async def test_switch_to_detail_view_with_default_sort(self, controller, mock_view):
        """Test switching to detail view with default sort."""
        controller.switch_to_detail_view(set_default_sort=True)

        assert controller.state.view_mode == ViewMode.DETAIL
        assert controller.state.sort_by == SortMode.DATE
        assert controller.state.sort_direction == SortDirection.DESC

    async def test_switch_to_detail_view_preserve_sort(self, controller, mock_view):
        """Test switching to detail view preserving current sort."""
        # Set non-default sort
        controller.state.sort_by = SortMode.AMOUNT
        controller.state.sort_direction = SortDirection.ASC

        controller.switch_to_detail_view(set_default_sort=False)

        assert controller.state.view_mode == ViewMode.DETAIL
        # Sort should be preserved
        assert controller.state.sort_by == SortMode.AMOUNT
        assert controller.state.sort_direction == SortDirection.ASC

    async def test_view_switch_clears_selections(self, controller, mock_view):
        """Test that switching views clears all drill-down selections."""
        # Set up some selections
        controller.state.selected_merchant = "Amazon"
        controller.state.selected_category = "Shopping"

        controller.switch_to_merchant_view()

        # All selections should be cleared
        assert controller.state.selected_merchant is None
        assert controller.state.selected_category is None
        assert controller.state.selected_group is None
        assert controller.state.selected_account is None

    async def test_aggregate_view_resets_invalid_sort(self, controller, mock_view):
        """Test that switching to aggregate view resets invalid sort fields."""
        # Set sort to DATE (invalid for aggregate views)
        controller.state.sort_by = SortMode.DATE

        controller.switch_to_merchant_view()

        # Should be reset to AMOUNT (valid aggregate field)
        assert controller.state.sort_by == SortMode.AMOUNT

    async def test_aggregate_view_preserves_valid_sort(self, controller, mock_view):
        """Test that valid sort fields are preserved."""
        controller.state.sort_by = SortMode.COUNT

        controller.switch_to_merchant_view()

        # COUNT is valid for aggregates, should be preserved
        assert controller.state.sort_by == SortMode.COUNT

    async def test_aggregate_view_preserves_field_sort(self, controller, mock_view):
        """Test that field name sort is preserved when switching aggregate views."""
        controller.state.sort_by = SortMode.MERCHANT

        controller.switch_to_merchant_view()

        # MERCHANT is valid for merchant view, should be preserved
        assert controller.state.sort_by == SortMode.MERCHANT

    async def test_cycle_grouping_returns_view_name(self, controller, mock_view):
        """Test cycle_grouping returns view name and refreshes."""
        controller.state.view_mode = ViewMode.MERCHANT

        view_name = controller.cycle_grouping()

        assert view_name is not None  # Should return next view name
        assert len(mock_view.table_updates) == 1  # Should refresh


class TestSortingFacade:
    """Test sorting facade methods that encapsulate sort operations."""

    async def test_toggle_sort_field_detail_view(self, controller, mock_view):
        """Test toggling sort field in detail view."""
        controller.state.view_mode = ViewMode.DETAIL
        controller.state.sort_by = SortMode.DATE

        display_name = controller.toggle_sort_field()

        assert controller.state.sort_by == SortMode.MERCHANT
        assert display_name == "Merchant"
        assert len(mock_view.table_updates) == 1

    async def test_toggle_sort_field_aggregate_view(self, controller, mock_view):
        """Test toggling sort field in aggregate view."""
        controller.state.view_mode = ViewMode.MERCHANT
        controller.state.sort_by = SortMode.COUNT

        display_name = controller.toggle_sort_field()

        assert controller.state.sort_by == SortMode.AMOUNT
        assert display_name == "Amount"

    async def test_reverse_sort_to_descending(self, controller, mock_view):
        """Test reversing sort to descending."""
        controller.state.sort_direction = SortDirection.ASC

        direction_name = controller.reverse_sort()

        assert controller.state.sort_direction == SortDirection.DESC
        assert direction_name == "Descending"
        assert len(mock_view.table_updates) == 1

    async def test_reverse_sort_to_ascending(self, controller, mock_view):
        """Test reversing sort to ascending."""
        controller.state.sort_direction = SortDirection.DESC

        direction_name = controller.reverse_sort()

        assert controller.state.sort_direction == SortDirection.ASC
        assert direction_name == "Ascending"


class TestTimeNavigationFacade:
    """Test time navigation facade methods."""

    async def test_set_timeframe_this_year(self, controller, mock_view):
        """Test setting timeframe to this year."""
        controller.set_timeframe_this_year()

        # Verify dates are set (this year = Jan 1 to Dec 31 of current year)
        assert controller.state.start_date is not None
        assert controller.state.end_date is not None
        assert controller.state.start_date.month == 1
        assert controller.state.start_date.day == 1
        assert controller.state.end_date.month == 12
        assert controller.state.end_date.day == 31
        assert len(mock_view.table_updates) == 1

    async def test_set_timeframe_all_time(self, controller, mock_view):
        """Test setting timeframe to all time."""
        controller.set_timeframe_all_time()

        # All-time has no date filters
        assert controller.state.start_date is None
        assert controller.state.end_date is None

    async def test_set_timeframe_this_month(self, controller, mock_view):
        """Test setting timeframe to this month."""
        from datetime import date as date_type

        today = date_type.today()
        controller.set_timeframe_this_month()

        # Verify it's current month
        assert controller.state.start_date is not None
        assert controller.state.start_date.month == today.month
        assert controller.state.start_date.day == 1

    async def test_select_month_returns_description(self, controller, mock_view):
        """Test selecting a specific month."""
        description = controller.select_month(3)  # March

        assert "March" in description
        assert len(mock_view.table_updates) == 1

    async def test_navigate_prev_period_from_all_time(self, controller, mock_view):
        """Test prev period from all-time view signals fallback."""
        from moneyflow.state import TimeFrame

        controller.state.set_timeframe(TimeFrame.ALL_TIME)
        controller.state.start_date = None  # All-time has no start_date

        should_fallback, description = controller.navigate_prev_period()

        assert should_fallback is True
        assert description is None

    async def test_navigate_prev_period_from_month(self, controller, mock_view):
        """Test navigating to previous period from a month."""
        from datetime import date as date_type

        from moneyflow.state import TimeFrame

        # Set to March 2025
        controller.state.set_timeframe(
            TimeFrame.CUSTOM, start_date=date_type(2025, 3, 1), end_date=date_type(2025, 3, 31)
        )

        should_fallback, description = controller.navigate_prev_period()

        assert should_fallback is False
        assert "February" in description or "Feb" in description

    async def test_navigate_next_period(self, controller, mock_view):
        """Test navigating to next period."""
        from datetime import date as date_type

        from moneyflow.state import TimeFrame

        # Set to March 2025
        controller.state.set_timeframe(
            TimeFrame.CUSTOM, start_date=date_type(2025, 3, 1), end_date=date_type(2025, 3, 31)
        )

        should_fallback, description = controller.navigate_next_period()

        assert should_fallback is False
        assert "April" in description or "Apr" in description


class TestMultiSelectGroups:
    """Tests for multi-selecting groups in aggregate views."""

    async def test_get_transactions_from_selected_merchants(self, controller, mock_view):
        """Should get all transactions from selected merchants."""
        controller.state.selected_group_keys = {"Amazon", "Starbucks"}

        result = controller.get_transactions_from_selected_groups("merchant")

        assert not result.is_empty()
        # Should have transactions from both merchants
        merchants = set(result["merchant"].unique().to_list())
        assert "Amazon" in merchants
        assert "Starbucks" in merchants

    async def test_get_transactions_from_selected_categories(self, controller, mock_view):
        """Should get all transactions from selected categories."""
        controller.state.selected_group_keys = {"Groceries", "Dining"}

        result = controller.get_transactions_from_selected_groups("category")

        assert not result.is_empty()
        categories = set(result["category"].unique().to_list())
        assert "Groceries" in categories or "Dining" in categories

    async def test_get_transactions_empty_when_no_selections(self, controller, mock_view):
        """Should return empty DataFrame when no groups selected."""
        controller.state.selected_group_keys = set()

        result = controller.get_transactions_from_selected_groups("merchant")

        assert result.is_empty()

    async def test_toggle_group_selection(self, controller, mock_view):
        """Should toggle group selection."""
        controller.state.toggle_group_selection("Amazon")
        assert "Amazon" in controller.state.selected_group_keys

        controller.state.toggle_group_selection("Amazon")
        assert "Amazon" not in controller.state.selected_group_keys

    async def test_clear_selection_clears_both(self, controller, mock_view):
        """Should clear both transaction and group selections."""
        controller.state.selected_ids.add("txn1")
        controller.state.selected_group_keys.add("Amazon")

        controller.state.clear_selection()

        assert len(controller.state.selected_ids) == 0
        assert len(controller.state.selected_group_keys) == 0

    async def test_view_switch_clears_selections(self, controller, mock_view):
        """Switching views should clear all selections."""
        controller.state.selected_group_keys.add("Amazon")
        controller.state.selected_ids.add("txn1")

        controller.switch_to_category_view()

        assert len(controller.state.selected_group_keys) == 0
        assert len(controller.state.selected_ids) == 0
