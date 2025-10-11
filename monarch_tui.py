#!/usr/bin/env python3
"""
Monarch Money Terminal UI - Power user interface for transaction management
"""
import asyncio
import os
from datetime import date
from typing import Optional, List

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    DataTable, Header, Footer, Static, Input, Button, Label, Select
)
from textual.reactive import reactive

from monarch_tui import MonarchMoney
from monarch_tui.data_manager import DataManager
from monarch_tui.state import AppState, ViewMode, SortMode, TimeFrame


class LoginScreen(Screen):
    """Initial login screen shown on first run."""

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="login-dialog"):
            yield Label("Monarch Money Login", id="login-title")
            yield Label("Email:")
            yield Input(placeholder="your@email.com", id="email-input")
            yield Label("Password:")
            yield Input(password=True, placeholder="password", id="password-input")
            yield Button("Login", variant="primary", id="login-button")
            yield Label("", id="login-error")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login-button":
            await self.do_login()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        await self.do_login()

    async def do_login(self) -> None:
        email_input = self.query_one("#email-input", Input)
        password_input = self.query_one("#password-input", Input)
        error_label = self.query_one("#login-error", Label)

        email = email_input.value.strip()
        password = password_input.value

        if not email or not password:
            error_label.update("Please enter both email and password")
            return

        error_label.update("Logging in...")
        try:
            # Get the app instance and login
            app = self.app
            await app.mm.login(email, password, save_session=True)
            error_label.update("Login successful! Loading data...")

            # Load data and switch to main screen
            await app.load_initial_data()
            self.app.pop_screen()

        except Exception as e:
            error_label.update(f"Login failed: {str(e)}")


