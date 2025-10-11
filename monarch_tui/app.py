"""
Main Monarch Money TUI Application.

A fast, keyboard-driven terminal interface for transaction management.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, DataTable, Static, LoadingIndicator
from textual.reactive import reactive

from .monarchmoney import MonarchMoney
from .data_manager import DataManager
from .state import AppState, ViewMode, SortMode
from .widgets.help_screen import HelpScreen


class MonarchTUI(App):
    """Monarch Money Power User TUI."""

    CSS_PATH = "styles/monarch.tcss"

    BINDINGS = [
        Binding("m", "view_merchants", "Merchants", show=True),
        Binding("c", "view_categories", "Categories", show=True),
        Binding("g", "view_groups", "Groups", show=True),
        Binding("question_mark", "help", "Help", show=True, key_display="?"),
        Binding("slash", "search", "Search", show=True, key_display="/"),
        Binding("h,left", "toggle_sort", "Sort", show=True),
        Binding("l,right", "toggle_sort", "Sort", show=True),
        Binding("escape", "go_back", "Back", show=False),
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("q", "quit_app", "Quit", show=True),
    ]

    # Reactive state
    status_message = reactive("Ready")
    pending_changes_count = reactive(0)

    def __init__(self):
        super().__init__()
        self.mm = MonarchMoney()
        self.data_manager: Optional[DataManager] = None
        self.state = AppState()
        self.loading = False

    def compose(self) -> ComposeResult:
        """Compose the main UI."""
        yield Header(show_clock=True)

        with Container(id="app-body"):
            # Top status bar
            with Horizontal(id="status-bar"):
                yield Static("", id="breadcrumb")
                yield Static("", id="stats")

            # Main content area
            with Vertical(id="content-area"):
                yield LoadingIndicator(id="loading")
                yield Static("", id="loading-status")
                yield DataTable(id="data-table", cursor_type="row")

            # Bottom action hints
            with Horizontal(id="action-bar"):
                yield Static("", id="action-hints")
                yield Static("", id="pending-changes")

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the app after mounting."""
        # Set up data table
        table = self.query_one("#data-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True

        # Hide loading initially
        self.query_one("#loading", LoadingIndicator).display = False
        self.query_one("#loading-status", Static).display = False

        # Attempt to use saved session or show login prompt
        # Must run in a worker to use push_screen with wait_for_dismiss
        self.run_worker(self.initialize_data(), exclusive=True)

    async def initialize_data(self) -> None:
        """Load data from Monarch API."""
        self.loading = True
        self.query_one("#loading", LoadingIndicator).display = True
        loading_status = self.query_one("#loading-status", Static)
        loading_status.display = True
        loading_status.update("🔄 Connecting to Monarch Money...")

        try:
            # Try to use encrypted credentials first
            from .credentials import CredentialManager
            from .monarchmoney import RequireMFAException, LoginFailedException
            from .screens.credential_screens import CredentialSetupScreen, CredentialUnlockScreen

            cred_manager = CredentialManager()
            creds = None

            if cred_manager.credentials_exist():
                # Show unlock screen
                result = await self.push_screen(CredentialUnlockScreen(), wait_for_dismiss=True)

                if result is None:
                    # User chose to reset - show setup screen
                    creds = await self.push_screen(CredentialSetupScreen(), wait_for_dismiss=True)
                    if not creds:
                        self.exit()
                        return
                else:
                    creds = result
            else:
                # No credentials - show setup screen
                creds = await self.push_screen(CredentialSetupScreen(), wait_for_dismiss=True)
                if not creds:
                    self.exit()
                    return

            # Login with credentials
            loading_status.update("🔐 Logging in to Monarch Money...")

            try:
                await self.mm.login(
                    email=creds['email'],
                    password=creds['password'],
                    use_saved_session=False,
                    save_session=True,
                    mfa_secret_key=creds['mfa_secret']
                )
                loading_status.update("✅ Logged in successfully!")
            except (RequireMFAException, LoginFailedException) as e:
                # Login failed - credentials may be invalid
                loading_status.update(f"❌ Login failed: {e}")
                self.notify(f"Login failed: {e}", severity="error", timeout=10)
                self.notify("Your credentials may be incorrect. Exiting...", timeout=10)
                self.exit()
                return

            # Initialize data manager
            self.data_manager = DataManager(self.mm)

            # Load last year of data
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')

            self.state.start_date = start_date
            self.state.end_date = end_date

            # Fetch data from API with progress updates
            loading_status.update("📊 Fetching transaction data from Monarch Money...")
            loading_status.update("⏳ This may take a minute for large accounts (10k+ transactions)...")

            def update_progress(msg: str) -> None:
                """Update the loading status display."""
                loading_status.update(f"📊 {msg}")

            df, categories, category_groups = await self.data_manager.fetch_all_data(
                start_date=start_date,
                end_date=end_date,
                progress_callback=update_progress
            )

            # Store in data manager
            self.data_manager.df = df
            self.data_manager.categories = categories
            self.data_manager.category_groups = category_groups
            self.state.transactions_df = df

            loading_status.update(f"✅ Loaded {len(df):,} transactions! Preparing view...")

            # Show initial view (merchants)
            self.refresh_view()

        except Exception as e:
            loading_status = self.query_one("#loading-status", Static)
            loading_status.update(f"❌ Error: {e}")
            self.notify(f"Failed to load data: {e}", severity="error", timeout=10)

        finally:
            self.loading = False
            self.query_one("#loading", LoadingIndicator).display = False
            self.query_one("#loading-status", Static).display = False

    def update_loading_progress(self, current: int, total: int, message: str) -> None:
        """Update loading progress message."""
        self.status_message = f"{message} ({current}/{total})"

    def refresh_view(self) -> None:
        """Refresh the current view based on state."""
        if self.data_manager is None:
            return

        table = self.query_one("#data-table", DataTable)
        table.clear(columns=True)

        # Determine what data to show
        if self.state.view_mode == ViewMode.MERCHANT:
            self.show_merchant_aggregation()
        elif self.state.view_mode == ViewMode.CATEGORY:
            self.show_category_aggregation()
        elif self.state.view_mode == ViewMode.GROUP:
            self.show_group_aggregation()
        elif self.state.view_mode == ViewMode.DETAIL:
            self.show_transactions()

        # Update UI elements
        self.update_breadcrumb()
        self.update_stats()
        self.update_action_hints()

    def show_merchant_aggregation(self) -> None:
        """Show merchant aggregation view."""
        table = self.query_one("#data-table", DataTable)

        # Add columns
        table.add_column("Merchant", key="merchant", width=40)
        table.add_column("Count", key="count", width=10)
        table.add_column("Total", key="total", width=15)

        # Get aggregated data
        agg = self.data_manager.aggregate_by_merchant(self.data_manager.df)
        # Sort based on mode
        if self.state.sort_mode != SortMode.COUNT_DESC:
            sort_col = "total" if "AMOUNT" in self.state.sort_mode.value else "count"
            agg = agg.sort(sort_col, descending=True)
        self.state.current_data = agg

        # Add rows
        for row in agg.iter_rows(named=True):
            merchant = row['merchant'] or 'Unknown'
            count = row['count']
            total = row['total']
            table.add_row(merchant, str(count), f"${total:,.2f}")

    def show_category_aggregation(self) -> None:
        """Show category aggregation view."""
        table = self.query_one("#data-table", DataTable)

        table.add_column("Category", key="category", width=40)
        table.add_column("Count", key="count", width=10)
        table.add_column("Total", key="total", width=15)

        agg = self.data_manager.aggregate_by_category(self.data_manager.df)
        # Sort based on mode
        if self.state.sort_mode != SortMode.COUNT_DESC:
            sort_col = "total" if "AMOUNT" in self.state.sort_mode.value else "count"
            agg = agg.sort(sort_col, descending=True)
        self.state.current_data = agg

        for row in agg.iter_rows(named=True):
            category = row['category'] or 'Uncategorized'
            count = row['count']
            total = row['total']
            table.add_row(category, str(count), f"${total:,.2f}")

    def show_group_aggregation(self) -> None:
        """Show group aggregation view."""
        table = self.query_one("#data-table", DataTable)

        table.add_column("Group", key="group", width=40)
        table.add_column("Count", key="count", width=10)
        table.add_column("Total", key="total", width=15)

        agg = self.data_manager.aggregate_by_group(self.data_manager.df)
        # Sort based on mode
        if self.state.sort_mode != SortMode.COUNT_DESC:
            sort_col = "total" if "AMOUNT" in self.state.sort_mode.value else "count"
            agg = agg.sort(sort_col, descending=True)
        self.state.current_data = agg

        for row in agg.iter_rows(named=True):
            group = row['group'] or 'Other'
            count = row['count']
            total = row['total']
            table.add_row(group, str(count), f"${total:,.2f}")

    def show_transactions(self) -> None:
        """Show individual transactions (drill-down view)."""
        table = self.query_one("#data-table", DataTable)

        table.add_column("Date", key="date", width=12)
        table.add_column("Merchant", key="merchant", width=30)
        table.add_column("Category", key="category", width=25)
        table.add_column("Amount", key="amount", width=12)
        table.add_column("", key="flags", width=3)

        # Filter transactions based on drill-down
        if self.state.selected_merchant:
            txns = self.data_manager.filter_by_merchant(self.data_manager.df, self.state.selected_merchant)
        elif self.state.selected_category:
            txns = self.data_manager.filter_by_category(self.data_manager.df, self.state.selected_category)
        elif self.state.selected_group:
            txns = self.data_manager.filter_by_group(self.data_manager.df, self.state.selected_group)
        else:
            txns = self.data_manager.df

        self.state.current_data = txns

        # Add rows
        for row in txns.iter_rows(named=True):
            date = str(row['date'])
            merchant = row['merchant'] or 'Unknown'
            category = row['category'] or 'Uncategorized'
            amount = row['amount']
            flags = "H" if row.get('hideFromReports', False) else ""

            table.add_row(date, merchant, category, f"${amount:,.2f}", flags)

    def update_breadcrumb(self) -> None:
        """Update breadcrumb navigation."""
        breadcrumb = self.query_one("#breadcrumb", Static)
        breadcrumb.update(self.state.get_breadcrumb())

    def update_stats(self) -> None:
        """Update statistics display."""
        if self.data_manager is None:
            return

        stats = self.data_manager.get_stats()
        stats_widget = self.query_one("#stats", Static)

        txn_count = stats['total_transactions']
        total_amount = stats['total_amount']

        stats_text = f"{txn_count:,} transactions | ${total_amount:,.2f} total"
        stats_widget.update(stats_text)

    def update_action_hints(self) -> None:
        """Update action hints based on current view."""
        hints_widget = self.query_one("#action-hints", Static)

        if self.state.view_mode in [ViewMode.MERCHANT, ViewMode.CATEGORY, ViewMode.GROUP]:
            hints = "[Enter] Drill down | [h/l] Toggle sort | [/] Search"
        else:  # DETAIL
            hints = "[e] Edit merchant | [r] Change category | [H] Hide | [Esc] Back"

        hints_widget.update(hints)

        # Update pending changes
        changes_widget = self.query_one("#pending-changes", Static)
        count = self.data_manager.get_stats()['pending_changes'] if self.data_manager else 0
        self.pending_changes_count = count
        if count > 0:
            changes_widget.update(f"⚠ {count} pending change(s)")
        else:
            changes_widget.update("")

    # Actions
    def action_view_merchants(self) -> None:
        """Switch to merchant view."""
        self.state.view_mode = ViewMode.MERCHANT
        self.state.selected_merchant = None
        self.state.selected_category = None
        self.state.selected_group = None
        self.refresh_view()

    def action_view_categories(self) -> None:
        """Switch to category view."""
        self.state.view_mode = ViewMode.CATEGORY
        self.state.selected_merchant = None
        self.state.selected_category = None
        self.state.selected_group = None
        self.refresh_view()

    def action_view_groups(self) -> None:
        """Switch to group view."""
        self.state.view_mode = ViewMode.GROUP
        self.state.selected_merchant = None
        self.state.selected_category = None
        self.state.selected_group = None
        self.refresh_view()

    def action_toggle_sort(self) -> None:
        """Toggle sort order."""
        self.state.toggle_sort()
        self.refresh_view()
        sort_name = "Count" if self.state.sort_mode == SortMode.COUNT else "Amount"
        self.notify(f"Sorted by {sort_name}", timeout=1)

    def action_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())

    def action_search(self) -> None:
        """Show search input."""
        # TODO: Implement search modal
        self.notify("Search not yet implemented", timeout=2)

    def action_go_back(self) -> None:
        """Go back to previous view."""
        if self.state.go_back():
            self.refresh_view()

    async def action_save(self) -> None:
        """Save pending changes."""
        if self.data_manager is None:
            return

        count = self.data_manager.get_stats()['pending_changes']
        if count == 0:
            self.notify("No pending changes to save", timeout=2)
            return

        self.notify(f"Saving {count} change(s)...", timeout=3)

        try:
            success_count, failure_count = await self.data_manager.commit_pending_edits(
                self.data_manager.pending_edits
            )
            if failure_count > 0:
                self.notify(f"Saved {success_count}, {failure_count} failed", severity="warning", timeout=5)
            else:
                self.notify(f"Saved {success_count} change(s)!", severity="information", timeout=3)

            # Clear pending edits on success
            self.data_manager.pending_edits.clear()
            self.update_action_hints()
        except Exception as e:
            self.notify(f"Error saving: {e}", severity="error", timeout=5)

    def action_quit_app(self) -> None:
        """Quit the application - show confirmation first."""
        # Show confirmation in a worker (required for push_screen with wait_for_dismiss)
        self.run_worker(self._confirm_and_quit(), exclusive=False)

    async def _confirm_and_quit(self) -> None:
        """Show quit confirmation dialog and exit if confirmed."""
        from .screens.credential_screens import QuitConfirmationScreen

        has_changes = (
            self.data_manager and
            self.data_manager.get_stats()['pending_changes'] > 0
        ) if self.data_manager else False

        should_quit = await self.push_screen(
            QuitConfirmationScreen(has_unsaved_changes=has_changes),
            wait_for_dismiss=True
        )

        if should_quit:
            self.exit()

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key)."""
        if self.state.view_mode in [ViewMode.MERCHANT, ViewMode.CATEGORY, ViewMode.GROUP]:
            # Drill down
            table = self.query_one("#data-table", DataTable)
            row_key = event.row_key
            row = table.get_row(row_key)

            # First column is the item name
            item_name = str(row[0])
            self.state.drill_down(item_name)
            self.refresh_view()


def main():
    """Entry point for the TUI."""
    app = MonarchTUI()
    app.run()


if __name__ == "__main__":
    main()
