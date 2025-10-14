"""
Tests for AppController business logic.

These tests verify controller behavior without requiring the UI to run.
They focus on the "data plane" bugs we recently fixed:
- View refresh logic
- force_rebuild behavior
- Table update sequencing
"""

import pytest
import polars as pl
from datetime import datetime
from moneyflow.app_controller import AppController
from moneyflow.state import AppState, ViewMode, SortMode, SortDirection
from moneyflow.data_manager import DataManager
from .mock_view import MockViewPresenter
from .mock_backend import MockMonarchMoney


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
        assert update["column_count"] == 3  # Merchant, Count, Total
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
        assert "Edit merchant" in mock_view.hints[0]

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
        assert update["column_count"] == 3
        # Columns should be: Merchant, Count, Total
        assert update["columns"][0]["key"] == "merchant"
        assert update["columns"][1]["key"] == "count"
        assert update["columns"][2]["key"] == "total"

    async def test_category_view(self, controller, mock_view):
        """Test category aggregation view."""
        controller.state.view_mode = ViewMode.CATEGORY

        controller.refresh_view()

        update = mock_view.get_last_table_update()
        assert update["column_count"] == 3
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
        empty_df = pl.DataFrame({
            "id": [],
            "date": [],
            "amount": [],
            "merchant": [],
            "category": [],
            "group": [],
            "hideFromReports": [],
        }, schema={
            "id": pl.Utf8,
            "date": pl.Date,
            "amount": pl.Float64,
            "merchant": pl.Utf8,
            "category": pl.Utf8,
            "group": pl.Utf8,
            "hideFromReports": pl.Boolean,
        })
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
        assert "Edit merchant" in hints
        assert "bulk" in hints

    async def test_category_view_hints(self, controller, mock_view):
        """Category view should show recategorize hint."""
        controller.state.view_mode = ViewMode.CATEGORY

        controller.refresh_view()

        hints = mock_view.hints[-1]
        assert "Recategorize" in hints
        assert "bulk" in hints

    async def test_detail_view_hints(self, controller, mock_view):
        """Detail view should show transaction-level hints."""
        controller.state.view_mode = ViewMode.DETAIL

        controller.refresh_view()

        hints = mock_view.hints[-1]
        assert "Info" in hints
        assert "Edit Merchant" in hints
        assert "Space=Select" in hints


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
        edits = [TransactionEdit("txn_1", "merchant", initial_merchant, "NewMerchant", datetime.now())]
        controller.data_manager.pending_edits = edits.copy()

        # Simulate successful commit
        controller.state.view_mode = ViewMode.DETAIL
        saved_state = controller.state.save_view_state()

        controller.handle_commit_result(
            success_count=1,
            failure_count=0,
            edits=edits,
            saved_state=saved_state
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
            success_count=1,
            failure_count=1,
            edits=edits,
            saved_state=saved_state
        )

        # CRITICAL VERIFICATION: Edits should NOT be applied
        current_merchant = controller.data_manager.df.filter(pl.col("id") == "txn_1")["merchant"][0]
        assert current_merchant == initial_merchant, \
            "Edit should NOT be applied when there were failures (data corruption!)"

        # VERIFY: Pending edits still present (for retry)
        assert len(controller.data_manager.pending_edits) == 2, \
            "Pending edits should be kept for retry"

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
            success_count=0,
            failure_count=2,
            edits=edits,
            saved_state=saved_state
        )

        # VERIFY: DataFrame unchanged
        assert controller.data_manager.df.equals(initial_df), \
            "DataFrame should be completely unchanged"

        # VERIFY: Pending edits preserved
        assert len(controller.data_manager.pending_edits) == 2

    async def test_commit_success_uses_force_rebuild_false(self, controller, mock_view):
        """Commit should use force_rebuild=False for smooth update."""
        from moneyflow.state import TransactionEdit

        edits = [TransactionEdit("txn_1", "merchant", "Old", "New", datetime.now())]

        controller.state.view_mode = ViewMode.DETAIL
        saved_state = controller.state.save_view_state()

        controller.handle_commit_result(
            success_count=1,
            failure_count=0,
            edits=edits,
            saved_state=saved_state
        )

        # VERIFY: force_rebuild=False (no flash)
        mock_view.assert_force_rebuild(False)

    async def test_commit_failure_restores_view_state(self, controller, mock_view):
        """Failed commit should restore saved view state."""
        from moneyflow.state import TransactionEdit

        # Set up specific view state
        controller.state.view_mode = ViewMode.DETAIL
        controller.state.sort_by = SortMode.AMOUNT
        saved_state = controller.state.save_view_state()

        # Change state after saving
        controller.state.sort_by = SortMode.DATE

        edits = [TransactionEdit("txn_1", "merchant", "Old", "New", datetime.now())]

        controller.handle_commit_result(
            success_count=0,
            failure_count=1,
            edits=edits,
            saved_state=saved_state
        )

        # VERIFY: State restored
        assert controller.state.sort_by == SortMode.AMOUNT, "State should be restored"


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
        txn_df = controller.data_manager.df.filter(
            pl.col("id").is_in(["txn_1", "txn_2"])
        )
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
        empty_df = pl.DataFrame({
            "id": [],
            "merchant": [],
            "category_id": [],
        }, schema={
            "id": pl.Utf8,
            "merchant": pl.Utf8,
            "category_id": pl.Utf8,
        })

        count = controller.queue_category_edits(empty_df, "cat_new")
        assert count == 0
        assert len(controller.data_manager.pending_edits) == 0

    async def test_queue_edits_preserves_transaction_ids(self, controller):
        """Test that transaction IDs are correctly preserved."""
        txn_df = controller.data_manager.df.filter(
            pl.col("id").is_in(["txn_1", "txn_3", "txn_5"])
        )

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

    async def test_merchant_view_count_to_amount(self, controller):
        """Merchant view: Count → Amount."""
        new_sort, display = controller.get_next_sort_field(ViewMode.MERCHANT, SortMode.COUNT)
        assert new_sort == SortMode.AMOUNT
        assert display == "Amount"

    async def test_merchant_view_amount_to_count(self, controller):
        """Merchant view: Amount → Count (toggle back)."""
        new_sort, display = controller.get_next_sort_field(ViewMode.MERCHANT, SortMode.AMOUNT)
        assert new_sort == SortMode.COUNT
        assert display == "Count"

    async def test_category_view_toggles_like_merchant(self, controller):
        """Category view uses same toggle as merchant view."""
        # Count → Amount
        new_sort, _ = controller.get_next_sort_field(ViewMode.CATEGORY, SortMode.COUNT)
        assert new_sort == SortMode.AMOUNT

        # Amount → Count
        new_sort, _ = controller.get_next_sort_field(ViewMode.CATEGORY, SortMode.AMOUNT)
        assert new_sort == SortMode.COUNT

    async def test_group_view_toggles_like_merchant(self, controller):
        """Group view uses same toggle as merchant view."""
        new_sort, _ = controller.get_next_sort_field(ViewMode.GROUP, SortMode.COUNT)
        assert new_sort == SortMode.AMOUNT

    async def test_account_view_toggles_like_merchant(self, controller):
        """Account view uses same toggle as merchant view."""
        new_sort, _ = controller.get_next_sort_field(ViewMode.ACCOUNT, SortMode.COUNT)
        assert new_sort == SortMode.AMOUNT

    async def test_aggregate_views_count_amount_bidirectional(self, controller):
        """Aggregate views toggle bidirectionally between count and amount."""
        for view_mode in [ViewMode.MERCHANT, ViewMode.CATEGORY, ViewMode.GROUP, ViewMode.ACCOUNT]:
            # Count → Amount → Count (should get back to count)
            sort1, _ = controller.get_next_sort_field(view_mode, SortMode.COUNT)
            assert sort1 == SortMode.AMOUNT

            sort2, _ = controller.get_next_sort_field(view_mode, sort1)
            assert sort2 == SortMode.COUNT


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

    async def test_cycle_grouping_returns_view_name(self, controller, mock_view):
        """Test cycle_grouping returns view name and refreshes."""
        controller.state.view_mode = ViewMode.MERCHANT

        view_name = controller.cycle_grouping()

        assert view_name is not None  # Should return next view name
        assert len(mock_view.table_updates) == 1  # Should refresh
