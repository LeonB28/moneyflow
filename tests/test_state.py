"""
Tests for state management, undo/redo, and change tracking.
"""

import pytest
import polars as pl
from datetime import date, datetime
from moneyflow.state import (
    AppState,
    ViewMode,
    SortMode,
    SortDirection,
    TimeFrame,
    TransactionEdit,
)


class TestAppState:
    """Test AppState initialization and basic operations."""

    def test_initial_state(self, app_state):
        """Test that AppState initializes with correct defaults."""
        assert app_state.view_mode == ViewMode.MERCHANT
        assert app_state.sort_by == SortMode.AMOUNT
        assert app_state.sort_direction == SortDirection.DESC
        assert app_state.time_frame == TimeFrame.THIS_YEAR
        assert app_state.transactions_df is None
        assert len(app_state.pending_edits) == 0
        assert len(app_state.selected_ids) == 0
        assert app_state.search_query == ""

    def test_set_timeframe_this_year(self, app_state):
        """Test setting timeframe to this year."""
        app_state.set_timeframe(TimeFrame.THIS_YEAR)

        assert app_state.time_frame == TimeFrame.THIS_YEAR
        assert app_state.start_date == date(date.today().year, 1, 1)
        assert app_state.end_date == date(date.today().year, 12, 31)

    def test_set_timeframe_this_month(self, app_state):
        """Test setting timeframe to this month."""
        app_state.set_timeframe(TimeFrame.THIS_MONTH)

        assert app_state.time_frame == TimeFrame.THIS_MONTH
        assert app_state.start_date.month == date.today().month
        assert app_state.start_date.day == 1

    def test_set_timeframe_custom(self, app_state):
        """Test setting custom timeframe."""
        start = date(2024, 1, 1)
        end = date(2024, 6, 30)

        app_state.set_timeframe(TimeFrame.CUSTOM, start_date=start, end_date=end)

        assert app_state.time_frame == TimeFrame.CUSTOM
        assert app_state.start_date == start
        assert app_state.end_date == end

    def test_toggle_sort(self, app_state):
        """Test sort field toggling."""
        # Start with AMOUNT
        assert app_state.sort_by == SortMode.AMOUNT
        assert app_state.sort_direction == SortDirection.DESC

        # Toggle to COUNT
        app_state.toggle_sort_field()
        assert app_state.sort_by == SortMode.COUNT

        # Toggle back to AMOUNT
        app_state.toggle_sort_field()
        assert app_state.sort_by == SortMode.AMOUNT

        # Test reverse sort
        app_state.reverse_sort()
        assert app_state.sort_direction == SortDirection.ASC

        app_state.reverse_sort()
        assert app_state.sort_direction == SortDirection.DESC


