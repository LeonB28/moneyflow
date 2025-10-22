"""
Tests for state management, undo/redo, and change tracking.
"""

from datetime import date

import polars as pl

from moneyflow.state import (
    AppState,
    NavigationState,
    SortDirection,
    SortMode,
    TimeFrame,
    ViewMode,
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

    def test_get_filtered_df_show_hidden_filter_in_aggregate_view(self, app_state):
        """Test filtering out hidden transactions in aggregate views."""
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
        app_state.view_mode = ViewMode.MERCHANT  # Aggregate view

        # When show_hidden is False in aggregate view, should filter out hidden transactions
        app_state.show_hidden = False
        filtered = app_state.get_filtered_df()
        assert len(filtered) == 1
        assert filtered["merchant"][0] == "Visible Merchant"

        # When enabled, should show all
        app_state.show_hidden = True
        filtered = app_state.get_filtered_df()
        assert len(filtered) == 2

    def test_get_filtered_df_show_hidden_in_detail_view(self, app_state):
        """Test that hidden transactions are ALWAYS shown in detail views."""
        data = [
            {
                "id": "txn_1",
                "date": date(2024, 10, 1),
                "amount": -100.00,
                "merchant": "Amazon",
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
                "merchant": "Amazon",
                "merchant_id": "merch_1",
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
        app_state.view_mode = ViewMode.DETAIL
        app_state.selected_merchant = "Amazon"

        # In detail view, hidden transactions should ALWAYS be shown
        # even when show_hidden is False
        app_state.show_hidden = False
        filtered = app_state.get_filtered_df()
        assert len(filtered) == 2  # Both transactions shown
        assert filtered["hideFromReports"].to_list() == [True, False]

        # When enabled, should still show all
        app_state.show_hidden = True
        filtered = app_state.get_filtered_df()
        assert len(filtered) == 2

    def test_get_filtered_df_hidden_in_drilled_down_category(self, app_state):
        """Test that hidden transactions are shown when drilling down into a category."""
        data = [
            {
                "id": "txn_1",
                "date": date(2024, 10, 1),
                "amount": -100.00,
                "merchant": "Store A",
                "merchant_id": "merch_1",
                "category": "Groceries",
                "category_id": "cat_1",
                "group": "Food & Dining",
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
                "merchant": "Store B",
                "merchant_id": "merch_2",
                "category": "Groceries",
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
                "date": date(2024, 10, 3),
                "amount": -25.00,
                "merchant": "Store C",
                "merchant_id": "merch_3",
                "category": "Gas",
                "category_id": "cat_2",
                "group": "Transportation",
                "account": "Checking",
                "account_id": "acc_1",
                "notes": "",
                "hideFromReports": True,
                "pending": False,
                "is_recurring": False,
            },
        ]
        app_state.transactions_df = pl.DataFrame(data)
        app_state.view_mode = ViewMode.DETAIL
        app_state.selected_category = "Groceries"
        app_state.show_hidden = False

        # Should show both Groceries transactions (including hidden one)
        filtered = app_state.get_filtered_df()
        assert len(filtered) == 2
        assert set(filtered["merchant"].to_list()) == {"Store A", "Store B"}
        # One is hidden, one is not
        hidden_count = sum(filtered["hideFromReports"].to_list())
        assert hidden_count == 1

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

        app_state.drill_down("Starbucks", cursor_position=5, scroll_y=150.5)

        assert app_state.view_mode == ViewMode.DETAIL
        assert app_state.selected_merchant == "Starbucks"
        assert app_state.selected_category is None
        assert app_state.selected_group is None
        assert len(app_state.navigation_history) == 1
        # Navigation history saves NavigationState object
        nav = app_state.navigation_history[0]
        assert nav.view_mode == ViewMode.MERCHANT
        assert nav.cursor_position == 5
        assert nav.scroll_y == 150.5
        assert nav.sort_by == SortMode.AMOUNT
        assert nav.sort_direction == SortDirection.DESC

    def test_drill_down_from_category_view(self, app_state):
        """Test drilling down from category view to detail view."""
        app_state.view_mode = ViewMode.CATEGORY

        app_state.drill_down("Groceries", cursor_position=3, scroll_y=200.0)

        assert app_state.view_mode == ViewMode.DETAIL
        assert app_state.selected_category == "Groceries"
        assert app_state.selected_merchant is None
        assert app_state.selected_group is None
        assert len(app_state.navigation_history) == 1
        # Navigation history saves NavigationState object
        nav = app_state.navigation_history[0]
        assert nav.view_mode == ViewMode.CATEGORY
        assert nav.cursor_position == 3
        assert nav.scroll_y == 200.0
        assert nav.sort_by == SortMode.AMOUNT
        assert nav.sort_direction == SortDirection.DESC

    def test_drill_down_from_group_view(self, app_state):
        """Test drilling down from group view to detail view."""
        app_state.view_mode = ViewMode.GROUP

        app_state.drill_down("Food & Dining", cursor_position=10, scroll_y=75.25)

        assert app_state.view_mode == ViewMode.DETAIL
        assert app_state.selected_group == "Food & Dining"
        assert app_state.selected_merchant is None
        assert app_state.selected_category is None
        assert len(app_state.navigation_history) == 1
        # Navigation history saves NavigationState object
        nav = app_state.navigation_history[0]
        assert nav.view_mode == ViewMode.GROUP
        assert nav.cursor_position == 10
        assert nav.scroll_y == 75.25
        assert nav.sort_by == SortMode.AMOUNT
        assert nav.sort_direction == SortDirection.DESC

    def test_go_back_from_detail_to_previous_view(self, app_state):
        """Test going back from detail view to previous view."""
        app_state.view_mode = ViewMode.MERCHANT
        app_state.drill_down("Starbucks", cursor_position=7, scroll_y=300.5)

        # Now go back
        success, cursor_position, scroll_y = app_state.go_back()

        assert success is True
        assert cursor_position == 7
        assert scroll_y == 300.5
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

        success, cursor_position, scroll_y = app_state.go_back()

        assert success is True
        assert cursor_position == 0  # Default cursor position
        assert scroll_y == 0.0  # Default scroll position
        assert app_state.view_mode == ViewMode.MERCHANT  # Default back to MERCHANT
        assert app_state.selected_merchant is None

    def test_go_back_from_top_level_view(self, app_state):
        """Test that go_back returns False when already at top-level view."""
        app_state.view_mode = ViewMode.MERCHANT

        success, cursor_position, scroll_y = app_state.go_back()

        assert success is False
        assert cursor_position == 0
        assert scroll_y == 0.0
        assert app_state.view_mode == ViewMode.MERCHANT

    def test_multiple_drill_downs_and_backs(self, app_state):
        """Test multiple drill-downs and back navigations with scroll positions."""
        # Start at merchant view
        app_state.view_mode = ViewMode.MERCHANT
        app_state.drill_down("Starbucks", cursor_position=2, scroll_y=100.0)
        assert app_state.view_mode == ViewMode.DETAIL

        # Go back to merchant
        success, cursor_pos, scroll_y = app_state.go_back()
        assert success is True
        assert cursor_pos == 2
        assert scroll_y == 100.0
        assert app_state.view_mode == ViewMode.MERCHANT

        # Switch to category view and drill down
        app_state.view_mode = ViewMode.CATEGORY
        app_state.drill_down("Groceries", cursor_position=8, scroll_y=250.5)
        assert app_state.view_mode == ViewMode.DETAIL
        assert app_state.selected_category == "Groceries"

        # Go back to category view
        success, cursor_pos, scroll_y = app_state.go_back()
        assert success is True
        assert cursor_pos == 8
        assert scroll_y == 250.5
        assert app_state.view_mode == ViewMode.CATEGORY
        assert app_state.selected_category is None

    def test_drill_down_resets_count_sort_to_date(self, app_state):
        """Test that drilling down from aggregate view resets COUNT sort to DATE."""
        app_state.view_mode = ViewMode.MERCHANT
        app_state.sort_by = SortMode.COUNT
        app_state.sort_direction = SortDirection.DESC

        app_state.drill_down("Starbucks", cursor_position=5, scroll_y=100.0)

        # Should reset to DATE sort since detail views don't have 'count' column
        assert app_state.sort_by == SortMode.DATE
        assert app_state.sort_direction == SortDirection.DESC
        assert app_state.view_mode == ViewMode.DETAIL

    def test_drill_down_preserves_amount_sort(self, app_state):
        """Test that drilling down preserves AMOUNT sort (valid in both views)."""
        app_state.view_mode = ViewMode.MERCHANT
        app_state.sort_by = SortMode.AMOUNT
        app_state.sort_direction = SortDirection.ASC

        app_state.drill_down("Amazon", cursor_position=3, scroll_y=50.0)

        # AMOUNT is valid in detail views, should be preserved
        assert app_state.sort_by == SortMode.AMOUNT
        assert app_state.sort_direction == SortDirection.ASC

    def test_go_back_restores_count_sort_ascending(self, app_state):
        """Test that go_back restores COUNT sort ASC after drilling down."""
        # Start in Merchant view with COUNT sort ascending
        app_state.view_mode = ViewMode.MERCHANT
        app_state.sort_by = SortMode.COUNT
        app_state.sort_direction = SortDirection.ASC

        # Drill down - should switch to DATE sort for detail view
        app_state.drill_down("Starbucks", cursor_position=5, scroll_y=100.0)
        assert app_state.sort_by == SortMode.DATE  # Changed for detail view

        # Go back - should restore COUNT ASC
        success, cursor, scroll = app_state.go_back()
        assert success is True
        assert app_state.sort_by == SortMode.COUNT
        assert app_state.sort_direction == SortDirection.ASC
        assert app_state.view_mode == ViewMode.MERCHANT

    def test_go_back_restores_amount_sort_descending(self, app_state):
        """Test that go_back restores AMOUNT sort DESC after drilling down."""
        # Start in Category view with AMOUNT sort descending
        app_state.view_mode = ViewMode.CATEGORY
        app_state.sort_by = SortMode.AMOUNT
        app_state.sort_direction = SortDirection.DESC

        # Drill down
        app_state.drill_down("Groceries", cursor_position=10, scroll_y=250.0)
        assert app_state.sort_by == SortMode.AMOUNT  # Preserved for detail view

        # Go back - should restore AMOUNT DESC
        success, cursor, scroll = app_state.go_back()
        assert success is True
        assert app_state.sort_by == SortMode.AMOUNT
        assert app_state.sort_direction == SortDirection.DESC
        assert app_state.view_mode == ViewMode.CATEGORY

    def test_go_back_restores_merchant_sort(self, app_state):
        """Test that go_back restores MERCHANT field sort after drilling down."""
        # Start in Merchant view sorted by merchant name
        app_state.view_mode = ViewMode.MERCHANT
        app_state.sort_by = SortMode.MERCHANT
        app_state.sort_direction = SortDirection.ASC

        # Drill down
        app_state.drill_down("Amazon", cursor_position=3, scroll_y=50.0)

        # Go back - should restore MERCHANT sort
        success, cursor, scroll = app_state.go_back()
        assert success is True
        assert app_state.sort_by == SortMode.MERCHANT
        assert app_state.sort_direction == SortDirection.ASC

    def test_multiple_drill_downs_preserve_each_sort(self, app_state):
        """Test that multiple drill-downs preserve sort state at each level."""
        # Start in Merchant view with COUNT sort
        app_state.view_mode = ViewMode.MERCHANT
        app_state.sort_by = SortMode.COUNT
        app_state.sort_direction = SortDirection.ASC

        # First drill down
        app_state.drill_down("Starbucks", cursor_position=5, scroll_y=100.0)
        assert app_state.sort_by == SortMode.DATE

        # Go back once
        app_state.go_back()
        assert app_state.sort_by == SortMode.COUNT
        assert app_state.sort_direction == SortDirection.ASC

        # Now switch to Category view with AMOUNT DESC
        app_state.view_mode = ViewMode.CATEGORY
        app_state.sort_by = SortMode.AMOUNT
        app_state.sort_direction = SortDirection.DESC

        # Drill down from Category
        app_state.drill_down("Groceries", cursor_position=2, scroll_y=50.0)

        # Go back - should restore Category view's AMOUNT DESC
        app_state.go_back()
        assert app_state.view_mode == ViewMode.CATEGORY
        assert app_state.sort_by == SortMode.AMOUNT
        assert app_state.sort_direction == SortDirection.DESC


class TestBreadcrumbs:
    """Test breadcrumb generation for navigation."""

    def test_breadcrumb_merchant_view(self, app_state):
        """Test breadcrumb for merchant view."""
        app_state.view_mode = ViewMode.MERCHANT
        breadcrumb = app_state.get_breadcrumb()
        assert "Merchants" in breadcrumb

    def test_breadcrumb_with_custom_labels(self, app_state):
        """Test breadcrumb uses custom display labels from backend."""
        app_state.view_mode = ViewMode.MERCHANT

        # Amazon backend labels
        amazon_labels = {"merchant": "Item Name", "account": "Order", "accounts": "Orders"}
        breadcrumb = app_state.get_breadcrumb(amazon_labels)

        assert "Item Names" in breadcrumb  # Pluralized
        assert "Merchants" not in breadcrumb

    def test_breadcrumb_account_view_with_custom_labels(self, app_state):
        """Test breadcrumb for account view with custom labels."""
        app_state.view_mode = ViewMode.ACCOUNT

        amazon_labels = {"merchant": "Item Name", "account": "Order", "accounts": "Orders"}
        breadcrumb = app_state.get_breadcrumb(amazon_labels)

        assert "Orders" in breadcrumb
        assert "Accounts" not in breadcrumb

    def test_breadcrumb_drilled_account_with_custom_labels(self, app_state):
        """Test breadcrumb when drilled into account with custom labels."""
        app_state.view_mode = ViewMode.DETAIL
        app_state.selected_account = "113-1234567-8901234"

        amazon_labels = {"merchant": "Item Name", "account": "Order", "accounts": "Orders"}
        breadcrumb = app_state.get_breadcrumb(amazon_labels)

        assert "Orders" in breadcrumb
        assert "113-1234567-8901234" in breadcrumb
        assert "Accounts" not in breadcrumb

    def test_breadcrumb_sub_grouping_with_custom_labels(self, app_state):
        """Test breadcrumb with sub-grouping uses custom labels."""
        app_state.view_mode = ViewMode.DETAIL
        app_state.selected_account = "113-1234567-8901234"
        app_state.sub_grouping_mode = ViewMode.MERCHANT

        amazon_labels = {"merchant": "Item Name", "account": "Order", "accounts": "Orders"}
        breadcrumb = app_state.get_breadcrumb(amazon_labels)

        assert "(by Item Name)" in breadcrumb
        assert "(by Merchant)" not in breadcrumb

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
            TimeFrame.CUSTOM, start_date=date(2024, 3, 1), end_date=date(2024, 3, 31)
        )

        breadcrumb = app_state.get_breadcrumb()

        assert "March" in breadcrumb
        assert "2024" in breadcrumb

    def test_breadcrumb_with_custom_date_range(self, app_state):
        """Test breadcrumb for custom timeframe spanning multiple months."""
        app_state.view_mode = ViewMode.MERCHANT
        app_state.set_timeframe(
            TimeFrame.CUSTOM, start_date=date(2024, 1, 1), end_date=date(2024, 6, 30)
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
            TimeFrame.CUSTOM, start_date=date(2024, 1, 1), end_date=date(2024, 12, 31)
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

        with patch("moneyflow.time_navigator.date") as mock_date:
            mock_date.today.return_value = date(2024, 12, 15)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            app_state.set_timeframe(TimeFrame.THIS_MONTH)

            assert app_state.start_date == date(2024, 12, 1)
            assert app_state.end_date == date(2024, 12, 31)

    def test_set_timeframe_this_month_february_leap_year(self, app_state):
        """Test THIS_MONTH handles February in a leap year."""
        from unittest.mock import patch

        with patch("moneyflow.time_navigator.date") as mock_date:
            mock_date.today.return_value = date(2024, 2, 15)  # 2024 is leap year
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            app_state.set_timeframe(TimeFrame.THIS_MONTH)

            assert app_state.start_date == date(2024, 2, 1)
            assert app_state.end_date == date(2024, 2, 29)  # Leap year has 29 days

    def test_set_timeframe_this_month_february_non_leap_year(self, app_state):
        """Test THIS_MONTH handles February in a non-leap year."""
        from unittest.mock import patch

        with patch("moneyflow.time_navigator.date") as mock_date:
            mock_date.today.return_value = date(2023, 2, 15)  # 2023 is not leap year
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)

            app_state.set_timeframe(TimeFrame.THIS_MONTH)

            assert app_state.start_date == date(2023, 2, 1)
            assert app_state.end_date == date(2023, 2, 28)  # Non-leap year has 28 days


class TestSubGrouping:
    """Tests for sub-grouping within drilled-down views."""

    def test_is_drilled_down_with_merchant(self):
        """Should return True when merchant is selected."""
        state = AppState()
        state.selected_merchant = "Amazon"
        assert state.is_drilled_down() is True

    def test_is_drilled_down_with_category(self):
        """Should return True when category is selected."""
        state = AppState()
        state.selected_category = "Groceries"
        assert state.is_drilled_down() is True

    def test_is_drilled_down_no_selection(self):
        """Should return False with no selections."""
        state = AppState()
        assert state.is_drilled_down() is False

    def test_cycle_sub_grouping_from_merchant_includes_category(self):
        """When drilled into Merchant, should offer Category sub-grouping."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"

        result = state.cycle_sub_grouping()

        # First cycle should go to Category (Merchant is excluded)
        assert state.sub_grouping_mode == ViewMode.CATEGORY
        assert result == "by Category"

    def test_cycle_sub_grouping_from_category_includes_merchant(self):
        """When drilled into Category, should offer Merchant sub-grouping."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_category = "Groceries"

        result = state.cycle_sub_grouping()

        # First cycle should go to Merchant (Category is excluded)
        assert state.sub_grouping_mode == ViewMode.MERCHANT
        assert result == "by Merchant"

    def test_cycle_sub_grouping_full_cycle_from_merchant(self):
        """Should cycle through all modes (excluding Merchant) then back."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"

        # Cycle: Category → Group → Account → Detail → Category
        assert state.cycle_sub_grouping() == "by Category"
        assert state.sub_grouping_mode == ViewMode.CATEGORY

        assert state.cycle_sub_grouping() == "by Group"
        assert state.sub_grouping_mode == ViewMode.GROUP

        assert state.cycle_sub_grouping() == "by Account"
        assert state.sub_grouping_mode == ViewMode.ACCOUNT

        assert state.cycle_sub_grouping() == "Detail"
        assert state.sub_grouping_mode is None

        # Back to Category
        assert state.cycle_sub_grouping() == "by Category"
        assert state.sub_grouping_mode == ViewMode.CATEGORY

    def test_cycle_sub_grouping_full_cycle_from_category(self):
        """Should cycle through all modes (excluding Category) then back."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_category = "Groceries"

        # Cycle: Merchant → Group → Account → Detail → Merchant
        assert state.cycle_sub_grouping() == "by Merchant"
        assert state.sub_grouping_mode == ViewMode.MERCHANT

        assert state.cycle_sub_grouping() == "by Group"
        assert state.sub_grouping_mode == ViewMode.GROUP

        assert state.cycle_sub_grouping() == "by Account"
        assert state.sub_grouping_mode == ViewMode.ACCOUNT

        assert state.cycle_sub_grouping() == "Detail"
        assert state.sub_grouping_mode is None

        # Back to Merchant
        assert state.cycle_sub_grouping() == "by Merchant"
        assert state.sub_grouping_mode == ViewMode.MERCHANT

    def test_cycle_grouping_delegates_to_sub_grouping_when_drilled_down(self):
        """When drilled down, cycle_grouping should delegate to sub-grouping."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"

        result = state.cycle_grouping()

        # Should have called cycle_sub_grouping
        assert state.sub_grouping_mode == ViewMode.CATEGORY
        assert result == "by Category"

    def test_cycle_grouping_works_normally_when_not_drilled_down(self):
        """When not drilled down, should cycle top-level views."""
        state = AppState()
        state.view_mode = ViewMode.MERCHANT

        result = state.cycle_grouping()

        # Should cycle to Category view
        assert state.view_mode == ViewMode.CATEGORY
        assert result == "Categories"

    def test_cycle_sub_grouping_resets_date_sort_to_amount(self):
        """When cycling from detail to aggregated sub-grouping, should reset DATE sort to AMOUNT."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_category = "Coffee Shops"
        state.sub_grouping_mode = None  # Currently in detail view
        state.sort_by = SortMode.DATE  # Sorted by date (valid for detail)

        # Cycle to aggregated sub-grouping
        result = state.cycle_sub_grouping()

        # Should switch to aggregated view and reset sort from DATE to AMOUNT
        assert state.sub_grouping_mode == ViewMode.MERCHANT
        assert state.sort_by == SortMode.AMOUNT
        assert result == "by Merchant"

    def test_cycle_sub_grouping_preserves_count_sort(self):
        """When cycling from detail to aggregated sub-grouping, COUNT sort should be preserved."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"
        state.sub_grouping_mode = None  # Currently in detail view
        state.sort_by = SortMode.COUNT  # Already valid for aggregated views

        # Cycle to aggregated sub-grouping
        result = state.cycle_sub_grouping()

        # Should preserve COUNT sort
        assert state.sub_grouping_mode == ViewMode.CATEGORY
        assert state.sort_by == SortMode.COUNT
        assert result == "by Category"

    def test_cycle_sub_grouping_preserves_amount_sort(self):
        """When cycling from detail to aggregated sub-grouping, AMOUNT sort should be preserved."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_group = "Food & Dining"
        state.sub_grouping_mode = None  # Currently in detail view
        state.sort_by = SortMode.AMOUNT

        # Cycle to aggregated sub-grouping
        result = state.cycle_sub_grouping()

        # Should preserve AMOUNT sort
        assert state.sub_grouping_mode == ViewMode.MERCHANT
        assert state.sort_by == SortMode.AMOUNT

    def test_go_back_clears_sub_grouping_first(self):
        """Escape should clear sub-grouping before going back."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"
        state.sub_grouping_mode = ViewMode.CATEGORY

        success, cursor, _ = state.go_back()

        # Should clear sub-grouping, stay drilled into Amazon
        assert success is True
        assert state.sub_grouping_mode is None
        assert state.selected_merchant == "Amazon"
        assert state.view_mode == ViewMode.DETAIL

    def test_go_back_then_clears_drill_down(self):
        """Second Escape should clear drill-down."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"
        state.sub_grouping_mode = ViewMode.CATEGORY
        # Navigation history uses NavigationState object
        state.navigation_history.append(
            NavigationState(
                view_mode=ViewMode.MERCHANT,
                cursor_position=5,
                scroll_y=125.0,
                sort_by=SortMode.AMOUNT,
                sort_direction=SortDirection.DESC,
            )
        )

        # First escape: clear sub-grouping
        success1, _, _ = state.go_back()
        assert success1 is True
        assert state.sub_grouping_mode is None
        assert state.selected_merchant == "Amazon"

        # Second escape: clear drill-down
        success2, cursor, scroll_y = state.go_back()
        assert success2 is True
        assert state.selected_merchant is None
        assert state.view_mode == ViewMode.MERCHANT
        assert cursor == 5
        assert scroll_y == 125.0

    def test_breadcrumb_shows_sub_grouping(self):
        """Breadcrumb should show sub-grouping mode."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"
        state.sub_grouping_mode = ViewMode.CATEGORY
        state.start_date = date(2025, 1, 1)
        state.end_date = date(2025, 12, 31)
        state.time_frame = TimeFrame.THIS_YEAR

        breadcrumb = state.get_breadcrumb()

        assert "Merchants" in breadcrumb
        assert "Amazon" in breadcrumb
        assert "(by Category)" in breadcrumb
        assert "Year 2025" in breadcrumb

    def test_breadcrumb_multi_level_drill_down(self):
        """Breadcrumb should show multiple drill-down levels."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"
        state.selected_category = "Groceries"
        state.start_date = date(2025, 10, 1)
        state.end_date = date(2025, 10, 31)
        state.time_frame = TimeFrame.THIS_MONTH

        breadcrumb = state.get_breadcrumb()

        assert "Merchants" in breadcrumb
        assert "Amazon" in breadcrumb
        assert "Groceries" in breadcrumb
        assert "October 2025" in breadcrumb

    def test_multi_level_go_back_clears_deepest_first(self):
        """Multi-level drill-down should clear deepest selection first."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"
        state.selected_category = "Groceries"

        # First go_back: clear category (deepest)
        success, _, _ = state.go_back()
        assert success is True
        assert state.selected_category is None
        assert state.selected_merchant == "Amazon"

        # Second go_back: clear merchant
        success, _, _ = state.go_back()
        assert success is True
        assert state.selected_merchant is None


class TestSmartSearchEscape:
    """Tests for smart search escape behavior."""

    def test_get_navigation_depth_top_level(self):
        """Top-level views should have depth 0."""
        state = AppState()
        state.view_mode = ViewMode.MERCHANT
        assert state.get_navigation_depth() == 0

    def test_get_navigation_depth_one_level(self):
        """Drilled once should have depth 1."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"
        assert state.get_navigation_depth() == 1

    def test_get_navigation_depth_two_levels(self):
        """Drilled twice should have depth 2."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"
        state.selected_category = "Groceries"
        assert state.get_navigation_depth() == 2

    def test_set_search_saves_navigation_state(self):
        """Setting search should save current navigation state."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"

        state.set_search("coffee")

        assert state.search_query == "coffee"
        assert state.search_navigation_state is not None
        assert state.search_navigation_state == (1, None)  # depth 1, no sub-grouping

    def test_set_search_with_sub_grouping(self):
        """Search with sub-grouping should save that state."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"
        state.sub_grouping_mode = ViewMode.CATEGORY

        state.set_search("grocery")

        assert state.search_navigation_state == (1, ViewMode.CATEGORY)

    def test_clear_search_clears_navigation_state(self):
        """Clearing search should clear navigation state."""
        state = AppState()
        state.set_search("coffee")

        state.set_search("")

        assert state.search_query == ""
        assert state.search_navigation_state is None

    def test_escape_clears_search_when_no_navigation(self):
        """Scenario 1: Search without further navigation, Escape clears search."""
        state = AppState()
        state.view_mode = ViewMode.MERCHANT
        state.set_search("coffee")

        # No navigation happened, just searched
        success, _, _ = state.go_back()

        assert success is True
        assert state.search_query == ""
        assert state.view_mode == ViewMode.MERCHANT  # Still in Merchants view

    def test_escape_navigates_after_drill_down_with_search(self):
        """Scenario 2: Search then drill down, Escape navigates (search persists)."""
        state = AppState()
        state.view_mode = ViewMode.MERCHANT
        state.set_search("coffee")

        # Drill down (navigation happened)
        state.drill_down("Starbucks", 5)

        # Now Escape should navigate back, not clear search
        success, cursor, _ = state.go_back()

        assert success is True
        assert state.search_query == "coffee"  # Search still active
        assert state.view_mode == ViewMode.MERCHANT
        assert cursor == 5

    def test_escape_twice_after_drill_clears_search(self):
        """After navigating back to search level, second Escape clears search."""
        state = AppState()
        state.view_mode = ViewMode.MERCHANT
        state.set_search("coffee")
        state.drill_down("Starbucks", 5)

        # First Escape: navigate back
        state.go_back()
        assert state.search_query == "coffee"  # Still active

        # Second Escape: clear search (back at original depth)
        success, _, _ = state.go_back()
        assert success is True
        assert state.search_query == ""

    def test_escape_with_search_and_sub_grouping(self):
        """Scenario 3: Search then sub-group, Escape clears sub-grouping first."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"
        state.set_search("grocery")

        # Sub-group (navigation happened - depth same but state changed)
        state.sub_grouping_mode = ViewMode.CATEGORY

        # Escape should clear sub-grouping (search still active, navigation happened)
        success, _, _ = state.go_back()

        assert success is True
        assert state.sub_grouping_mode is None
        assert state.search_query == "grocery"  # Search persists
        assert state.selected_merchant == "Amazon"  # Still drilled down

    def test_escape_after_clearing_sub_grouping_clears_search(self):
        """After clearing sub-grouping, if back at search level, Escape clears search."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"
        state.set_search("grocery")
        state.sub_grouping_mode = ViewMode.CATEGORY

        # First Escape: clear sub-grouping
        state.go_back()
        assert state.sub_grouping_mode is None
        assert state.search_query == "grocery"

        # Now we're at same state as when search was set
        # Second Escape: should clear search
        success, _, _ = state.go_back()
        assert success is True
        assert state.search_query == ""
        assert state.selected_merchant == "Amazon"  # Still drilled down

    def test_search_persists_across_navigation(self):
        """Search should stay active when navigating away and back."""
        state = AppState()
        state.view_mode = ViewMode.MERCHANT
        state.set_search("coffee")
        state.drill_down("Starbucks", 5)

        # Navigate back
        state.go_back()

        # Search should still be active
        assert state.search_query == "coffee"

    def test_get_navigation_state_comparison(self):
        """Navigation state should change when sub-grouping changes."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"

        state1 = state.get_navigation_state()
        assert state1 == (1, None)

        state.sub_grouping_mode = ViewMode.CATEGORY
        state2 = state.get_navigation_state()
        assert state2 == (1, ViewMode.CATEGORY)
        assert state1 != state2
