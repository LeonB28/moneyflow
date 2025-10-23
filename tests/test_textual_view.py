"""
Tests for TextualViewPresenter.

This module tests the Textual-specific view implementation, ensuring proper
integration with Textual widgets.
"""

import pytest
from textual.app import App
from textual.widgets import DataTable, Static

from moneyflow.textual_view import TextualViewPresenter


class MockApp(App):
    """Mock Textual app for testing."""

    def compose(self):
        yield DataTable(id="data-table")
        yield Static(id="breadcrumb")
        yield Static(id="stats")
        yield Static(id="action-hints")
        yield Static(id="pending-changes")


@pytest.fixture
def mock_app():
    """Create a mock Textual app."""
    return MockApp()


@pytest.fixture
def view_presenter(mock_app):
    """Create a TextualViewPresenter with mock app."""
    return TextualViewPresenter(mock_app)


class TestUpdateTable:
    """Tests for update_table method."""

    async def test_update_table_with_force_rebuild(self, view_presenter, mock_app):
        """Test that force_rebuild clears columns and rebuilds."""
        # Mount the app
        async with mock_app.run_test():
            table = mock_app.query_one("#data-table", DataTable)

            # Add some initial columns
            table.add_column("Old1", key="old1")
            table.add_column("Old2", key="old2")
            assert len(table.columns) == 2

            # Update with force_rebuild
            columns = [
                {"label": "New1", "key": "new1", "width": 10},
                {"label": "New2", "key": "new2", "width": 15},
            ]
            rows = [("val1", "val2")]

            view_presenter.update_table(columns, rows, force_rebuild=True)

            # Should have new columns
            assert len(table.columns) == 2
            assert "new1" in table.columns
            assert "new2" in table.columns
            assert table.row_count == 1

    async def test_update_table_without_force_rebuild_existing_columns(
        self, view_presenter, mock_app
    ):
        """Test that smooth update keeps columns when they exist."""
        async with mock_app.run_test():
            table = mock_app.query_one("#data-table", DataTable)

            # Add initial columns and rows
            table.add_column("Col1", key="col1")
            table.add_column("Col2", key="col2")
            table.add_row("old1", "old2")
            assert len(table.columns) == 2
            assert table.row_count == 1

            # Update without force_rebuild
            columns = [
                {"label": "Col1", "key": "col1", "width": 10},
                {"label": "Col2", "key": "col2", "width": 15},
            ]
            rows = [("new1", "new2"), ("new3", "new4")]

            view_presenter.update_table(columns, rows, force_rebuild=False)

            # Should keep columns but update rows
            assert len(table.columns) == 2
            assert table.row_count == 2

    async def test_update_table_without_force_rebuild_no_columns(self, view_presenter, mock_app):
        """Test that smooth update adds columns if none exist (edge case)."""
        async with mock_app.run_test():
            table = mock_app.query_one("#data-table", DataTable)

            # Ensure no columns
            assert len(table.columns) == 0

            # Update without force_rebuild
            columns = [
                {"label": "Col1", "key": "col1", "width": 10},
                {"label": "Col2", "key": "col2", "width": 15},
            ]
            rows = [("val1", "val2")]

            view_presenter.update_table(columns, rows, force_rebuild=False)

            # Should add columns and rows
            assert len(table.columns) == 2
            assert table.row_count == 1

    async def test_update_table_empty_rows(self, view_presenter, mock_app):
        """Test updating table with no rows."""
        async with mock_app.run_test():
            table = mock_app.query_one("#data-table", DataTable)

            columns = [
                {"label": "Col1", "key": "col1", "width": 10},
            ]
            rows = []

            view_presenter.update_table(columns, rows, force_rebuild=True)

            assert len(table.columns) == 1
            assert table.row_count == 0

    async def test_update_table_handles_column_mismatch(self, view_presenter, mock_app):
        """Test that column mismatch triggers rebuild even with force_rebuild=False."""
        async with mock_app.run_test():
            table = mock_app.query_one("#data-table", DataTable)

            # Initial setup with 2 columns
            columns1 = [
                {"label": "Col1", "key": "col1", "width": 10},
                {"label": "Col2", "key": "col2", "width": 15},
            ]
            rows1 = [("a", "b")]
            view_presenter.update_table(columns1, rows1, force_rebuild=True)

            assert len(table.columns) == 2
            assert table.row_count == 1

            # Update with different columns (3 instead of 2), force_rebuild=False
            columns2 = [
                {"label": "ColA", "key": "colA", "width": 10},
                {"label": "ColB", "key": "colB", "width": 15},
                {"label": "ColC", "key": "colC", "width": 20},
            ]
            rows2 = [("x", "y", "z")]
            view_presenter.update_table(columns2, rows2, force_rebuild=False)

            # Should rebuild columns automatically
            assert len(table.columns) == 3
            assert table.row_count == 1
            assert "colA" in table.columns
            assert "colB" in table.columns
            assert "colC" in table.columns


class TestNotifications:
    """Tests for notification methods."""

    def test_show_notification(self, view_presenter, mock_app):
        """Test that notifications are displayed."""
        # Notifications are shown via app.notify, which we can't easily test
        # without a full integration test. Just verify method doesn't crash.
        view_presenter.show_notification("Test message", "information", 3)


class TestWidgetUpdates:
    """Tests for widget update methods."""

    async def test_update_breadcrumb(self, view_presenter, mock_app):
        """Test breadcrumb update."""
        async with mock_app.run_test():
            # Just verify the method doesn't crash
            view_presenter.update_breadcrumb("Test > Path")

    async def test_update_stats(self, view_presenter, mock_app):
        """Test stats update."""
        async with mock_app.run_test():
            # Just verify the method doesn't crash
            view_presenter.update_stats("Total: $100")

    async def test_update_hints(self, view_presenter, mock_app):
        """Test action hints update."""
        async with mock_app.run_test():
            # Just verify the method doesn't crash
            view_presenter.update_hints("Press q to quit")

    async def test_update_pending_changes_with_count(self, view_presenter, mock_app):
        """Test pending changes display with count."""
        async with mock_app.run_test():
            # Just verify the method doesn't crash
            view_presenter.update_pending_changes(5)

    async def test_update_pending_changes_zero(self, view_presenter, mock_app):
        """Test pending changes cleared when zero."""
        async with mock_app.run_test():
            # Just verify the method doesn't crash
            view_presenter.update_pending_changes(3)
            view_presenter.update_pending_changes(0)