class TestChangeTracking:
    """Test edit tracking, undo, and redo functionality."""

    def test_add_edit(self, app_state):
        """Test adding a pending edit."""
        app_state.add_edit(
            transaction_id="txn_1",
            field="merchant",
            old_value="Old Merchant",
            new_value="New Merchant",
        )

        assert len(app_state.pending_edits) == 1
        assert len(app_state.undo_stack) == 1
        assert len(app_state.redo_stack) == 0

        edit = app_state.pending_edits[0]
        assert edit.transaction_id == "txn_1"
        assert edit.field == "merchant"
        assert edit.old_value == "Old Merchant"
        assert edit.new_value == "New Merchant"

    def test_multiple_edits(self, app_state):
        """Test adding multiple edits."""
        app_state.add_edit("txn_1", "merchant", "A", "B")
        app_state.add_edit("txn_2", "category", "Cat1", "Cat2")
        app_state.add_edit("txn_3", "hide_from_reports", False, True)

        assert len(app_state.pending_edits) == 3
        assert len(app_state.undo_stack) == 3

    def test_undo_single_edit(self, app_state):
        """Test undoing a single edit."""
        app_state.add_edit("txn_1", "merchant", "Old", "New")

        edit = app_state.undo_last_edit()

        assert edit is not None
        assert edit.transaction_id == "txn_1"
        assert len(app_state.pending_edits) == 0
        assert len(app_state.undo_stack) == 0
        assert len(app_state.redo_stack) == 1

    def test_undo_multiple_edits(self, app_state):
        """Test undoing multiple edits in sequence."""
        app_state.add_edit("txn_1", "merchant", "A", "B")
        app_state.add_edit("txn_2", "merchant", "C", "D")
        app_state.add_edit("txn_3", "merchant", "E", "F")

        # Undo last edit
        edit1 = app_state.undo_last_edit()
        assert edit1.transaction_id == "txn_3"
        assert len(app_state.pending_edits) == 2

        # Undo second-to-last edit
        edit2 = app_state.undo_last_edit()
        assert edit2.transaction_id == "txn_2"
        assert len(app_state.pending_edits) == 1

        # Undo first edit
        edit3 = app_state.undo_last_edit()
        assert edit3.transaction_id == "txn_1"
        assert len(app_state.pending_edits) == 0

    def test_undo_when_empty(self, app_state):
        """Test undo when there are no edits."""
        edit = app_state.undo_last_edit()
        assert edit is None

    def test_redo_after_undo(self, app_state):
        """Test redoing after an undo."""
        app_state.add_edit("txn_1", "merchant", "Old", "New")
        app_state.undo_last_edit()

        edit = app_state.redo_last_edit()

        assert edit is not None
        assert edit.transaction_id == "txn_1"
        assert len(app_state.pending_edits) == 1
        assert len(app_state.redo_stack) == 0
        assert len(app_state.undo_stack) == 1

    def test_redo_clears_after_new_edit(self, app_state):
        """Test that redo stack clears when a new edit is made."""
        app_state.add_edit("txn_1", "merchant", "A", "B")
        app_state.undo_last_edit()

        assert len(app_state.redo_stack) == 1

        # Make a new edit - should clear redo stack
        app_state.add_edit("txn_2", "merchant", "C", "D")

        assert len(app_state.redo_stack) == 0

    def test_redo_when_empty(self, app_state):
        """Test redo when there's nothing to redo."""
        edit = app_state.redo_last_edit()
        assert edit is None

    def test_has_unsaved_changes(self, app_state):
        """Test detecting unsaved changes."""
        assert not app_state.has_unsaved_changes()

        app_state.add_edit("txn_1", "merchant", "A", "B")
        assert app_state.has_unsaved_changes()

        app_state.clear_pending_edits()
        assert not app_state.has_unsaved_changes()

    def test_clear_pending_edits(self, app_state):
        """Test clearing all pending edits."""
        app_state.add_edit("txn_1", "merchant", "A", "B")
        app_state.add_edit("txn_2", "category", "C", "D")

        app_state.clear_pending_edits()

        assert len(app_state.pending_edits) == 0
        assert len(app_state.undo_stack) == 0
        assert len(app_state.redo_stack) == 0


class TestMultiSelect:
    """Test multi-selection for bulk operations."""

    def test_toggle_selection_add(self, app_state):
        """Test adding a transaction to selection."""
        app_state.toggle_selection("txn_1")

        assert "txn_1" in app_state.selected_ids
        assert len(app_state.selected_ids) == 1

    def test_toggle_selection_remove(self, app_state):
        """Test removing a transaction from selection."""
        app_state.toggle_selection("txn_1")
        app_state.toggle_selection("txn_1")

        assert "txn_1" not in app_state.selected_ids
        assert len(app_state.selected_ids) == 0

    def test_multiple_selections(self, app_state):
        """Test selecting multiple transactions."""
        app_state.toggle_selection("txn_1")
        app_state.toggle_selection("txn_2")
        app_state.toggle_selection("txn_3")

        assert len(app_state.selected_ids) == 3
        assert "txn_1" in app_state.selected_ids
        assert "txn_2" in app_state.selected_ids
        assert "txn_3" in app_state.selected_ids

    def test_clear_selection(self, app_state):
        """Test clearing all selections."""
        app_state.toggle_selection("txn_1")
        app_state.toggle_selection("txn_2")

        app_state.clear_selection()

        assert len(app_state.selected_ids) == 0


