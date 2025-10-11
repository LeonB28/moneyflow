"""
Tests for state management, undo/redo, and change tracking.
"""
import pytest
from datetime import date, datetime
from state import AppState, ViewMode, SortMode, TimeFrame, TransactionEdit


class TestAppState:
    """Test AppState initialization and basic operations."""

    def test_initial_state(self, app_state):
        """Test that AppState initializes with correct defaults."""
        assert app_state.view_mode == ViewMode.MERCHANT
        assert app_state.sort_mode == SortMode.COUNT_DESC
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
        """Test sort mode toggling."""
        # Start with COUNT_DESC
        assert app_state.sort_mode == SortMode.COUNT_DESC

        # Toggle to DATE_DESC
        app_state.toggle_sort()
        assert app_state.sort_mode == SortMode.DATE_DESC

        # Toggle back to AMOUNT_DESC (not COUNT)
        app_state.toggle_sort()
        assert app_state.sort_mode == SortMode.AMOUNT_DESC


class TestChangeTracking:
    """Test edit tracking, undo, and redo functionality."""

    def test_add_edit(self, app_state):
        """Test adding a pending edit."""
        app_state.add_edit(
            transaction_id="txn_1",
            field="merchant",
            old_value="Old Merchant",
            new_value="New Merchant"
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
