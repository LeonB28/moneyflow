"""
Main Monarch Money TUI Application.

A fast, keyboard-driven terminal interface for transaction management.
"""

import argparse
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
        Binding("y", "this_year", "This Year", show=True),
        Binding("a", "all_time", "All Time", show=True),
        Binding("t", "this_month", "This Month", show=True),
        Binding("1", "select_month_1", "Jan", show=False),
        Binding("2", "select_month_2", "Feb", show=False),
        Binding("3", "select_month_3", "Mar", show=False),
        Binding("4", "select_month_4", "Apr", show=False),
        Binding("5", "select_month_5", "May", show=False),
        Binding("6", "select_month_6", "Jun", show=False),
        Binding("7", "select_month_7", "Jul", show=False),
        Binding("8", "select_month_8", "Aug", show=False),
        Binding("9", "select_month_9", "Sep", show=False),
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

    def __init__(self, start_year: Optional[int] = None, custom_start_date: Optional[str] = None):
        super().__init__()
        self.mm = MonarchMoney()
        self.data_manager: Optional[DataManager] = None
        self.state = AppState()
        self.loading = False
        self.start_year = start_year  # Optional year cutoff for data loading
        self.custom_start_date = custom_start_date  # Optional custom start date

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

            # Determine date range based on CLI arguments
            if self.custom_start_date:
                start_date = self.custom_start_date
                end_date = datetime.now().strftime('%Y-%m-%d')
                loading_status.update(f"📊 Fetching transactions from {self.custom_start_date} onwards...")
            elif self.start_year:
                start_date = f"{self.start_year}-01-01"
                end_date = datetime.now().strftime('%Y-%m-%d')
                loading_status.update(f"📊 Fetching transactions from {self.start_year} onwards...")
            else:
                # Fetch ALL transactions (no date filter for offline-first approach)
                start_date = None
                end_date = None
                loading_status.update("📊 Fetching ALL transaction data from Monarch Money...")

            loading_status.update("⏳ This may take a minute for large accounts (10k+ transactions)...")
            loading_status.update("💡 TIP: This is a one-time download. Future operations will be instant!")

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

            # Initialize time frame to THIS_YEAR (default view filter)
            # This filters the display to current year even though we loaded all data
            from datetime import date as date_type
            today = date_type.today()
            self.state.start_date = date_type(today.year, 1, 1)
            self.state.end_date = date_type(today.year, 12, 31)

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

        # Get filtered data based on time_frame
        filtered_df = self.state.get_filtered_df()
        if filtered_df is None:
            return

        # Get aggregated data
        agg = self.data_manager.aggregate_by_merchant(filtered_df)
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

        # Get filtered data based on time_frame
        filtered_df = self.state.get_filtered_df()
        if filtered_df is None:
            return

        agg = self.data_manager.aggregate_by_category(filtered_df)
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

        # Get filtered data based on time_frame
        filtered_df = self.state.get_filtered_df()
        if filtered_df is None:
            return

        agg = self.data_manager.aggregate_by_group(filtered_df)
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

        # Start with filtered data based on time_frame
        filtered_df = self.state.get_filtered_df()
        if filtered_df is None:
            return

        # Apply drill-down filters if any
        if self.state.selected_merchant:
            txns = self.data_manager.filter_by_merchant(filtered_df, self.state.selected_merchant)
        elif self.state.selected_category:
            txns = self.data_manager.filter_by_category(filtered_df, self.state.selected_category)
        elif self.state.selected_group:
            txns = self.data_manager.filter_by_group(filtered_df, self.state.selected_group)
        else:
            txns = filtered_df

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

    # Time navigation actions
    def action_this_year(self) -> None:
        """Switch to current year view."""
        self.state.set_timeframe(TimeFrame.THIS_YEAR)
        self.refresh_view()
        self.notify("Viewing: This Year", timeout=1)

    def action_all_time(self) -> None:
        """Switch to all time view."""
        self.state.set_timeframe(TimeFrame.ALL_TIME)
        self.refresh_view()
        self.notify("Viewing: All Time", timeout=1)

    def action_this_month(self) -> None:
        """Switch to current month view."""
        self.state.set_timeframe(TimeFrame.THIS_MONTH)
        self.refresh_view()
        self.notify("Viewing: This Month", timeout=1)

    def action_select_month_1(self) -> None:
        """View January of current year."""
        self._select_month(1, "January")

    def action_select_month_2(self) -> None:
        """View February of current year."""
        self._select_month(2, "February")

    def action_select_month_3(self) -> None:
        """View March of current year."""
        self._select_month(3, "March")

    def action_select_month_4(self) -> None:
        """View April of current year."""
        self._select_month(4, "April")

    def action_select_month_5(self) -> None:
        """View May of current year."""
        self._select_month(5, "May")

    def action_select_month_6(self) -> None:
        """View June of current year."""
        self._select_month(6, "June")

    def action_select_month_7(self) -> None:
        """View July of current year."""
        self._select_month(7, "July")

    def action_select_month_8(self) -> None:
        """View August of current year."""
        self._select_month(8, "August")

    def action_select_month_9(self) -> None:
        """View September of current year."""
        self._select_month(9, "September")

    def _select_month(self, month: int, month_name: str) -> None:
        """Helper to select a specific month of the current year."""
        from datetime import date as date_type
        import calendar

        today = date_type.today()
        year = today.year
        first_day = date_type(year, month, 1)
        last_day_num = calendar.monthrange(year, month)[1]
        last_day = date_type(year, month, last_day_num)

        self.state.set_timeframe(TimeFrame.CUSTOM, start_date=first_day, end_date=last_day)
        self.refresh_view()
        self.notify(f"Viewing: {month_name} {year}", timeout=1)

    def action_toggle_sort(self) -> None:
        """Toggle sort order."""
        self.state.toggle_sort()
        self.refresh_view()
        sort_name = "Count" if self.state.sort_mode == SortMode.COUNT_DESC else "Amount"
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
    parser = argparse.ArgumentParser(
        description="Monarch Money Terminal UI - Fast transaction management"
    )
    parser.add_argument(
        "--year",
        type=int,
        metavar="YYYY",
        help="Only load transactions from this year onwards (e.g., --year 2025 loads from 2025-01-01 to now). Default: load all transactions."
    )
    parser.add_argument(
        "--since",
        type=str,
        metavar="YYYY-MM-DD",
        help="Only load transactions from this date onwards (e.g., --since 2024-06-01). Overrides --year if both provided."
    )

    args = parser.parse_args()

    # Determine start year
    start_year = None
    custom_start_date = None

    if args.since:
        custom_start_date = args.since
    elif args.year:
        start_year = args.year

    app = MonarchTUI(start_year=start_year, custom_start_date=custom_start_date)
    app.run()


if __name__ == "__main__":
    main()