class TestDataFiltering:
    """Test filtered DataFrame operations."""

    def test_get_filtered_df_with_search(self, app_state, sample_transactions_df):
        """Test filtering by search query."""
        app_state.transactions_df = sample_transactions_df
        app_state.search_query = "starbucks"

        filtered = app_state.get_filtered_df()

        assert filtered is not None
        assert len(filtered) == 1
        assert filtered["merchant"][0] == "Starbucks"

    def test_get_filtered_df_with_dates(self, app_state, sample_transactions_df):
        """Test filtering by date range."""
        app_state.transactions_df = sample_transactions_df
        app_state.start_date = date(2024, 10, 2)
        app_state.end_date = date(2024, 10, 2)

        filtered = app_state.get_filtered_df()

        assert filtered is not None
        assert len(filtered) == 1
        assert filtered["date"][0] == date(2024, 10, 2)

    def test_get_filtered_df_no_filters(self, app_state, sample_transactions_df):
        """Test getting unfiltered DataFrame."""
        app_state.transactions_df = sample_transactions_df

        filtered = app_state.get_filtered_df()

        assert filtered is not None
        assert len(filtered) == len(sample_transactions_df)

    def test_get_filtered_df_none_when_no_data(self, app_state):
        """Test that get_filtered_df returns None when no data loaded."""
        assert app_state.transactions_df is None
        filtered = app_state.get_filtered_df()
        assert filtered is None

    def test_get_filtered_df_show_transfers_filter(self, app_state):
        """Test filtering out transfers."""
        data = [
            {
                "id": "txn_1",
                "date": date(2024, 10, 1),
                "amount": -100.00,
                "merchant": "Transfer",
                "merchant_id": "merch_1",
                "category": "Transfer",
                "category_id": "cat_1",
                "group": "Transfers",
                "account": "Checking",
                "account_id": "acc_1",
                "notes": "",
                "hideFromReports": False,
                "pending": False,
                "is_recurring": False,
            },
            {
                "id": "txn_2",
                "date": date(2024, 10, 2),
                "amount": -50.00,
                "merchant": "Store",
                "merchant_id": "merch_2",
                "category": "Shopping",
                "category_id": "cat_2",
                "group": "Shopping",
                "account": "Checking",
                "account_id": "acc_1",
                "notes": "",
                "hideFromReports": False,
                "pending": False,
                "is_recurring": False,
            },
        ]
        app_state.transactions_df = pl.DataFrame(data)

        # By default, show_transfers should be False
        app_state.show_transfers = False
        filtered = app_state.get_filtered_df()
        assert len(filtered) == 1
        assert filtered["group"][0] == "Shopping"

        # When enabled, should show all
        app_state.show_transfers = True
        filtered = app_state.get_filtered_df()
        assert len(filtered) == 2

    def test_get_filtered_df_show_hidden_filter(self, app_state):
        """Test filtering out hidden transactions."""
        data = [
            {
                "id": "txn_1",
                "date": date(2024, 10, 1),
                "amount": -100.00,
                "merchant": "Hidden Merchant",
                "merchant_id": "merch_1",
                "category": "Shopping",
                "category_id": "cat_1",
                "group": "Shopping",
                "account": "Checking",
                "account_id": "acc_1",
                "notes": "",
                "hideFromReports": True,
                "pending": False,
                "is_recurring": False,
            },
            {
                "id": "txn_2",
                "date": date(2024, 10, 2),
                "amount": -50.00,
                "merchant": "Visible Merchant",
                "merchant_id": "merch_2",
                "category": "Shopping",
                "category_id": "cat_2",
                "group": "Shopping",
                "account": "Checking",
                "account_id": "acc_1",
                "notes": "",
                "hideFromReports": False,
                "pending": False,
                "is_recurring": False,
            },
        ]
        app_state.transactions_df = pl.DataFrame(data)

        # When show_hidden is False, should filter out hidden transactions
        app_state.show_hidden = False
        filtered = app_state.get_filtered_df()
        assert len(filtered) == 1
        assert filtered["merchant"][0] == "Visible Merchant"

        # When enabled, should show all
        app_state.show_hidden = True
        filtered = app_state.get_filtered_df()
        assert len(filtered) == 2

    def test_get_filtered_df_detail_view_by_merchant(self, app_state, sample_transactions_df):
        """Test filtering in detail view by selected merchant."""
        app_state.transactions_df = sample_transactions_df
        app_state.view_mode = ViewMode.DETAIL
        app_state.selected_merchant = "Starbucks"

        filtered = app_state.get_filtered_df()

        assert len(filtered) == 1
        assert filtered["merchant"][0] == "Starbucks"

    def test_get_filtered_df_detail_view_by_category(self, app_state, sample_transactions_df):
        """Test filtering in detail view by selected category."""
        app_state.transactions_df = sample_transactions_df
        app_state.view_mode = ViewMode.DETAIL
        app_state.selected_category = "Groceries"

        filtered = app_state.get_filtered_df()

        assert len(filtered) == 1
        assert filtered["category"][0] == "Groceries"

    def test_get_filtered_df_detail_view_by_group(self, app_state, sample_transactions_df):
        """Test filtering in detail view by selected group."""
        app_state.transactions_df = sample_transactions_df
        app_state.view_mode = ViewMode.DETAIL
        app_state.selected_group = "Food & Dining"

        filtered = app_state.get_filtered_df()

        assert len(filtered) == 2
        assert all(row["group"] == "Food & Dining" for row in filtered.iter_rows(named=True))

    def test_get_filtered_df_combined_filters(self, app_state):
        """Test combining multiple filters (time + search + group filter)."""
        data = [
            {
                "id": "txn_1",
                "date": date(2024, 1, 1),
                "amount": -100.00,
                "merchant": "Starbucks Downtown",
                "merchant_id": "merch_1",
                "category": "Restaurants & Bars",
                "category_id": "cat_1",
                "group": "Food & Dining",
                "account": "Checking",
                "account_id": "acc_1",
                "notes": "",
                "hideFromReports": False,
                "pending": False,
                "is_recurring": False,
            },
            {
                "id": "txn_2",
                "date": date(2024, 1, 15),
                "amount": -50.00,
                "merchant": "Starbucks Uptown",
                "merchant_id": "merch_2",
                "category": "Restaurants & Bars",
                "category_id": "cat_1",
                "group": "Food & Dining",
                "account": "Checking",
                "account_id": "acc_1",
                "notes": "",
                "hideFromReports": False,
                "pending": False,
                "is_recurring": False,
            },
            {
                "id": "txn_3",
                "date": date(2024, 2, 1),
                "amount": -75.00,
                "merchant": "Starbucks Mall",
                "merchant_id": "merch_3",
                "category": "Restaurants & Bars",
                "category_id": "cat_1",
                "group": "Food & Dining",
                "account": "Checking",
                "account_id": "acc_1",
                "notes": "",
                "hideFromReports": False,
                "pending": False,
                "is_recurring": False,
            },
            {
                "id": "txn_4",
                "date": date(2024, 1, 20),
                "amount": 200.00,
                "merchant": "Transfer In",
                "merchant_id": "merch_4",
                "category": "Transfer",
                "category_id": "cat_2",
                "group": "Transfers",
                "account": "Checking",
                "account_id": "acc_1",
                "notes": "",
                "hideFromReports": False,
                "pending": False,
                "is_recurring": False,
            },
        ]
        app_state.transactions_df = pl.DataFrame(data)

        # Combine filters: time range (Jan only) + search (Starbucks) + no transfers
        app_state.start_date = date(2024, 1, 1)
        app_state.end_date = date(2024, 1, 31)
        app_state.search_query = "starbucks"
        app_state.show_transfers = False

        filtered = app_state.get_filtered_df()

        # Should only get Starbucks transactions from January, no transfers
        assert len(filtered) == 2
        assert all("Starbucks" in row["merchant"] for row in filtered.iter_rows(named=True))
        assert all(row["group"] != "Transfers" for row in filtered.iter_rows(named=True))


