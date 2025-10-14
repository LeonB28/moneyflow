"""
Main moneyflow TUI Application.

A fast, keyboard-driven terminal interface for personal finance management.

This is the main application module containing the MoneyflowTUI class which:
- Coordinates all UI components (screens, widgets, data table)
- Handles keyboard bindings and user actions
- Manages application state and data loading
- Orchestrates the commit workflow

Architecture:
- UI Layer: This file (Textual screens and widgets)
- Business Logic: Extracted to service classes (ViewPresenter, TimeNavigator, CommitOrchestrator)
- Data Layer: DataManager handles API operations and Polars DataFrames
- State Layer: AppState holds application state

The separation allows business logic to be thoroughly tested while keeping
the UI layer thin and focused on rendering and user interaction.
"""

import argparse
import asyncio
import os
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable
import polars as pl

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, DataTable, Static, LoadingIndicator
from textual.reactive import reactive

from .backends import MonarchBackend, DemoBackend
from .data_manager import DataManager
from .state import AppState, ViewMode, SortMode, SortDirection, TimeFrame, TransactionEdit
from .widgets.help_screen import HelpScreen
from .formatters import ViewPresenter, AggregationField
from .time_navigator import TimeNavigator
from .commit_orchestrator import CommitOrchestrator
from .logging_config import setup_logging
from .notification_helper import NotificationHelper
from .modal_helper import ModalHelper
from .app_controller import AppController
from .textual_view import TextualViewPresenter


