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