class TestNavigation:
    """Test navigation and drill-down functionality."""

    def test_drill_down_from_merchant_view(self, app_state):
        """Test drilling down from merchant view to detail view."""
        app_state.view_mode = ViewMode.MERCHANT

        app_state.drill_down("Starbucks", cursor_position=5)

        assert app_state.view_mode == ViewMode.DETAIL
        assert app_state.selected_merchant == "Starbucks"
        assert app_state.selected_category is None
        assert app_state.selected_group is None
        assert len(app_state.navigation_history) == 1
        assert app_state.navigation_history[0] == (ViewMode.MERCHANT, 5)

    def test_drill_down_from_category_view(self, app_state):
        """Test drilling down from category view to detail view."""
        app_state.view_mode = ViewMode.CATEGORY

        app_state.drill_down("Groceries", cursor_position=3)

        assert app_state.view_mode == ViewMode.DETAIL
        assert app_state.selected_category == "Groceries"
        assert app_state.selected_merchant is None
        assert app_state.selected_group is None
        assert len(app_state.navigation_history) == 1
        assert app_state.navigation_history[0] == (ViewMode.CATEGORY, 3)

    def test_drill_down_from_group_view(self, app_state):
        """Test drilling down from group view to detail view."""
        app_state.view_mode = ViewMode.GROUP

        app_state.drill_down("Food & Dining", cursor_position=10)

        assert app_state.view_mode == ViewMode.DETAIL
        assert app_state.selected_group == "Food & Dining"
        assert app_state.selected_merchant is None
        assert app_state.selected_category is None
        assert len(app_state.navigation_history) == 1
        assert app_state.navigation_history[0] == (ViewMode.GROUP, 10)

    def test_go_back_from_detail_to_previous_view(self, app_state):
        """Test going back from detail view to previous view."""
        app_state.view_mode = ViewMode.MERCHANT
        app_state.drill_down("Starbucks", cursor_position=7)

        # Now go back
        success, cursor_position = app_state.go_back()

        assert success is True
        assert cursor_position == 7
        assert app_state.view_mode == ViewMode.MERCHANT
        assert app_state.selected_merchant is None
        assert app_state.selected_category is None
        assert app_state.selected_group is None
        assert len(app_state.navigation_history) == 0

    def test_go_back_from_detail_without_history(self, app_state):
        """Test going back from detail view when no history exists."""
        # Manually put into detail view without using drill_down
        app_state.view_mode = ViewMode.DETAIL
        app_state.selected_merchant = "Starbucks"

        success, cursor_position = app_state.go_back()

        assert success is True
        assert cursor_position == 0  # Default cursor position
        assert app_state.view_mode == ViewMode.MERCHANT  # Default back to MERCHANT
        assert app_state.selected_merchant is None

    def test_go_back_from_top_level_view(self, app_state):
        """Test that go_back returns False when already at top-level view."""
        app_state.view_mode = ViewMode.MERCHANT

        success, cursor_position = app_state.go_back()

        assert success is False
        assert cursor_position == 0
        assert app_state.view_mode == ViewMode.MERCHANT

    def test_multiple_drill_downs_and_backs(self, app_state):
        """Test multiple drill-downs and back navigations."""
        # Start at merchant view
        app_state.view_mode = ViewMode.MERCHANT
        app_state.drill_down("Starbucks", cursor_position=2)
        assert app_state.view_mode == ViewMode.DETAIL

        # Go back to merchant
        success, cursor_pos = app_state.go_back()
        assert success is True
        assert cursor_pos == 2
        assert app_state.view_mode == ViewMode.MERCHANT

        # Switch to category view and drill down
        app_state.view_mode = ViewMode.CATEGORY
        app_state.drill_down("Groceries", cursor_position=8)
        assert app_state.view_mode == ViewMode.DETAIL
        assert app_state.selected_category == "Groceries"

        # Go back to category view
        success, cursor_pos = app_state.go_back()
        assert success is True
        assert cursor_pos == 8
        assert app_state.view_mode == ViewMode.CATEGORY
        assert app_state.selected_category is None