class MoneyflowTUI(App):
    """
    Main application class for the moneyflow terminal UI.

    This Textual application provides a keyboard-driven interface for managing
    personal finance transactions with a focus on power user workflows:

    **Key Features**:
    - Aggregated views (merchant, category, group, account)
    - Drill-down navigation with breadcrumbs
    - Bulk editing with multi-select
    - Time period navigation (year/month with arrow keys)
    - Search and filtering
    - Review-before-commit workflow
    - Offline-first (fetch once, work locally, commit when ready)

    **State Management**:
    - AppState: Holds all application state
    - DataManager: Manages transaction data and API operations
    - Backend: Pluggable backend (MonarchBackend, DemoBackend, etc.)

    **Keyboard Bindings**:
    See BINDINGS class attribute for full list. Key actions:
    - g: Cycle grouping modes
    - u: View all transactions
    - Enter: Drill down
    - Esc: Go back
    - m/r/h/d: Edit operations
    - w: Review and commit
    - ←/→: Navigate time periods
    - y/t/a: Year/month/all time

    **Architecture**:
    Business logic has been extracted to testable service classes:
    - ViewPresenter: Presentation logic (formatting, flags)
    - TimeNavigator: Date calculations
    - CommitOrchestrator: DataFrame updates after commits

    This allows the UI layer to focus on rendering and user interaction
    while keeping complex logic fully tested.
    """

    # Use Path object to properly resolve CSS file location
    # __file__ is moneyflow/app.py, so parent/styles/moneyflow.tcss is correct
    CSS_PATH = str(Path(__file__).parent / "styles" / "moneyflow.tcss")

    BINDINGS = [
        # View mode
        Binding("g", "cycle_grouping", "Group By", show=True),
        Binding("u", "view_ungrouped", "All Txns", show=True),
        Binding("D", "find_duplicates", "Duplicates", show=True, key_display="D"),
        # Hidden direct access bindings (still available in aggregate views, not shown in footer)
        # Note: 'm' conflicts with edit_merchant in detail view, so view_merchants removed
        Binding("c", "view_categories", "Categories", show=False),
        Binding("A", "view_accounts", "Accounts", show=False, key_display="A"),
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
        Binding("s", "toggle_sort_field", "Sort", show=True),
        Binding("v", "reverse_sort", "↕ Reverse", show=True),
        # Time navigation with arrows
        Binding("left", "prev_period", "← Prev", show=True),
        Binding("right", "next_period", "→ Next", show=True),
        # Editing
        Binding("m", "edit_merchant", "Edit Merchant", show=False),
        Binding("r", "recategorize", "Recategorize", show=False),
        Binding("d", "delete_transaction", "Delete", show=False),
        Binding("h", "toggle_hide_from_reports", "Hide/Unhide", show=False),
        Binding("i", "show_transaction_details", "Info", show=False),
        Binding("space", "toggle_select", "Select", show=False),
        # Other actions
        Binding("f", "show_filters", "Filters", show=True),
        Binding("question_mark", "help", "Help", show=True, key_display="?"),
        Binding("slash", "search", "Search", show=True, key_display="/"),
        Binding("escape", "go_back", "Back", show=False),
        Binding("w", "review_and_commit", "Commit", show=True),
        Binding("q", "quit_app", "Quit", show=True),
        Binding("ctrl+c", "quit_app", "Force Quit", show=False),  # Also allow Ctrl+C
    ]

    # Reactive state
    status_message = reactive("Ready")
    pending_changes_count = reactive(0)

    def _notify(self, notification_tuple: tuple[str, str, int]) -> None:
        """
        Wrapper for self.notify() that unpacks NotificationHelper tuples.

        Usage:
            self._notify(NotificationHelper.commit_success(10))

        Instead of:
            msg, severity, timeout = NotificationHelper.commit_success(10)
            self.notify(msg, severity=severity, timeout=timeout)
        """
        msg, severity, timeout = notification_tuple
        self.notify(msg, severity=severity, timeout=timeout)

    def __init__(
        self,
        start_year: Optional[int] = None,
        custom_start_date: Optional[str] = None,
        demo_mode: bool = False,
        cache_path: Optional[str] = None,
        force_refresh: bool = False,
    ):
        super().__init__()
        self.demo_mode = demo_mode
        self.start_year = start_year
        # Backend will be initialized in initialize_data() based on credentials
        self.mm = None
        if demo_mode:
            self.mm = DemoBackend(year=start_year or 2025)
            self.title = "moneyflow [DEMO MODE]"
        else:
            self.title = "moneyflow"
        self.data_manager: Optional[DataManager] = None
        self.state = AppState()
        self.loading = False
        self.custom_start_date = custom_start_date
        self.stored_credentials: Optional[dict] = None
        self.cache_path = cache_path
        self.force_refresh = force_refresh
        self.cache_manager = None  # Will be set if caching is enabled
        self.cache_year_filter = None  # Track what filters the cache uses
        self.cache_since_filter = None
        # Controller will be initialized after data_manager is ready
        self.controller: Optional[AppController] = None

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
        try:
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
        except Exception as e:
            # Try to show error to user
            try:
                loading_status = self.query_one("#loading-status", Static)
                loading_status.update(f"❌ Startup failed: {e}\n\nPress 'q' to quit")
                loading_status.display = True
            except:
                pass
            raise

    def _setup_loading_ui(self):
        """Setup loading UI and return loading status widget."""
        self.loading = True
        self.query_one("#loading", LoadingIndicator).display = True
        loading_status = self.query_one("#loading-status", Static)
        loading_status.display = True
        return loading_status

    def _initialize_managers(self):
        """Initialize data manager, cache manager, and controller."""
        self.data_manager = DataManager(self.mm)

        # Initialize cache manager only if user requested caching
        if self.cache_path is not None:
            from .cache_manager import CacheManager
            self.cache_manager = CacheManager(cache_dir=self.cache_path)

        # Initialize controller with view presenter pattern
        view = TextualViewPresenter(self)
        self.controller = AppController(view, self.state, self.data_manager, self.cache_manager)

    def _determine_date_range(self):
        """Determine date range based on CLI arguments.

        Returns:
            tuple: (start_date, end_date, cache_year_filter, cache_since_filter)
        """
        if self.custom_start_date:
            start_date = self.custom_start_date
            end_date = datetime.now().strftime("%Y-%m-%d")
            cache_year_filter = None
            cache_since_filter = self.custom_start_date
        elif self.start_year:
            start_date = f"{self.start_year}-01-01"
            end_date = datetime.now().strftime("%Y-%m-%d")
            cache_year_filter = self.start_year
            cache_since_filter = None
        else:
            # Fetch ALL transactions (no date filter for offline-first approach)
            start_date = None
            end_date = None
            cache_year_filter = None
            cache_since_filter = None

        return start_date, end_date, cache_year_filter, cache_since_filter

    def _store_data(self, df, categories, category_groups):
        """Store data in data manager and state."""
        self.data_manager.df = df
        self.data_manager.categories = categories
        self.data_manager.category_groups = category_groups
        self.state.transactions_df = df

    def _initialize_view(self):
        """Initialize time frame to THIS_YEAR and show initial view."""
        from datetime import date as date_type

        today = date_type.today()
        self.state.start_date = date_type(today.year, 1, 1)
        self.state.end_date = date_type(today.year, 12, 31)

        # Show initial view (merchants)
        self.refresh_view()

    async def _handle_credentials(self):
        """Handle credential unlock/setup flow.

        Returns:
            dict: Credentials dict or None if user exits
        """
        from .credentials import CredentialManager
        from .screens.credential_screens import (
            BackendSelectionScreen,
            CredentialSetupScreen,
            CredentialUnlockScreen,
        )

        cred_manager = CredentialManager()

        from .logging_config import get_logger
        logger = get_logger(__name__)
        logger.debug(f"Credentials exist: {cred_manager.credentials_exist()}")

        if cred_manager.credentials_exist():
            # Show unlock screen
            result = await self.push_screen(CredentialUnlockScreen(), wait_for_dismiss=True)

            if result is None:
                # User chose to reset - show backend selection then setup screen
                backend_type = await self.push_screen(
                    BackendSelectionScreen(), wait_for_dismiss=True
                )
                if not backend_type:
                    self.exit()
                    return None

                creds = await self.push_screen(
                    CredentialSetupScreen(backend_type=backend_type), wait_for_dismiss=True
                )
                if not creds:
                    self.exit()
                    return None
                return creds
            else:
                return result
        else:
            # No credentials - show backend selection first, then setup screen
            backend_type = await self.push_screen(
                BackendSelectionScreen(), wait_for_dismiss=True
            )
            if not backend_type:
                self.exit()
                return None

            creds = await self.push_screen(
                CredentialSetupScreen(backend_type=backend_type), wait_for_dismiss=True
            )
            if not creds:
                self.exit()
                return None
            return creds

    async def _login_with_retry(self, creds, loading_status):
        """Login with retry logic for robustness.

        Args:
            creds: Credentials dict
            loading_status: Loading status widget

        Returns:
            bool: True on success, False on failure
        """
        from .retry_logic import retry_with_backoff, RetryAborted
        from .logging_config import get_logger
        logger = get_logger(__name__)

        backend_type = creds.get("backend_type", "monarch")
        loading_status.update(f"🔐 Logging in to {backend_type.capitalize()}...")

        logger.debug(f"Starting login flow for {backend_type}")
        logger.debug(f"Email: {creds['email']}")
        logger.debug(f"Has MFA secret: {bool(creds.get('mfa_secret'))}")

        def on_login_retry(attempt: int, wait_seconds: float) -> None:
            """Show retry progress during login."""
            loading_status.update(
                f"⚠ Login failed. Retrying in {wait_seconds:.0f}s (attempt {attempt + 1}/5). Press Ctrl-C to abort."
            )

        async def login_operation():
            """Login with automatic retry on session expiration."""
            try:
                logger.debug("Attempting login with saved session...")
                await self.mm.login(
                    email=creds["email"],
                    password=creds["password"],
                    use_saved_session=True,  # Try saved session first
                    save_session=True,
                    mfa_secret_key=creds["mfa_secret"],
                )
                logger.debug("Login succeeded!")
                return True
            except Exception as e:
                logger.warning(f"Login failed: {e}", exc_info=True)
                error_str = str(e).lower()
                # Check if it's a stale session
                if "401" in error_str or "unauthorized" in error_str:
                    logger.debug("Detected stale session, deleting and retrying with fresh login")
                    self.mm.delete_session()
                    # Retry with fresh login
                    await self.mm.login(
                        email=creds["email"],
                        password=creds["password"],
                        use_saved_session=False,  # Force fresh login
                        save_session=True,
                        mfa_secret_key=creds["mfa_secret"],
                    )
                    logger.debug("Fresh login succeeded!")
                    return True
                # Not a session issue, re-raise for retry logic
                raise

        try:
            await retry_with_backoff(
                operation=login_operation,
                operation_name="Login to backend",
                max_retries=5,
                initial_wait=60.0,
                on_retry=on_login_retry
            )
            # Store credentials for automatic session refresh if needed
            self.stored_credentials = creds
            loading_status.update("✅ Logged in successfully!")
            logger.debug("Login flow completed successfully")
            return True
        except RetryAborted:
            # User pressed Ctrl-C
            logger.debug("Login cancelled by user")
            loading_status.update("Login cancelled by user. Press 'q' to quit.")
            return False
        except Exception as e:
            # All retries exhausted
            logger.error(f"Login failed after all retries: {e}", exc_info=True)
            error_msg = f"Login failed: {e}"
            loading_status.update(f"❌ {error_msg}\n\nCheck ~/.moneyflow/moneyflow.log for details.\n\nPress 'q' to quit")
            return False

    async def _check_and_load_cache(self, loading_status):
        """Check if cache is valid and load from cache if user approves.

        Args:
            loading_status: Loading status widget

        Returns:
            tuple: (df, categories, category_groups) or None if not using cache
        """
        use_cache = False
        if (
            self.cache_manager
            and not self.force_refresh
            and self.cache_manager.is_cache_valid(year=self.cache_year_filter, since=self.cache_since_filter)
        ):
            # Cache is valid - show prompt
            cache_info = self.cache_manager.get_cache_info()
            if cache_info:
                from .screens.credential_screens import CachePromptScreen

                use_cache = await self.push_screen(
                    CachePromptScreen(
                        age=cache_info["age"],
                        transaction_count=cache_info["transaction_count"],
                        filter_desc=cache_info["filter"],
                    ),
                    wait_for_dismiss=True,
                )

        if use_cache:
            # Load from cache
            loading_status.update("📦 Loading from cache...")
            result = self.cache_manager.load_cache()
            if result:
                df, categories, category_groups, metadata = result
                # Apply category grouping dynamically (so CATEGORY_GROUPS changes take effect)
                loading_status.update("🔄 Applying category groupings...")
                df = self.data_manager.apply_category_groups(df)
                loading_status.update(f"✅ Loaded {len(df):,} transactions from cache!")
                return df, categories, category_groups
            else:
                # Cache load failed, fall back to API
                loading_status.update("⚠ Cache load failed, fetching from API...")
                return None

        return None

    async def _fetch_data_with_retry(self, creds, start_date, end_date, loading_status):
        """Fetch data from API with retry logic.

        Args:
            creds: Credentials dict (may be None in demo mode)
            start_date: Start date for fetch
            end_date: End date for fetch
            loading_status: Loading status widget

        Returns:
            tuple: (df, categories, category_groups) or None on failure
        """
        from .retry_logic import retry_with_backoff, RetryAborted
        from .logging_config import get_logger
        logger = get_logger(__name__)

        # Update status based on date range
        if self.custom_start_date:
            loading_status.update(
                f"📊 Fetching transactions from {self.custom_start_date} onwards..."
            )
        elif self.start_year:
            loading_status.update(
                f"📊 Fetching transactions from {self.start_year} onwards..."
            )
        else:
            loading_status.update("📊 Fetching ALL transaction data from backend...")

        loading_status.update(
            "⏳ This may take a minute for large accounts (10k+ transactions)..."
        )
        loading_status.update(
            "💡 TIP: This is a one-time download. Future operations will be instant!"
        )

        def update_progress(msg: str) -> None:
            """Update the loading status display."""
            loading_status.update(f"📊 {msg}")

        def on_fetch_retry(attempt: int, wait_seconds: float) -> None:
            """Show retry progress during data fetch."""
            loading_status.update(
                f"⚠ Data fetch failed. Retrying in {wait_seconds:.0f}s (attempt {attempt + 1}/5). Press Ctrl-C to abort."
            )

        async def fetch_operation():
            """Fetch data with automatic error logging."""
            try:
                logger.debug(f"Fetching transactions (start={start_date}, end={end_date})")
                result = await self.data_manager.fetch_all_data(
                    start_date=start_date, end_date=end_date, progress_callback=update_progress
                )
                logger.debug(f"Data fetch succeeded - loaded {len(result[0])} transactions")
                return result
            except Exception as e:
                logger.error(f"Data fetch failed: {e}", exc_info=True)
                # Check if session expiration
                error_str = str(e).lower()
                if ("401" in error_str or "unauthorized" in error_str) and creds:
                    logger.info("Session expired during fetch, attempting fresh login...")
                    loading_status.update("🔄 Session expired. Re-authenticating...")
                    # Delete stale session and force fresh login
                    try:
                        self.mm.delete_session()
                        logger.info("Deleted stale session, attempting fresh login")
                        await self.mm.login(
                            email=creds["email"],
                            password=creds["password"],
                            use_saved_session=False,  # Force fresh login
                            save_session=True,
                            mfa_secret_key=creds["mfa_secret"],
                        )
                        logger.info("Fresh login succeeded, retrying fetch")
                        loading_status.update("✅ Re-authenticated. Retrying fetch...")
                        result = await self.data_manager.fetch_all_data(
                            start_date=start_date, end_date=end_date, progress_callback=update_progress
                        )
                        logger.info(f"Fetch retry succeeded - loaded {len(result[0])} transactions")
                        return result
                    except Exception as reauth_error:
                        logger.error(f"Re-authentication failed: {reauth_error}", exc_info=True)
                        # Re-auth failed, let retry logic handle it with backoff
                        raise Exception(f"Session refresh failed: {reauth_error}")
                # Not auth error, re-raise for retry logic
                raise

        try:
            df, categories, category_groups = await retry_with_backoff(
                operation=fetch_operation,
                operation_name="Fetch transaction data",
                max_retries=5,
                initial_wait=60.0,
                on_retry=on_fetch_retry
            )

            # Save to cache for next time (only if --cache was passed)
            if self.cache_manager:
                loading_status.update("💾 Saving to cache...")
                self.cache_manager.save_cache(
                    transactions_df=df,
                    categories=categories,
                    category_groups=category_groups,
                    year=self.cache_year_filter,
                    since=self.cache_since_filter,
                )
                loading_status.update(f"✅ Loaded {len(df):,} transactions and cached!")
            else:
                loading_status.update(f"✅ Loaded {len(df):,} transactions!")

            return df, categories, category_groups
        except RetryAborted:
            logger.debug("Data fetch cancelled by user")
            loading_status.update("Data fetch cancelled. Press 'q' to quit.")
            return None
        except Exception as e:
            logger.error(f"Data fetch failed after all retries: {e}", exc_info=True)
            loading_status.update(f"❌ Failed to load data: {e}\n\nCheck ~/.moneyflow/moneyflow.log for details.\n\nPress 'q' to quit")
            return None

    async def _handle_init_error(self, error, loading_status):
        """Handle initialization errors.

        Args:
            error: The exception that occurred
            loading_status: Loading status widget
        """
        from .logging_config import get_logger
        logger = get_logger(__name__)

        error_str = str(error).lower()

        # Check if it's a 401/unauthorized error
        if "401" in error_str or "unauthorized" in error_str:
            logger.error("401/Unauthorized in outer handler - recovery already attempted")
            # If we get here, session recovery already failed in the fetch block above
            # Delete the bad session
            try:
                if self.mm:
                    self.mm.delete_session()
                    logger.debug("Session deleted")
            except Exception as del_err:
                logger.error(f"Failed to delete session: {del_err}")

            # Show helpful error
            loading_status.update(
                f"❌ Session error.\n\n"
                f"Could not authenticate with backend.\n"
                f"Please restart the app to login fresh.\n\n"
                f"Press 'q' to quit"
            )
        else:
            error_msg = f"Failed to load data: {error}"
            loading_status.update(f"❌ {error_msg}\n\nPress 'q' to quit")

        # Log detailed error for debugging
        logger.error(f"DATA LOADING ERROR: {error} (Type: {type(error).__name__})", exc_info=True)

    async def initialize_data(self) -> None:
        """
        Load data from backend API or cache.

        This is the main orchestrator for data initialization. It coordinates:
        1. Credential handling (unlock/setup)
        2. Backend login with retry logic
        3. Cache checking and loading
        4. Data fetching from API with retry logic
        5. Data storage and view initialization
        6. Error handling and cleanup
        """
        from .logging_config import get_logger
        logger = get_logger(__name__)
        logger.debug("initialize_data started")
        has_error = False  # Track if we encountered an error

        # Setup loading UI
        try:
            loading_status = self._setup_loading_ui()
        except Exception as e:
            logger.error(f"Failed to initialize UI: {e}", exc_info=True)
            raise

        # Set initial status
        if self.demo_mode:
            loading_status.update("🎮 DEMO MODE - Loading sample data...")
        else:
            loading_status.update("🔄 Connecting to backend...")

        try:
            # Step 1: Handle credentials (if not demo mode)
            creds = None
            if not self.demo_mode:
                from .backends import get_backend

                creds = await self._handle_credentials()
                if creds is None:
                    return  # User exited

                # Initialize backend based on credentials
                backend_type = creds.get("backend_type", "monarch")
                loading_status.update(f"🔄 Initializing {backend_type} backend...")
                self.mm = get_backend(backend_type)

                # Step 2: Login with retry logic
                login_success = await self._login_with_retry(creds, loading_status)
                if not login_success:
                    has_error = True
                    return
            else:
                # Demo mode - no authentication needed
                loading_status.update("🎮 DEMO MODE - No authentication required")
                await self.mm.login()  # No-op for DemoBackend

            # Step 3: Initialize managers
            self._initialize_managers()

            # Step 4: Determine date range
            start_date, end_date, self.cache_year_filter, self.cache_since_filter = self._determine_date_range()

            # Step 5: Check and load cache
            cached_data = await self._check_and_load_cache(loading_status)

            if cached_data:
                df, categories, category_groups = cached_data
            else:
                # Step 6: Fetch from API with retry logic
                fetch_result = await self._fetch_data_with_retry(creds, start_date, end_date, loading_status)
                if fetch_result is None:
                    has_error = True
                    return
                df, categories, category_groups = fetch_result

            # Step 7: Store data
            self._store_data(df, categories, category_groups)

            # Step 8: Initialize view
            loading_status.update(f"✅ Ready! Showing {len(df):,} transactions")
            self._initialize_view()

        except Exception as e:
            await self._handle_init_error(e, loading_status)
            has_error = True

        finally:
            self.loading = False
            self.query_one("#loading", LoadingIndicator).display = False
            # DON'T hide loading-status if we had an error
            if not has_error:
                self.query_one("#loading-status", Static).display = False
            # If there was an error, keep the error message visible

    def update_loading_progress(self, current: int, total: int, message: str) -> None:
        """Update loading progress message."""
        self.status_message = f"{message} ({current}/{total})"

    def refresh_view(self, force_rebuild: bool = True) -> None:
        """
        Refresh the current view based on state.

        Delegates to AppController which handles all business logic.
        This method is now just a thin wrapper for backwards compatibility.

        Args:
            force_rebuild: If True, clear columns and rebuild entire table.
                          If False, only update rows (avoids flash when staying in same view).
        """
        if self.controller is None:
            return

        # Delegate to controller - it handles all the business logic
        self.controller.refresh_view(force_rebuild=force_rebuild)

    # Actions
    def _switch_to_aggregate_view(self, view_mode: ViewMode) -> None:
        """
        Helper to switch to an aggregate view.

        Clears selections, resets sort field to valid aggregate column, and refreshes.
        """
        self.state.view_mode = view_mode
        self.state.selected_merchant = None
        self.state.selected_category = None
        self.state.selected_group = None
        self.state.selected_account = None
        # Reset sort to valid field for aggregate views
        if self.state.sort_by not in [SortMode.COUNT, SortMode.AMOUNT]:
            self.state.sort_by = SortMode.AMOUNT
        self.refresh_view()

    def action_view_merchants(self) -> None:
        """Switch to merchant view."""
        self._switch_to_aggregate_view(ViewMode.MERCHANT)

    def action_view_categories(self) -> None:
        """Switch to category view."""
        self._switch_to_aggregate_view(ViewMode.CATEGORY)

    def action_view_groups(self) -> None:
        """Switch to group view."""
        self._switch_to_aggregate_view(ViewMode.GROUP)

    def action_view_accounts(self) -> None:
        """Switch to account view."""
        self._switch_to_aggregate_view(ViewMode.ACCOUNT)

    def action_cycle_grouping(self) -> None:
        """Cycle through aggregation views (Merchant → Category → Group → Account)."""
        view_name = self.state.cycle_grouping()
        if view_name:
            self.refresh_view()
            self._notify(NotificationHelper.view_changed(view_name))

    def action_view_ungrouped(self) -> None:
        """Switch to ungrouped transactions view (all transactions in reverse chronological order)."""
        self.state.view_mode = ViewMode.DETAIL
        self.state.selected_merchant = None
        self.state.selected_category = None
        self.state.selected_group = None
        self.state.selected_account = None
        # Set default sort for all transactions: Date descending (newest first)
        self.state.sort_by = SortMode.DATE
        self.state.sort_direction = SortDirection.DESC
        self.refresh_view()
        self._notify(NotificationHelper.all_transactions_view())

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

        today = date_type.today()
        date_range = TimeNavigator.get_month_range(today.year, month)

        self.state.set_timeframe(
            TimeFrame.CUSTOM,
            start_date=date_range.start_date,
            end_date=date_range.end_date
        )
        self.refresh_view()
        self.notify(f"Viewing: {date_range.description}", timeout=1)

    def action_prev_period(self) -> None:
        """Navigate to previous time period."""
        if self.state.start_date is None:
            # In all-time view, go to current year
            self.action_this_year()
            return

        date_range = TimeNavigator.previous_period(self.state.start_date, self.state.end_date)

        self.state.set_timeframe(
            TimeFrame.CUSTOM,
            start_date=date_range.start_date,
            end_date=date_range.end_date
        )
        self.notify(f"Viewing: {date_range.description}", timeout=1)
        self.refresh_view()

    def action_next_period(self) -> None:
        """Navigate to next time period."""
        if self.state.start_date is None:
            # In all-time view, go to current year
            self.action_this_year()
            return

        date_range = TimeNavigator.next_period(self.state.start_date, self.state.end_date)

        self.state.set_timeframe(
            TimeFrame.CUSTOM,
            start_date=date_range.start_date,
            end_date=date_range.end_date
        )
        self.notify(f"Viewing: {date_range.description}", timeout=1)
        self.refresh_view()

    def action_reverse_sort(self) -> None:
        """Reverse the current sort direction."""
        self.state.reverse_sort()
        self.refresh_view()
        direction = "Descending" if self.state.sort_direction == SortDirection.DESC else "Ascending"
        self.notify(f"Sort: {direction}", timeout=1)

    def action_toggle_sort_field(self) -> None:
        """Toggle sorting field."""
        # In detail view, cycle through: Date → Merchant → Category → Account → Amount → Date
        if self.state.view_mode == ViewMode.DETAIL:
            if self.state.sort_by == SortMode.DATE:
                self.state.sort_by = SortMode.MERCHANT
                field = "Merchant"
            elif self.state.sort_by == SortMode.MERCHANT:
                self.state.sort_by = SortMode.CATEGORY
                field = "Category"
            elif self.state.sort_by == SortMode.CATEGORY:
                self.state.sort_by = SortMode.ACCOUNT
                field = "Account"
            elif self.state.sort_by == SortMode.ACCOUNT:
                self.state.sort_by = SortMode.AMOUNT
                field = "Amount"
            else:  # AMOUNT or anything else
                self.state.sort_by = SortMode.DATE
                field = "Date"
        else:
            # In aggregate views, toggle between count and amount
            self.state.toggle_sort_field()
            field = "Count" if self.state.sort_by == SortMode.COUNT else "Amount"

        self.refresh_view()
        self.notify(f"Sorting by: {field}", timeout=1)

    def action_show_filters(self) -> None:
        """Show filter options modal."""
        self.run_worker(self._show_filter_modal(), exclusive=False)

    async def _show_filter_modal(self) -> None:
        """Show filter modal and apply selected filters."""
        from .screens.credential_screens import FilterScreen

        result = await self.push_screen(
            FilterScreen(
                show_transfers=self.state.show_transfers, show_hidden=self.state.show_hidden
            ),
            wait_for_dismiss=True,
        )

        if result is not None:
            # Apply filters
            self.state.show_transfers = result["show_transfers"]
            self.state.show_hidden = result["show_hidden"]
            self.refresh_view()

            # Build status message
            statuses = []
            if result["show_hidden"]:
                statuses.append("hidden items shown")
            else:
                statuses.append("hidden items excluded")
            if result["show_transfers"]:
                statuses.append("transfers shown")
            else:
                statuses.append("transfers excluded")

            self.notify(f"Filters: {', '.join(statuses)}", timeout=3)

    def action_help(self) -> None:
        """Show help screen."""
        self.push_screen(HelpScreen())

    def action_search(self) -> None:
        """Show search input with live filtering."""
        self.run_worker(self._show_search(), exclusive=False)

    async def _show_search(self) -> None:
        """Show search modal and apply filter."""
        from .screens.search_screen import SearchScreen

        # Show search modal with current query
        new_query = await self.push_screen(
            SearchScreen(current_query=self.state.search_query), wait_for_dismiss=True
        )

        if new_query is not None:  # None means cancelled
            # Apply search
            self.state.search_query = new_query
            self.refresh_view()

            if new_query:
                # Get count of filtered results
                filtered = self.state.get_filtered_df()
                count = len(filtered) if filtered is not None else 0
                self.notify(f"Search: '{new_query}' - {count} results", timeout=2)
            else:
                self.notify("Search cleared", timeout=1)

    def action_toggle_select(self) -> None:
        """Toggle selection of current row for bulk operations."""
        if self.data_manager is None or self.state.current_data is None:
            return

        table = self.query_one("#data-table", DataTable)
        if table.cursor_row < 0:
            return

        # Save cursor position
        saved_cursor_row = table.cursor_row

        # Get the transaction ID from current row
        row_data = self.state.current_data.row(table.cursor_row, named=True)
        txn_id = row_data.get("id")

        if txn_id:
            self.state.toggle_selection(txn_id)
            count = len(self.state.selected_ids)
            # Refresh view to show checkmark
            self.refresh_view()
            # Restore cursor position
            if saved_cursor_row < table.row_count:
                table.move_cursor(row=saved_cursor_row)
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
            total_amount = row_data["total"]

            # Get list of all merchants for suggestions
            if self.data_manager.df is None:
                return
            all_merchants = self.data_manager.df["merchant"].unique().to_list()

            # Pass aggregate summary for bulk edit
            bulk_summary = {
                "total_amount": total_amount,
            }

            # Show edit modal
            new_merchant = await self.push_screen(
                EditMerchantScreen(merchant_name, transaction_count, all_merchants, bulk_summary),
                wait_for_dismiss=True,
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
                            timestamp=datetime.now(),
                        )
                    )

                self._notify(NotificationHelper.edit_queued(len(merchant_txns)))
                self.refresh_view()
        else:
            self.notify("Edit merchant only works from Merchant view", timeout=2)

    async def _edit_merchant_detail(self) -> None:
        """Edit merchant in detail view."""
        from .screens.edit_screens import EditMerchantScreen

        if self.state.current_data is None:
            return

        table = self.query_one("#data-table", DataTable)
        if table.cursor_row < 0:
            return

        # Get current transaction
        row_data = self.state.current_data.row(table.cursor_row, named=True)
        current_merchant = row_data["merchant"]

        # Get list of all merchants for suggestions
        if self.data_manager.df is None:
            return
        all_merchants = self.data_manager.df["merchant"].unique().to_list()

        # Check if we have selected transactions for bulk edit
        if len(self.state.selected_ids) > 0:
            # Bulk edit selected transactions
            new_merchant = await self.push_screen(
                EditMerchantScreen(current_merchant, len(self.state.selected_ids), all_merchants),
                wait_for_dismiss=True,
            )

            if new_merchant:
                # Remember count before clearing
                num_selected = len(self.state.selected_ids)

                # Edit all selected transactions
                for txn_id in self.state.selected_ids:
                    # Find the transaction in current view
                    txn_rows = self.state.current_data.filter(pl.col("id") == txn_id)
                    if len(txn_rows) > 0:
                        txn = txn_rows.row(0, named=True)
                        self.data_manager.pending_edits.append(
                            TransactionEdit(
                                transaction_id=txn_id,
                                field="merchant",
                                old_value=txn["merchant"],
                                new_value=new_merchant,
                                timestamp=datetime.now(),
                            )
                        )

                self.state.clear_selection()
                self.notify(
                    f"Queued {num_selected} edits. Press w to review and commit.", timeout=3
                )
                # Refresh to update the * markers but stay in current view
                self.refresh_view()
        else:
            # Edit single transaction - pass details for context
            txn_details = {
                "date": row_data.get("date"),
                "amount": row_data.get("amount"),
                "category": row_data.get("category"),
            }

            new_merchant = await self.push_screen(
                EditMerchantScreen(current_merchant, 1, all_merchants, txn_details),
                wait_for_dismiss=True,
            )

            if new_merchant:
                # Save cursor position before refresh
                saved_cursor_row = table.cursor_row

                txn_id = row_data["id"]
                self.data_manager.pending_edits.append(
                    TransactionEdit(
                        transaction_id=txn_id,
                        field="merchant",
                        old_value=current_merchant,
                        new_value=new_merchant,
                        timestamp=datetime.now(),
                    )
                )

                self._notify(NotificationHelper.merchant_changed())
                # Refresh to show * marker, stays in detail view since view_mode unchanged
                self.refresh_view()
                # Restore cursor position
                if saved_cursor_row < table.row_count:
                    table.move_cursor(row=saved_cursor_row)

    def action_recategorize(self) -> None:
        """Change category for current selection (works in aggregate and detail views)."""
        from .logging_config import get_logger
        logger = get_logger(__name__)

        if self.data_manager is None:
            return

        logger.debug(f"action_recategorize called, view_mode={self.state.view_mode}")

        # Check if in aggregate view (MERCHANT, CATEGORY or GROUP) or detail view
        if self.state.view_mode in [ViewMode.MERCHANT, ViewMode.CATEGORY, ViewMode.GROUP]:
            logger.debug("Calling _bulk_recategorize_from_aggregate()")
            # Aggregate view - recategorize all transactions for this merchant/category/group
            self.run_worker(self._bulk_recategorize_from_aggregate(), exclusive=False)
        else:
            logger.debug(f"Calling _recategorize() - view_mode {self.state.view_mode} not in aggregate views")
            # Detail view - recategorize selected transaction(s)
            self.run_worker(self._recategorize(), exclusive=False)

    async def _bulk_recategorize_from_aggregate(self) -> None:
        """Recategorize all transactions in selected merchant/category/group."""
        from .screens.edit_screens import SelectCategoryScreen
        from .logging_config import get_logger
        logger = get_logger(__name__)

        logger.debug(f"_bulk_recategorize_from_aggregate called, view_mode={self.state.view_mode}")

        if self.state.current_data is None:
            logger.warning("current_data is None, returning")
            return

        table = self.query_one("#data-table", DataTable)
        if table.cursor_row < 0:
            logger.warning(f"cursor_row < 0 ({table.cursor_row}), returning")
            return

        # Get the merchant/category/group from current row
        row_data = self.state.current_data.row(table.cursor_row, named=True)
        logger.debug(f"row_data keys: {list(row_data.keys())}")

        # Determine what field we're grouping by and get transactions
        if self.state.view_mode == ViewMode.MERCHANT:
            field_name = row_data["merchant"]
            current_category_id = None  # Merchants can have mixed categories
            filter_func = self.data_manager.filter_by_merchant
        elif self.state.view_mode == ViewMode.CATEGORY:
            field_name = row_data["category"]
            current_category_id = row_data["category_id"]
            filter_func = self.data_manager.filter_by_category
        elif self.state.view_mode == ViewMode.GROUP:
            field_name = row_data["group"]
            current_category_id = None  # Groups can have mixed categories
            filter_func = self.data_manager.filter_by_group
        else:
            return

        # Show category selection modal
        new_category_id = await self.push_screen(
            SelectCategoryScreen(
                self.data_manager.categories,
                current_category_id,
                None  # No transaction details for bulk operations
            ),
            wait_for_dismiss=True,
        )

        # If user cancelled or selected same category, do nothing
        if not new_category_id or (current_category_id and new_category_id == current_category_id):
            return

        # Get all transactions for this merchant/category/group
        filtered_df = self.state.get_filtered_df()
        matching_txns = filter_func(filtered_df, field_name)

        # Add edits for all matching transactions
        for txn in matching_txns.iter_rows(named=True):
            self.data_manager.pending_edits.append(
                TransactionEdit(
                    transaction_id=txn["id"],
                    field="category",
                    old_value=txn["category_id"],
                    new_value=new_category_id,
                    timestamp=datetime.now(),
                )
            )

        # Show success notification
        new_cat_name = self.data_manager.categories.get(new_category_id, {}).get("name", "Unknown")
        self.notify(
            f"Queued {len(matching_txns)} transactions from {field_name} to recategorize to {new_cat_name}. Press w to commit.",
            timeout=3
        )
        self.refresh_view()

    async def _recategorize(self) -> None:
        """Show category selection and apply (for detail view)."""
        from .screens.edit_screens import SelectCategoryScreen
        from .state import TransactionEdit

        if self.state.current_data is None:
            return

        table = self.query_one("#data-table", DataTable)
        if table.cursor_row < 0:
            return

        # In detail view, categorize current transaction or selected transactions
        if self.state.view_mode == ViewMode.DETAIL:
            row_data = self.state.current_data.row(table.cursor_row, named=True)

            # Check if multi-select is active
            if len(self.state.selected_ids) > 0:
                # Multi-select recategorize
                num_selected = len(self.state.selected_ids)

                # Show category selection (no transaction details for bulk)
                new_category_id = await self.push_screen(
                    SelectCategoryScreen(
                        self.data_manager.categories,
                        row_data["category_id"],
                        None,  # No single transaction details for bulk operation
                    ),
                    wait_for_dismiss=True,
                )

                if new_category_id:
                    # Apply to all selected transactions
                    for txn_id in self.state.selected_ids:
                        txn_rows = self.state.current_data.filter(pl.col("id") == txn_id)
                        if len(txn_rows) > 0:
                            txn = txn_rows.row(0, named=True)
                            self.data_manager.pending_edits.append(
                                TransactionEdit(
                                    transaction_id=txn_id,
                                    field="category",
                                    old_value=txn["category_id"],
                                    new_value=new_category_id,
                                    timestamp=datetime.now(),
                                )
                            )

                    self.state.clear_selection()
                    self.notify(
                        f"Queued {num_selected} category changes. Press w to review and commit.",
                        timeout=3,
                    )
                    self.refresh_view()
            else:
                # Single transaction recategorize
                # Pass transaction details for context
                txn_details = {
                    "date": row_data.get("date"),
                    "amount": row_data.get("amount"),
                    "merchant": row_data.get("merchant"),
                }

                # Show category selection
                new_category_id = await self.push_screen(
                    SelectCategoryScreen(
                        self.data_manager.categories, row_data["category_id"], txn_details
                    ),
                    wait_for_dismiss=True,
                )

                if new_category_id:
                    # Save cursor position before refresh
                    saved_cursor_row = table.cursor_row

                    txn_id = row_data["id"]
                    old_category_id = row_data["category_id"]

                    self.data_manager.pending_edits.append(
                        TransactionEdit(
                            transaction_id=txn_id,
                            field="category",
                            old_value=old_category_id,
                            new_value=new_category_id,
                            timestamp=datetime.now(),
                        )
                    )

                    self.notify("Category changed. Press w to review and commit.", timeout=2)
                    # Refresh to show * marker, stays in detail view since view_mode unchanged
                    self.refresh_view()
                    # Restore cursor position
                    if saved_cursor_row < table.row_count:
                        table.move_cursor(row=saved_cursor_row)
        else:
            self.notify("Recategorize only works in transaction detail view", timeout=2)

    def action_toggle_hide_from_reports(self) -> None:
        """Toggle hide from reports flag for current transaction(s)."""
        if self.data_manager is None or self.state.view_mode != ViewMode.DETAIL:
            self.notify("Hide/unhide only works in transaction view", timeout=2)
            return

        if self.state.current_data is None:
            return

        table = self.query_one("#data-table", DataTable)
        if table.cursor_row < 0:
            return

        # Check if multi-select is active
        if len(self.state.selected_ids) > 0:
            # Toggle for all selected
            num_selected = len(self.state.selected_ids)
            for txn_id in self.state.selected_ids:
                txn_rows = self.state.current_data.filter(pl.col("id") == txn_id)
                if len(txn_rows) > 0:
                    txn = txn_rows.row(0, named=True)
                    current_hidden = txn.get("hideFromReports", False)
                    self.data_manager.pending_edits.append(
                        TransactionEdit(
                            transaction_id=txn_id,
                            field="hide_from_reports",
                            old_value=current_hidden,
                            new_value=not current_hidden,
                            timestamp=datetime.now(),
                        )
                    )

            self.state.clear_selection()
            self.notify(
                f"Toggled hide/unhide for {num_selected} transactions. Press w to commit.",
                timeout=3,
            )
            self.refresh_view()
        else:
            # Toggle single transaction
            row_data = self.state.current_data.row(table.cursor_row, named=True)
            txn_id = row_data["id"]
            current_hidden = row_data.get("hideFromReports", False)

            # Save cursor position before refresh
            saved_cursor_row = table.cursor_row

            self.data_manager.pending_edits.append(
                TransactionEdit(
                    transaction_id=txn_id,
                    field="hide_from_reports",
                    old_value=current_hidden,
                    new_value=not current_hidden,
                    timestamp=datetime.now(),
                )
            )

            action = "Unhidden" if current_hidden else "Hidden"
            self.notify(f"{action} from reports. Press w to commit.", timeout=2)
            self.refresh_view()
            # Restore cursor position
            if saved_cursor_row < table.row_count:
                table.move_cursor(row=saved_cursor_row)

    def action_show_transaction_details(self) -> None:
        """Show detailed information about current transaction."""
        if self.data_manager is None or self.state.view_mode != ViewMode.DETAIL:
            self.notify("Details only available in transaction view", timeout=2)
            return

        if self.state.current_data is None:
            return

        table = self.query_one("#data-table", DataTable)
        if table.cursor_row < 0:
            return

        # Get current transaction data
        row_data = self.state.current_data.row(table.cursor_row, named=True)

        # Show detail modal (doesn't change view state, just displays info)
        from .screens.transaction_detail_screen import TransactionDetailScreen

        self.push_screen(TransactionDetailScreen(dict(row_data)))

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
            DeleteConfirmationScreen(transaction_count=1), wait_for_dismiss=True
        )

        if confirmed:
            try:
                # Delete via API
                await self.mm.delete_transaction(txn_id)
                self.notify("Transaction deleted", severity="information", timeout=2)

                # Refresh data - need to re-fetch
                # For now, just notify user to refresh
                self.notify("Press Ctrl+L to refresh data from backend", timeout=3)
            except Exception as e:
                self.notify(f"Error deleting: {e}", severity="error", timeout=5)

    def action_go_back(self) -> None:
        """
        Go back to previous view and restore cursor position.

        To clear search: Press / then Enter with empty search box.
        """
        success, cursor_position = self.state.go_back()
        if success:
            self.refresh_view()
            # Restore cursor position
            table = self.query_one("#data-table", DataTable)
            if cursor_position >= 0 and cursor_position < table.row_count:
                table.move_cursor(row=cursor_position)

    async def _refresh_session(self) -> bool:
        """Refresh expired session by re-authenticating with stored credentials."""
        from .logging_config import get_logger
        logger = get_logger(__name__)

        if self.stored_credentials is None:
            logger.error("Cannot refresh session - no stored credentials")
            return False

        try:
            logger.info("Session expired - deleting stale session and re-authenticating")
            self._notify(NotificationHelper.session_refreshing())
            # CRITICAL: Delete stale session first (same as fetch_operation)
            self.mm.delete_session()
            logger.info("Deleted stale session, attempting fresh login")
            await self.mm.login(
                email=self.stored_credentials["email"],
                password=self.stored_credentials["password"],
                use_saved_session=False,  # Force fresh login
                save_session=True,
                mfa_secret_key=self.stored_credentials["mfa_secret"],
            )
            logger.info("Session refresh succeeded")
            self._notify(NotificationHelper.session_refresh_success())
            return True
        except Exception as e:
            logger.error(f"Session refresh failed: {e}", exc_info=True)
            self._notify(NotificationHelper.session_refresh_failed(str(e)))
            return False

    async def _commit_with_retry(self, edits):
        """
        Commit edits with automatic retry on session expiration.

        Uses exponential backoff (60s, 120s, 240s, 480s, 960s) for transient failures.
        User can press Ctrl-C to abort during retry waits.

        **User Experience:**
        - On auth error: "Session expired, re-authenticating..." → immediate retry
        - On other error: "Commit failed due to {reason}. Retrying in Xs (attempt N/5). Press Ctrl-C to abort."
        - On retry success: Returns normally (no extra notification)
        - On all retries exhausted: Re-raises exception (caller shows error)
        - On user cancel: "Commit cancelled by user"
        """
        from .retry_logic import retry_with_backoff, RetryAborted
        from .logging_config import get_logger
        logger = get_logger(__name__)

        def on_retry_notification(attempt: int, wait_seconds: float) -> None:
            """
            Show retry progress to user.

            Called AFTER the first failure and BEFORE waiting to retry.
            """
            self._notify(NotificationHelper.retry_waiting(attempt, wait_seconds))

        async def commit_operation():
            """Wrapper to commit and re-authenticate if needed."""
            try:
                return await self.data_manager.commit_pending_edits(edits)
            except Exception as e:
                # Check if it's an auth error (session expired)
                error_msg = str(e).lower()
                if "401" in error_msg or "unauthorized" in error_msg or "token" in error_msg:
                    logger.debug(f"Commit failed with auth error, attempting session refresh")
                    # Show clear message to user
                    self._notify(NotificationHelper.session_expired())
                    # Try to refresh session once
                    if await self._refresh_session():
                        logger.debug("Session refreshed, retrying commit immediately")
                        # Session refreshed - try commit again immediately
                        return await self.data_manager.commit_pending_edits(edits)
                    else:
                        logger.error("Session refresh failed")
                        # Session refresh failed - will trigger retry with backoff
                        raise Exception("Session refresh failed - will retry with backoff")
                # Re-raise for retry logic to handle
                logger.warning(f"Commit failed: {e}")
                raise

        try:
            # Use retry_with_backoff for robust error handling
            return await retry_with_backoff(
                operation=commit_operation,
                operation_name="Commit changes",
                max_retries=5,
                initial_wait=60.0,
                on_retry=on_retry_notification
            )
        except RetryAborted:
            # User pressed Ctrl-C
            logger.debug("Commit retry cancelled by user")
            self._notify(NotificationHelper.retry_cancelled())
            raise
        except Exception as e:
            # All retries exhausted
            logger.error(f"All commit retries exhausted: {e}")
            raise

    def action_review_and_commit(self) -> None:
        """Review pending changes and commit if confirmed."""
        if self.data_manager is None:
            return

        count = self.data_manager.get_stats()["pending_changes"]
        if count == 0:
            self._notify(NotificationHelper.no_pending_changes())
            return

        # Show review screen
        self.run_worker(self._review_and_commit(), exclusive=False)

    async def _review_and_commit(self) -> None:
        """Show review screen and commit if confirmed."""
        from .screens.review_screen import ReviewChangesScreen

        # Save view state before showing review screen
        saved_state = self.state.save_view_state()

        # Show review screen with category names for readable display
        should_commit = await self.push_screen(
            ReviewChangesScreen(self.data_manager.pending_edits, self.data_manager.categories),
            wait_for_dismiss=True,
        )

        if should_commit:
            count = len(self.data_manager.pending_edits)
            self._notify(NotificationHelper.commit_starting(count))

            try:
                success_count, failure_count = await self._commit_with_retry(
                    self.data_manager.pending_edits
                )

                # Show notification based on results
                if failure_count > 0:
                    self._notify(NotificationHelper.commit_partial(success_count, failure_count))
                else:
                    self._notify(NotificationHelper.commit_success(success_count))

                # Delegate to controller for data integrity logic
                # Controller handles: apply edits if success, preserve state if failure
                cache_filters = {
                    "year": self.cache_year_filter,
                    "since": self.cache_since_filter
                } if self.cache_manager else None

                self.controller.handle_commit_result(
                    success_count=success_count,
                    failure_count=failure_count,
                    edits=self.data_manager.pending_edits,
                    saved_state=saved_state,
                    cache_filters=cache_filters
                )
            except Exception as e:
                self._notify(NotificationHelper.commit_error(str(e)))
                # Restore view state even on error
                self.state.restore_view_state(saved_state)
                self.refresh_view(force_rebuild=False)
        else:
            # User pressed Escape - restore view state and refresh to go back to where they were
            self.state.restore_view_state(saved_state)
            self.refresh_view(force_rebuild=False)

    def action_quit_app(self) -> None:
        """Quit the application - show confirmation first."""
        # If we're in an error state (no data_manager), just exit immediately
        if self.data_manager is None:
            self.exit()
            return
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
        if self.state.view_mode in [
            ViewMode.MERCHANT,
            ViewMode.CATEGORY,
            ViewMode.GROUP,
            ViewMode.ACCOUNT,
        ]:
            # Drill down - save cursor position for restoration on go_back
            table = self.query_one("#data-table", DataTable)
            cursor_position = table.cursor_row
            row_key = event.row_key
            row = table.get_row(row_key)

            # First column is the item name
            item_name = str(row[0])
            self.state.drill_down(item_name, cursor_position)
            self.refresh_view()


