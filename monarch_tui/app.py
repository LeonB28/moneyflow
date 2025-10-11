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
from .state import AppState, ViewMode, SortMode, SortDirection, TimeFrame, TransactionEdit
from .widgets.help_screen import HelpScreen


class MonarchTUI(App):
    """Monarch Money Power User TUI."""

    CSS_PATH = "styles/monarch.tcss"

    BINDINGS = [
        # View mode
        Binding("m", "view_merchants", "Merchants", show=True),
        Binding("c", "view_categories", "Categories", show=True),
        Binding("g", "view_groups", "Groups", show=True),
        Binding("D", "find_duplicates", "Duplicates", show=True, key_display="D"),
        # Time navigation
        Binding("y", "this_year", "Year", show=True),
        Binding("t", "this_month", "Month", show=True),
        Binding("a", "all_time", "All", show=True),
        Binding("1", "select_month_1", "Jan", show=False),
        Binding("2", "select_month_2", "Feb", show=False),
        Binding("3", "select_month_3", "Mar", show=False),
        Binding("4", "select_month_4", "Apr", show=False),
        Binding("5", "select_month_5", "May", show=False),
        Binding("6", "select_month_6", "Jun", show=False),
        Binding("7", "select_month_7", "Jul", show=False),
        Binding("8", "select_month_8", "Aug", show=False),
        Binding("9", "select_month_9", "Sep", show=False),
        # Sorting
        Binding("s", "toggle_sort_field", "Count/Amount", show=True),
        Binding("h,left", "reverse_sort", "Reverse", show=True),
        Binding("l,right", "reverse_sort", "Reverse", show=True),
        # Editing
        Binding("e", "edit_merchant", "Edit Merchant", show=False),
        Binding("r", "recategorize", "Recategorize", show=False),
        Binding("d", "delete_transaction", "Delete", show=False),
        Binding("space", "toggle_select", "Select", show=False),
        # Other actions
        Binding("f", "show_filters", "Filters", show=True),
        Binding("question_mark", "help", "Help", show=True, key_display="?"),
        Binding("slash", "search", "Search", show=True, key_display="/"),
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
                    email=creds["email"],
                    password=creds["password"],
                    use_saved_session=False,
                    save_session=True,
                    mfa_secret_key=creds["mfa_secret"],
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
                end_date = datetime.now().strftime("%Y-%m-%d")
                loading_status.update(
                    f"📊 Fetching transactions from {self.custom_start_date} onwards..."
                )
            elif self.start_year:
                start_date = f"{self.start_year}-01-01"
                end_date = datetime.now().strftime("%Y-%m-%d")
                loading_status.update(f"📊 Fetching transactions from {self.start_year} onwards...")
            else:
                # Fetch ALL transactions (no date filter for offline-first approach)
                start_date = None
                end_date = None
                loading_status.update("📊 Fetching ALL transaction data from Monarch Money...")

            loading_status.update(
                "⏳ This may take a minute for large accounts (10k+ transactions)..."
            )
            loading_status.update(
                "💡 TIP: This is a one-time download. Future operations will be instant!"
            )

            def update_progress(msg: str) -> None:
                """Update the loading status display."""
                loading_status.update(f"📊 {msg}")

            df, categories, category_groups = await self.data_manager.fetch_all_data(
                start_date=start_date, end_date=end_date, progress_callback=update_progress
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

        # Apply sorting
        sort_col = self.state.sort_by.value
        if sort_col == "amount":
            sort_col = "total"

        # Amount sorting: invert direction so largest expenses (-1000) come first
        descending = (
            self.state.sort_direction == SortDirection.ASC
            if sort_col == "total"
            else self.state.sort_direction == SortDirection.DESC
        )

        agg = agg.sort(sort_col, descending=descending)

        self.state.current_data = agg

        # Add rows
        for row in agg.iter_rows(named=True):
            merchant = row["merchant"] or "Unknown"
            count = row["count"]
            total = row["total"]
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

        # Apply sorting
        sort_col = self.state.sort_by.value
        if sort_col == "amount":
            sort_col = "total"

        # Amount sorting: invert direction so largest expenses (-1000) come first
        descending = (
            self.state.sort_direction == SortDirection.ASC
            if sort_col == "total"
            else self.state.sort_direction == SortDirection.DESC
        )

        agg = agg.sort(sort_col, descending=descending)

        self.state.current_data = agg

        for row in agg.iter_rows(named=True):
            category = row["category"] or "Uncategorized"
            count = row["count"]
            total = row["total"]
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

        # Apply sorting
        sort_col = self.state.sort_by.value
        if sort_col == "amount":
            sort_col = "total"

        # Amount sorting: invert direction so largest expenses (-1000) come first
        descending = (
            self.state.sort_direction == SortDirection.ASC
            if sort_col == "total"
            else self.state.sort_direction == SortDirection.DESC
        )

        agg = agg.sort(sort_col, descending=descending)

        self.state.current_data = agg

        for row in agg.iter_rows(named=True):
            group = row["group"] or "Other"
            count = row["count"]
            total = row["total"]
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
            date = str(row["date"])
            merchant = row["merchant"] or "Unknown"
            category = row["category"] or "Uncategorized"
            amount = row["amount"]
            flags = "H" if row.get("hideFromReports", False) else ""

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

        txn_count = stats["total_transactions"]
        total_amount = stats["total_amount"]

        stats_text = f"{txn_count:,} transactions | ${total_amount:,.2f} total"
        stats_widget.update(stats_text)

    def update_action_hints(self) -> None:
        """Update action hints based on current view."""
        hints_widget = self.query_one("#action-hints", Static)

        if self.state.view_mode == ViewMode.MERCHANT:
            hints = "[Enter] Drill down | [e] Edit merchant (bulk) | [s] Sort by | [h/l] Reverse"
        elif self.state.view_mode in [ViewMode.CATEGORY, ViewMode.GROUP]:
            hints = "[Enter] Drill down | [s] Sort by | [h/l] Reverse"
        else:  # DETAIL
            hints = "[e] Edit merchant | [r] Recategorize | [d] Delete | [Space] Select | [Esc] Back"

        hints_widget.update(hints)

        # Update pending changes
        changes_widget = self.query_one("#pending-changes", Static)
        count = self.data_manager.get_stats()["pending_changes"] if self.data_manager else 0
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

    def action_find_duplicates(self) -> None:
        """Find and display duplicate transactions."""
        if self.data_manager is None or self.data_manager.df is None:
            return

        from .duplicate_detector import DuplicateDetector
        from .screens.duplicates_screen import DuplicatesScreen

        # Find duplicates in current filtered view
        filtered_df = self.state.get_filtered_df()
        if filtered_df is None or filtered_df.is_empty():
            self.notify("No transactions to check", timeout=2)
            return

        self.notify("Scanning for duplicates...", timeout=1)
        duplicates = DuplicateDetector.find_duplicates(filtered_df)

        if duplicates.is_empty():
            self.notify("✅ No duplicates found!", severity="information", timeout=3)
        else:
            groups = DuplicateDetector.get_duplicate_groups(filtered_df, duplicates)
            # Show duplicates screen
            self.push_screen(DuplicatesScreen(duplicates, groups, filtered_df))

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

    def action_reverse_sort(self) -> None:
        """Reverse the current sort direction."""
        self.state.reverse_sort()
        self.refresh_view()
        direction = "Descending" if self.state.sort_direction == SortDirection.DESC else "Ascending"
        self.notify(f"Sort: {direction}", timeout=1)

    def action_toggle_sort_field(self) -> None:
        """Toggle between sorting by count and amount."""
        self.state.toggle_sort_field()
        self.refresh_view()
        field = "Count" if self.state.sort_by == SortMode.COUNT else "Amount"
        self.notify(f"Sorting by: {field}", timeout=1)

    def action_show_filters(self) -> None:
        """Show filter options modal."""
        self.run_worker(self._show_filter_modal(), exclusive=False)

    async def _show_filter_modal(self) -> None:
        """Show filter modal and apply selected filters."""
        from .screens.credential_screens import FilterScreen

        result = await self.push_screen(
            FilterScreen(show_transfers=self.state.show_transfers),
            wait_for_dismiss=True
        )

        if result is not None:
            # Apply filters
            self.state.show_transfers = result["show_transfers"]
            self.refresh_view()

            filter_status = "shown" if result["show_transfers"] else "hidden"
            self.notify(f"Transfers {filter_status}", timeout=2)

    def action_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())

    def action_search(self) -> None:
        """Show search input."""
        # TODO: Implement search modal
        self.notify("Search not yet implemented", timeout=2)

    def action_toggle_select(self) -> None:
        """Toggle selection of current row for bulk operations."""
        if self.data_manager is None or self.state.current_data is None:
            return

        table = self.query_one("#data-table", DataTable)
        if table.cursor_row < 0:
            return

        # Get the transaction ID from current row
        row_data = self.state.current_data.row(table.cursor_row, named=True)
        txn_id = row_data.get("id")

        if txn_id:
            self.state.toggle_selection(txn_id)
            count = len(self.state.selected_ids)
            self.notify(f"Selected: {count} transaction(s)", timeout=1)

    def action_edit_merchant(self) -> None:
        """Edit merchant name for current selection."""
        if self.data_manager is None:
            return

        # Check if in aggregate view or detail view
        if self.state.view_mode in [ViewMode.MERCHANT, ViewMode.CATEGORY, ViewMode.GROUP]:
            # Aggregate view - edit all transactions for this merchant
            self.run_worker(self._bulk_edit_merchant_from_aggregate(), exclusive=False)
        else:
            # Detail view - edit selected transaction(s)
            self.run_worker(self._edit_merchant_detail(), exclusive=False)

    async def _bulk_edit_merchant_from_aggregate(self) -> None:
        """Edit merchant for all transactions in selected aggregate row."""
        from .screens.edit_screens import EditMerchantScreen

        if self.state.current_data is None:
            return

        table = self.query_one("#data-table", DataTable)
        if table.cursor_row < 0:
            return

        # Get the merchant/category/group from current row
        row_data = self.state.current_data.row(table.cursor_row, named=True)

        if self.state.view_mode == ViewMode.MERCHANT:
            merchant_name = row_data["merchant"]
            transaction_count = row_data["count"]

            # Show edit modal
            new_merchant = await self.push_screen(
                EditMerchantScreen(merchant_name, transaction_count),
                wait_for_dismiss=True
            )

            if new_merchant:
                # Get all transactions for this merchant
                filtered_df = self.state.get_filtered_df()
                merchant_txns = self.data_manager.filter_by_merchant(filtered_df, merchant_name)

                # Add edits for all transactions
                for txn in merchant_txns.iter_rows(named=True):
                    self.data_manager.pending_edits.append(
                        TransactionEdit(
                            transaction_id=txn["id"],
                            field="merchant",
                            old_value=merchant_name,
                            new_value=new_merchant,
                            timestamp=datetime.now()
                        )
                    )

                self.notify(f"Queued {len(merchant_txns)} edits. Press Ctrl+S to save.", timeout=3)
                self.refresh_view()
        else:
            self.notify("Edit merchant only works from Merchant view", timeout=2)

    async def _edit_merchant_detail(self) -> None:
        """Edit merchant in detail view."""
        # TODO: Implement for detail view
        self.notify("Edit merchant in detail view not yet implemented", timeout=2)

    def action_recategorize(self) -> None:
        """Change category for current selection."""
        if self.data_manager is None:
            return

        self.run_worker(self._recategorize(), exclusive=False)

    async def _recategorize(self) -> None:
        """Show category selection and apply."""
        from .screens.edit_screens import SelectCategoryScreen
        from .state import TransactionEdit

        if self.state.current_data is None:
            return

        table = self.query_one("#data-table", DataTable)
        if table.cursor_row < 0:
            return

        # Show category selection
        new_category_id = await self.push_screen(
            SelectCategoryScreen(self.data_manager.categories),
            wait_for_dismiss=True
        )

        if new_category_id:
            # In detail view, categorize current transaction
            if self.state.view_mode == ViewMode.DETAIL:
                row_data = self.state.current_data.row(table.cursor_row, named=True)
                txn_id = row_data["id"]
                old_category_id = row_data["category_id"]

                self.data_manager.pending_edits.append(
                    TransactionEdit(
                        transaction_id=txn_id,
                        field="category",
                        old_value=old_category_id,
                        new_value=new_category_id,
                        timestamp=datetime.now()
                    )
                )

                self.notify("Category changed. Press Ctrl+S to save.", timeout=2)
                self.refresh_view()
            else:
                self.notify("Recategorize only works in transaction detail view", timeout=2)

    def action_delete_transaction(self) -> None:
        """Delete current transaction with confirmation."""
        if self.data_manager is None or self.state.view_mode != ViewMode.DETAIL:
            self.notify("Delete only works in transaction detail view", timeout=2)
            return

        self.run_worker(self._delete_transaction(), exclusive=False)

    async def _delete_transaction(self) -> None:
        """Show delete confirmation and delete if confirmed."""
        from .screens.edit_screens import DeleteConfirmationScreen

        if self.state.current_data is None:
            return

        table = self.query_one("#data-table", DataTable)
        if table.cursor_row < 0:
            return

        # Get current transaction
        row_data = self.state.current_data.row(table.cursor_row, named=True)
        txn_id = row_data["id"]

        # Show confirmation
        confirmed = await self.push_screen(
            DeleteConfirmationScreen(transaction_count=1),
            wait_for_dismiss=True
        )

        if confirmed:
            try:
                # Delete via API
                await self.mm.delete_transaction(txn_id)
                self.notify("Transaction deleted", severity="information", timeout=2)

                # Refresh data - need to re-fetch
                # For now, just notify user to refresh
                self.notify("Press Ctrl+L to refresh data from Monarch", timeout=3)
            except Exception as e:
                self.notify(f"Error deleting: {e}", severity="error", timeout=5)

    def action_go_back(self) -> None:
        """Go back to previous view."""
        if self.state.go_back():
            self.refresh_view()

    async def action_save(self) -> None:
        """Save pending changes."""
        if self.data_manager is None:
            return

        count = self.data_manager.get_stats()["pending_changes"]
        if count == 0:
            self.notify("No pending changes to save", timeout=2)
            return

        self.notify(f"Saving {count} change(s)...", timeout=3)

        try:
            success_count, failure_count = await self.data_manager.commit_pending_edits(
                self.data_manager.pending_edits
            )
            if failure_count > 0:
                self.notify(
                    f"Saved {success_count}, {failure_count} failed", severity="warning", timeout=5
                )
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
            (self.data_manager and self.data_manager.get_stats()["pending_changes"] > 0)
            if self.data_manager
            else False
        )

        should_quit = await self.push_screen(
            QuitConfirmationScreen(has_unsaved_changes=has_changes), wait_for_dismiss=True
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
        help="Only load transactions from this year onwards (e.g., --year 2025 loads from 2025-01-01 to now). Default: load all transactions.",
    )
    parser.add_argument(
        "--since",
        type=str,
        metavar="YYYY-MM-DD",
        help="Only load transactions from this date onwards (e.g., --since 2024-06-01). Overrides --year if both provided.",
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