class TestBreadcrumbs:
    """Test breadcrumb generation for navigation."""

    def test_breadcrumb_merchant_view(self, app_state):
        """Test breadcrumb for merchant view."""
        app_state.view_mode = ViewMode.MERCHANT
        breadcrumb = app_state.get_breadcrumb()
        assert "Merchants" in breadcrumb

    def test_breadcrumb_category_view(self, app_state):
        """Test breadcrumb for category view."""
        app_state.view_mode = ViewMode.CATEGORY
        breadcrumb = app_state.get_breadcrumb()
        assert "Categories" in breadcrumb

    def test_breadcrumb_group_view(self, app_state):
        """Test breadcrumb for group view."""
        app_state.view_mode = ViewMode.GROUP
        breadcrumb = app_state.get_breadcrumb()
        assert "Groups" in breadcrumb

    def test_breadcrumb_detail_view_merchant(self, app_state):
        """Test breadcrumb for detail view drilled down from merchant."""
        app_state.view_mode = ViewMode.DETAIL
        app_state.selected_merchant = "Starbucks"

        breadcrumb = app_state.get_breadcrumb()

        assert "Merchants" in breadcrumb
        assert "Starbucks" in breadcrumb

    def test_breadcrumb_detail_view_category(self, app_state):
        """Test breadcrumb for detail view drilled down from category."""
        app_state.view_mode = ViewMode.DETAIL
        app_state.selected_category = "Groceries"

        breadcrumb = app_state.get_breadcrumb()

        assert "Categories" in breadcrumb
        assert "Groceries" in breadcrumb

    def test_breadcrumb_detail_view_group(self, app_state):
        """Test breadcrumb for detail view drilled down from group."""
        app_state.view_mode = ViewMode.DETAIL
        app_state.selected_group = "Food & Dining"

        breadcrumb = app_state.get_breadcrumb()

        assert "Groups" in breadcrumb
        assert "Food & Dining" in breadcrumb

    def test_breadcrumb_detail_view_no_selection(self, app_state):
        """Test breadcrumb for detail view with no selection."""
        app_state.view_mode = ViewMode.DETAIL

        breadcrumb = app_state.get_breadcrumb()

        assert "Transactions" in breadcrumb

    def test_breadcrumb_with_this_year_timeframe(self, app_state):
        """Test breadcrumb includes year when in THIS_YEAR mode."""
        app_state.view_mode = ViewMode.MERCHANT
        app_state.set_timeframe(TimeFrame.THIS_YEAR)

        breadcrumb = app_state.get_breadcrumb()

        assert "Year" in breadcrumb
        assert str(date.today().year) in breadcrumb

    def test_breadcrumb_with_this_month_timeframe(self, app_state):
        """Test breadcrumb includes month when in THIS_MONTH mode."""
        app_state.view_mode = ViewMode.MERCHANT
        app_state.set_timeframe(TimeFrame.THIS_MONTH)

        breadcrumb = app_state.get_breadcrumb()

        # Should include month name
        month_name = date.today().strftime("%B")
        assert month_name in breadcrumb
        assert str(date.today().year) in breadcrumb

    def test_breadcrumb_with_custom_single_month(self, app_state):
        """Test breadcrumb for custom timeframe spanning a single month."""
        app_state.view_mode = ViewMode.MERCHANT
        app_state.set_timeframe(
            TimeFrame.CUSTOM,
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 31)
        )

        breadcrumb = app_state.get_breadcrumb()

        assert "March" in breadcrumb
        assert "2024" in breadcrumb

    def test_breadcrumb_with_custom_date_range(self, app_state):
        """Test breadcrumb for custom timeframe spanning multiple months."""
        app_state.view_mode = ViewMode.MERCHANT
        app_state.set_timeframe(
            TimeFrame.CUSTOM,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30)
        )

        breadcrumb = app_state.get_breadcrumb()

        assert "2024-01-01" in breadcrumb
        assert "2024-06-30" in breadcrumb
        assert "to" in breadcrumb