def main():
    """Entry point for the TUI."""
    parser = argparse.ArgumentParser(
        description="moneyflow - Terminal UI for personal finance management"
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
    parser.add_argument(
        "--mtd",
        action="store_true",
        help="Load month-to-date transactions (from 1st of current month to today). Fast startup for editing recent transactions. Overrides --year and --since.",
    )
    parser.add_argument(
        "--cache",
        type=str,
        nargs="?",
        const="",  # Use default location if flag given without path
        metavar="PATH",
        help="Enable caching. Optionally specify cache directory (default: ~/.moneyflow/cache/). Without this flag, always fetches fresh data.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force refresh from API, skip cache even if valid cache exists",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode with sample data (no authentication required)",
    )

    args = parser.parse_args()

    # Initialize logging (file only - Textual swallows console output anyway)
    logger = setup_logging(console_output=False)
    logger.info("Starting moneyflow application")

    # Determine start year or date range
    start_year = None
    custom_start_date = None

    if args.mtd:
        # Month-to-date: Load from 1st of current month to today
        from datetime import date as date_type
        today = date_type.today()
        first_of_month = date_type(today.year, today.month, 1)
        custom_start_date = first_of_month.strftime("%Y-%m-%d")
    elif args.since:
        custom_start_date = args.since
    elif args.year:
        start_year = args.year

    # Handle cache path
    # If --cache passed without path, use empty string (triggers default in CacheManager)
    # If --cache not passed at all, args.cache is None (no caching)
    cache_path = args.cache if hasattr(args, "cache") and args.cache is not None else None

    try:
        app = MoneyflowTUI(
            start_year=start_year,
            custom_start_date=custom_start_date,
            demo_mode=args.demo,
            cache_path=cache_path,
            force_refresh=args.refresh,
        )

        app.run()
    except Exception as e:
        # Print full traceback to console
        print("\n" + "=" * 80, file=sys.stderr)
        print("FATAL ERROR - moneyflow TUI crashed!", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print("\n" + "=" * 80, file=sys.stderr)
        print("Please report this error with the traceback above.", file=sys.stderr)
        print("=" * 80 + "\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