class MerchantEditDialog(ModalScreen):
    """Dialog for editing merchant name."""

    def __init__(self, transaction_id: str, current_merchant: str):
        super().__init__()
        self.transaction_id = transaction_id
        self.current_merchant = current_merchant

    def compose(self) -> ComposeResult:
        with Container(id="edit-dialog"):
            yield Label("Edit Merchant Name", id="dialog-title")
            yield Label(f"Current: {self.current_merchant}")
            yield Input(
                value=self.current_merchant,
                placeholder="Merchant name",
                id="merchant-input"
            )
            with Horizontal(id="dialog-buttons"):
                yield Button("Save", variant="primary", id="save-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-button":
            merchant_input = self.query_one("#merchant-input", Input)
            new_merchant = merchant_input.value.strip()
            if new_merchant and new_merchant != self.current_merchant:
                self.dismiss(new_merchant)
            else:
                self.dismiss(None)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        new_merchant = event.value.strip()
        if new_merchant and new_merchant != self.current_merchant:
            self.dismiss(new_merchant)
        else:
            self.dismiss(None)


class CategoryEditDialog(ModalScreen):
    """Dialog for editing transaction category."""

    def __init__(
        self,
        transaction_id: str,
        current_category: str,
        categories: dict
    ):
        super().__init__()
        self.transaction_id = transaction_id
        self.current_category = current_category
        self.categories = categories

    def compose(self) -> ComposeResult:
        # Create options list from categories
        options = [(cat_data['name'], cat_id)
                   for cat_id, cat_data in self.categories.items()]
        options.sort(key=lambda x: x[0])

        with Container(id="edit-dialog"):
            yield Label("Edit Category", id="dialog-title")
            yield Label(f"Current: {self.current_category}")
            yield Select(
                options=options,
                prompt="Select category",
                id="category-select"
            )
            with Horizontal(id="dialog-buttons"):
                yield Button("Save", variant="primary", id="save-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-button":
            category_select = self.query_one("#category-select", Select)
            if category_select.value != Select.BLANK:
                self.dismiss(category_select.value)
            else:
                self.dismiss(None)
        else:
            self.dismiss(None)


class BulkEditDialog(ModalScreen):
    """Dialog for bulk editing selected transactions."""

    def __init__(self, selected_count: int, categories: dict):
        super().__init__()
        self.selected_count = selected_count
        self.categories = categories

    def compose(self) -> ComposeResult:
        options = [(cat_data['name'], cat_id)
                   for cat_id, cat_data in self.categories.items()]
        options.sort(key=lambda x: x[0])

        with Container(id="edit-dialog"):
            yield Label(
                f"Bulk Edit ({self.selected_count} transactions)",
                id="dialog-title"
            )
            yield Label("Select action:")
            with Horizontal(id="bulk-actions"):
                yield Button("Change Category", id="bulk-category-button")
                yield Button("Toggle Hide", id="bulk-hide-button")
                yield Button("Cancel", id="cancel-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "bulk-category-button":
            self.dismiss(("category", None))
        elif event.button.id == "bulk-hide-button":
            self.dismiss(("hide", None))
        else:
            self.dismiss(None)


class SearchBar(Static):
    """Search/filter bar at the top of the screen."""

    search_query = reactive("")

    def compose(self) -> ComposeResult:
        with Horizontal(id="search-container"):
            yield Label("Search: ", id="search-label")
            yield Input(placeholder="Filter by merchant, category...", id="search-input")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.search_query = event.value
            # Notify parent to update filter
            self.post_message(self.SearchChanged(event.value))

    class SearchChanged(Static.MessageSent):
        def __init__(self, query: str):
            super().__init__()
            self.query = query


class StatusBar(Static):
    """Status bar showing current state and pending changes."""

    status = reactive("")

    def compose(self) -> ComposeResult:
        yield Label(self.status, id="status-text")

    def watch_status(self, status: str) -> None:
        self.query_one("#status-text", Label).update(status)


class MonarchTUI(App):
    """Main TUI application."""

    CSS = """
    #login-dialog {
        width: 60;
        height: auto;
        border: solid $accent;
        background: $surface;
        margin: 1 2;
        padding: 1 2;
    }

    #login-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #login-error {
        color: $error;
        margin-top: 1;
    }

    #edit-dialog {
        width: 70;
        height: auto;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }

    #dialog-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #dialog-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    #dialog-buttons Button {
        margin: 0 1;
    }

    #search-container {
        dock: top;
        height: 3;
        background: $panel;
        padding: 0 1;
    }

    #search-label {
        width: auto;
        margin-right: 1;
        content-align: left middle;
    }

    #search-input {
        width: 1fr;
    }

    #status-text {
        dock: bottom;
        height: 1;
        background: $panel;
        padding: 0 1;
    }

    DataTable {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("m", "view_merchants", "Merchants"),
        Binding("c", "view_categories", "Categories"),
        Binding("g", "view_groups", "Groups"),
        Binding("slash", "search", "Search", key_display="/"),
        Binding("e", "edit_merchant", "Edit Merchant"),
        Binding("r", "edit_category", "Change Category"),
        Binding("h", "toggle_hide", "Toggle Hide"),
        Binding("space", "toggle_select", "Select"),
        Binding("b", "bulk_edit", "Bulk Edit"),
        Binding("u", "undo", "Undo"),
        Binding("ctrl+r", "redo", "Redo"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+l", "refresh", "Refresh"),
        Binding("q", "quit_app", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.mm = MonarchMoney()
        self.data_manager: Optional[DataManager] = None
        self.state = AppState()

    def compose(self) -> ComposeResult:
        yield Header()
        yield SearchBar()
        yield DataTable(zebra_stripes=True)
        yield StatusBar()
        yield Footer()

    async def on_mount(self) -> None:
        """Check if logged in, show login screen if needed."""
        session_file = ".mm/mm_session.pickle"

        if os.path.exists(session_file):
            try:
                self.mm.load_session(session_file)
                await self.load_initial_data()
            except Exception as e:
                self.push_screen(LoginScreen())
        else:
            self.push_screen(LoginScreen())

    async def load_initial_data(self) -> None:
        """Load all transactions and metadata from API."""
        self.state.loading = True
        self.update_status("Loading transactions...")

        self.data_manager = DataManager(self.mm)

        # Set default timeframe to this year
        self.state.set_timeframe(TimeFrame.THIS_YEAR)

        # Fetch data
        df, categories, category_groups = await self.data_manager.fetch_all_data(
            start_date=self.state.start_date.isoformat() if self.state.start_date else None,
            end_date=self.state.end_date.isoformat() if self.state.end_date else None,
            progress_callback=self.update_status
        )

        self.state.transactions_df = df
        self.state.categories = categories
        self.state.category_groups = category_groups

        self.state.loading = False
        self.update_status(f"Loaded {len(df)} transactions")

        # Show merchant view by default
        self.action_view_merchants()

    def update_status(self, message: str) -> None:
        """Update status bar."""
        status_bar = self.query_one(StatusBar)
        pending = len(self.state.pending_edits)
        if pending > 0:
            status_bar.status = f"{message} | {pending} pending edit(s)"
        else:
            status_bar.status = message

    def action_view_merchants(self) -> None:
        """Switch to merchant aggregation view."""
        self.state.view_mode = ViewMode.MERCHANT
        self.state.selected_row = 0
        self.refresh_table()
        self.update_status("Viewing by merchant")

    def action_view_categories(self) -> None:
        """Switch to category aggregation view."""
        self.state.view_mode = ViewMode.CATEGORY
        self.state.selected_row = 0
        self.refresh_table()
        self.update_status("Viewing by category")

    def action_view_groups(self) -> None:
        """Switch to group aggregation view."""
        self.state.view_mode = ViewMode.GROUP
        self.state.selected_row = 0
        self.refresh_table()
        self.update_status("Viewing by group")

    def refresh_table(self) -> None:
        """Refresh the data table based on current view mode."""
        table = self.query_one(DataTable)
        table.clear(columns=True)

        filtered_df = self.state.get_filtered_df()
        if filtered_df is None or filtered_df.is_empty():
            return

        if self.state.view_mode == ViewMode.MERCHANT:
            agg_df = self.data_manager.aggregate_by_merchant(filtered_df)
            table.add_columns("Merchant", "Count", "Total")
            for row in agg_df.iter_rows():
                merchant, count, total, _ = row
                table.add_row(merchant, str(count), f"${total:,.2f}")

        elif self.state.view_mode == ViewMode.CATEGORY:
            agg_df = self.data_manager.aggregate_by_category(filtered_df)
            table.add_columns("Category", "Group", "Count", "Total")
            for row in agg_df.iter_rows():
                category, count, total, _, group = row
                table.add_row(category, group, str(count), f"${total:,.2f}")

        elif self.state.view_mode == ViewMode.GROUP:
            agg_df = self.data_manager.aggregate_by_group(filtered_df)
            table.add_columns("Group", "Count", "Total")
            for row in agg_df.iter_rows():
                group, count, total = row
                table.add_row(group, str(count), f"${total:,.2f}")

        elif self.state.view_mode == ViewMode.DETAIL:
            # Show individual transactions
            table.add_columns("Date", "Merchant", "Amount", "Category", "Hidden")
            for row in filtered_df.iter_rows():
                txn_id, txn_date, amount, merchant, _, category, *rest = row
                hidden = rest[5] if len(rest) > 5 else False
                table.add_row(
                    str(txn_date),
                    merchant,
                    f"${amount:,.2f}",
                    category,
                    "Yes" if hidden else ""
                )

    def action_search(self) -> None:
        """Focus on search bar."""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

    async def on_search_bar_search_changed(self, event: SearchBar.SearchChanged) -> None:
        """Handle search query change."""
        self.state.search_query = event.query
        self.refresh_table()

    async def action_edit_merchant(self) -> None:
        """Edit merchant name for selected transaction."""
        table = self.query_one(DataTable)
        if table.cursor_row is None or table.cursor_row < 0:
            return

        # Get selected row data
        row_data = list(table.get_row_at(table.cursor_row))

        if self.state.view_mode != ViewMode.DETAIL:
            # Switch to detail view for the selected merchant/category/group
            merchant_name = row_data[0]
            self.state.selected_merchant = merchant_name
            self.state.view_mode = ViewMode.DETAIL
            self.refresh_table()
            return

        # In detail view, edit the merchant
        merchant_name = row_data[1]  # Merchant column in detail view

        # Find the transaction
        filtered_df = self.state.get_filtered_df()
        txn_row = filtered_df.row(table.cursor_row, named=True)
        txn_id = txn_row['id']

        # Show edit dialog
        result = await self.push_screen_wait(
            MerchantEditDialog(txn_id, merchant_name)
        )

        if result:
            # Add to pending edits
            self.state.add_edit(txn_id, 'merchant', merchant_name, result)
            self.update_status(f"Changed merchant to: {result}")

    async def action_edit_category(self) -> None:
        """Change category for selected transaction."""
        table = self.query_one(DataTable)
        if table.cursor_row is None or table.cursor_row < 0:
            return

        if self.state.view_mode != ViewMode.DETAIL:
            self.update_status("Switch to detail view first (press Enter)")
            return

        # Get transaction data
        filtered_df = self.state.get_filtered_df()
        txn_row = filtered_df.row(table.cursor_row, named=True)
        txn_id = txn_row['id']
        current_category = txn_row['category']

        # Show category edit dialog
        result = await self.push_screen_wait(
            CategoryEditDialog(txn_id, current_category, self.state.categories)
        )

        if result:
            # Get category name from ID
            new_category_name = self.state.categories[result]['name']
            self.state.add_edit(txn_id, 'category', txn_row['category_id'], result)
            self.update_status(f"Changed category to: {new_category_name}")

    def action_toggle_hide(self) -> None:
        """Toggle hide from reports for selected transaction."""
        table = self.query_one(DataTable)
        if table.cursor_row is None or table.cursor_row < 0:
            return

        if self.state.view_mode != ViewMode.DETAIL:
            self.update_status("Switch to detail view first (press Enter)")
            return

        # Get transaction data
        filtered_df = self.state.get_filtered_df()
        txn_row = filtered_df.row(table.cursor_row, named=True)
        txn_id = txn_row['id']
        current_hide = txn_row['hide_from_reports']

        # Toggle value
        new_hide = not current_hide
        self.state.add_edit(txn_id, 'hide_from_reports', current_hide, new_hide)
        self.update_status(f"{'Hidden' if new_hide else 'Unhidden'} from reports")
        self.refresh_table()

    def action_toggle_select(self) -> None:
        """Toggle selection for bulk operations."""
        table = self.query_one(DataTable)
        if table.cursor_row is None or table.cursor_row < 0:
            return

        if self.state.view_mode != ViewMode.DETAIL:
            self.update_status("Switch to detail view first (press Enter)")
            return

        filtered_df = self.state.get_filtered_df()
        txn_row = filtered_df.row(table.cursor_row, named=True)
        txn_id = txn_row['id']

        self.state.toggle_selection(txn_id)
        self.update_status(f"{len(self.state.selected_ids)} transaction(s) selected")

    async def action_bulk_edit(self) -> None:
        """Bulk edit selected transactions."""
        if not self.state.selected_ids:
            self.update_status("No transactions selected")
            return

        result = await self.push_screen_wait(
            BulkEditDialog(len(self.state.selected_ids), self.state.categories)
        )

        if not result:
            return

        action, value = result

        if action == "category":
            # Show category selector
            # TODO: Implement category selection for bulk edit
            self.update_status("Bulk category edit not yet implemented")

        elif action == "hide":
            # Toggle hide for all selected
            filtered_df = self.state.get_filtered_df()
            for txn_id in self.state.selected_ids:
                txn_rows = filtered_df.filter(pl.col('id') == txn_id)
                if len(txn_rows) > 0:
                    txn_row = txn_rows.row(0, named=True)
                    current_hide = txn_row['hide_from_reports']
                    self.state.add_edit(txn_id, 'hide_from_reports', current_hide, not current_hide)

            self.update_status(f"Toggled hide for {len(self.state.selected_ids)} transactions")
            self.state.clear_selection()
            self.refresh_table()

    def action_undo(self) -> None:
        """Undo last edit."""
        edit = self.state.undo_last_edit()
        if edit:
            self.update_status(f"Undone: {edit.field} change")
            self.refresh_table()
        else:
            self.update_status("Nothing to undo")

    def action_redo(self) -> None:
        """Redo last undone edit."""
        edit = self.state.redo_last_edit()
        if edit:
            self.update_status(f"Redone: {edit.field} change")
            self.refresh_table()
        else:
            self.update_status("Nothing to redo")

    async def action_save(self) -> None:
        """Commit pending changes to Monarch Money API."""
        if not self.state.pending_edits:
            self.update_status("No pending changes to save")
            return

        edit_count = len(self.state.pending_edits)
        self.update_status(f"Saving {edit_count} change(s)...")

        success, failure = await self.data_manager.commit_pending_edits(
            self.state.pending_edits
        )

        if failure == 0:
            self.state.clear_pending_edits()
            self.update_status(f"Successfully saved {success} change(s)")
        else:
            self.update_status(f"Saved {success}, failed {failure}")

    async def action_refresh(self) -> None:
        """Re-fetch data from API."""
        await self.load_initial_data()

    def action_quit_app(self) -> None:
        """Quit the application."""
        if self.state.has_unsaved_changes():
            # TODO: Show confirmation dialog
            self.update_status("Warning: You have unsaved changes! Press Ctrl+S to save, then q to quit.")
        else:
            self.exit()


if __name__ == "__main__":
    app = MonarchTUI()
    app.run()