class TestTimeFrameEdgeCases:
    """Test edge cases in time frame handling."""

    def test_set_timeframe_all_time(self, app_state):
        """Test setting timeframe to ALL_TIME clears dates."""
        # First set some dates
        app_state.set_timeframe(
            TimeFrame.CUSTOM,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31)
        )
        assert app_state.start_date is not None
        assert app_state.end_date is not None

        # Now set to ALL_TIME
        app_state.set_timeframe(TimeFrame.ALL_TIME)

        assert app_state.time_frame == TimeFrame.ALL_TIME
        assert app_state.start_date is None
        assert app_state.end_date is None

    def test_set_timeframe_this_month_december(self, app_state):
        """Test setting timeframe to THIS_MONTH handles December correctly."""
        # Mock today being in December - must mock in time_navigator module
        from unittest.mock import patch
        with patch('moneyflow.time_navigator.date') as mock_date:
            mock_date.today.return_value = date(2024, 12, 15)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            app_state.set_timeframe(TimeFrame.THIS_MONTH)

            assert app_state.start_date == date(2024, 12, 1)
            assert app_state.end_date == date(2024, 12, 31)

    def test_set_timeframe_this_month_february_leap_year(self, app_state):
        """Test THIS_MONTH handles February in a leap year."""
        from unittest.mock import patch
        with patch('moneyflow.time_navigator.date') as mock_date:
            mock_date.today.return_value = date(2024, 2, 15)  # 2024 is leap year
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            app_state.set_timeframe(TimeFrame.THIS_MONTH)

            assert app_state.start_date == date(2024, 2, 1)
            assert app_state.end_date == date(2024, 2, 29)  # Leap year has 29 days

    def test_set_timeframe_this_month_february_non_leap_year(self, app_state):
        """Test THIS_MONTH handles February in a non-leap year."""
        from unittest.mock import patch
        with patch('moneyflow.time_navigator.date') as mock_date:
            mock_date.today.return_value = date(2023, 2, 15)  # 2023 is not leap year
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            app_state.set_timeframe(TimeFrame.THIS_MONTH)

            assert app_state.start_date == date(2023, 2, 1)
            assert app_state.end_date == date(2023, 2, 28)  # Non-leap year has 28 days
