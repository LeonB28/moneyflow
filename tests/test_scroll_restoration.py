"""
Tests for scroll position restoration.

These tests verify that scroll position is correctly saved and restored
during navigation operations (drill-down, go-back, sub-grouping, etc.).

These are regression tests for bugs where Textual's move_cursor() auto-scroll
would override our scroll_y restoration.
"""

from moneyflow.state import AppState, ViewMode


class TestScrollPositionSaving:
    """Test that scroll position is saved correctly in navigation history."""

    def test_drill_down_saves_scroll_position(self):
        """Drill down should save scroll position to navigation history."""
        state = AppState()
        state.view_mode = ViewMode.MERCHANT

        # Drill down with specific scroll position
        state.drill_down("Amazon", cursor_position=39, scroll_y=7.0)

        # Should have saved to navigation history
        assert len(state.navigation_history) == 1
        nav = state.navigation_history[0]
        assert nav.cursor_position == 39
        assert nav.scroll_y == 7.0
        assert nav.view_mode == ViewMode.MERCHANT

    def test_drill_down_saves_large_scroll_position(self):
        """Drill down should save large scroll positions correctly."""
        state = AppState()
        state.view_mode = ViewMode.CATEGORY

        # Simulate scrolling far down
        state.drill_down("Groceries", cursor_position=50, scroll_y=120.5)

        nav = state.navigation_history[0]
        assert nav.scroll_y == 120.5
        assert nav.cursor_position == 50


class TestScrollPositionRestoration:
    """Test that scroll position is restored correctly on go_back."""

    def test_go_back_returns_saved_scroll_position(self):
        """go_back should return the scroll position that was saved."""
        state = AppState()
        state.view_mode = ViewMode.MERCHANT

        # Drill down with scroll position
        state.drill_down("Starbucks", cursor_position=39, scroll_y=7.0)

        # Go back should return the saved values
        success, cursor, scroll_y = state.go_back()

        assert success is True
        assert cursor == 39
        assert scroll_y == 7.0

    def test_go_back_preserves_scroll_through_multiple_operations(self):
        """Scroll position should survive multiple drill-down and go-back cycles."""
        state = AppState()
        state.view_mode = ViewMode.MERCHANT

        # First drill-down
        state.drill_down("Amazon", cursor_position=25, scroll_y=5.0)

        # Go back
        success1, cursor1, scroll1 = state.go_back()
        assert cursor1 == 25
        assert scroll1 == 5.0

        # Second drill-down (different position)
        state.drill_down("Whole Foods", cursor_position=50, scroll_y=12.0)

        # Go back again
        success2, cursor2, scroll2 = state.go_back()
        assert cursor2 == 50
        assert scroll2 == 12.0

    def test_sub_grouping_preserves_drill_down_scroll_position(self):
        """When entering sub-grouping, original drill-down scroll should be preserved."""
        state = AppState()
        state.view_mode = ViewMode.MERCHANT

        # Drill down with scroll position
        state.drill_down("Amazon", cursor_position=39, scroll_y=7.0)

        # Enter sub-grouping (saves detail view state)
        state.cycle_sub_grouping()

        # Clear sub-grouping (should restore to detail view)
        state.go_back()

        # Original drill-down scroll position should still be in history
        assert len(state.navigation_history) == 1
        nav = state.navigation_history[0]
        assert nav.scroll_y == 7.0
        assert nav.cursor_position == 39

        # Final go-back should return original scroll position
        success, cursor, scroll_y = state.go_back()
        assert cursor == 39
        assert scroll_y == 7.0


class TestEdgeCases:
    """Test edge cases for scroll restoration."""

    def test_go_back_with_zero_scroll_position(self):
        """Should handle scroll_y=0 (top of list)."""
        state = AppState()
        state.view_mode = ViewMode.CATEGORY

        state.drill_down("Shopping", cursor_position=0, scroll_y=0.0)

        success, cursor, scroll_y = state.go_back()
        assert cursor == 0
        assert scroll_y == 0.0

    def test_go_back_without_navigation_history_returns_zero(self):
        """When no history exists, should return default scroll position."""
        state = AppState()
        state.view_mode = ViewMode.DETAIL
        state.selected_merchant = "Amazon"

        # Go back without drill-down history
        success, cursor, scroll_y = state.go_back()

        assert success is True
        assert cursor == 0
        assert scroll_y == 0.0
