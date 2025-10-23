"""
Application controller - business logic without UI dependencies.

This module contains the AppController which orchestrates all business logic
for the application. It delegates all UI operations to an IViewPresenter,
making the business logic testable without requiring a UI.

The controller handles:
- View refresh logic (what to show, when to force rebuild)
- Navigation between views
- Commit workflow
- All business decisions

The controller does NOT:
- Render anything directly
- Know about Textual widgets
- Manage keyboard bindings (that's UI layer)
"""

from datetime import date as date_type
from datetime import datetime
from typing import List, Optional

import polars as pl

from .commit_orchestrator import CommitOrchestrator
from .data_manager import DataManager
from .formatters import ViewPresenter
from .logging_config import get_logger
from .state import AppState, SortDirection, SortMode, TimeFrame, TransactionEdit, ViewMode
from .time_navigator import TimeNavigator
from .view_interface import IViewPresenter

logger = get_logger(__name__)


class AppController:
    """
    UI-agnostic application controller.

    Handles all business logic and delegates UI operations to IViewPresenter.
    This separation allows testing business logic without running the TUI.

    Example:
        controller = AppController(view, state, data_manager)
        controller.refresh_view(force_rebuild=False)  # Smooth update
    """

    def __init__(
        self, view: IViewPresenter, state: AppState, data_manager: DataManager, cache_manager=None
    ):
        """
        Initialize controller.

        Args:
            view: UI implementation (TextualView, WebView, MockView, etc.)
            state: Application state
            data_manager: Data operations layer
            cache_manager: Optional cache manager for saving updated data
        """
        self.view = view
        self.state = state
        self.data_manager = data_manager
        self.cache_manager = cache_manager

    def _get_display_labels(self) -> dict:
        """Get display labels from backend, with safe fallback to defaults."""
        try:
            return self.data_manager.mm.get_display_labels()
        except (AttributeError, Exception):
            # Fallback to default labels if backend doesn't support it
            return {
                "merchant": "Merchant",
                "account": "Account",
                "accounts": "Accounts",
            }

    def _get_column_config(self) -> dict:
        """Get column configuration from backend, with safe fallback to defaults."""
        try:
            return self.data_manager.mm.get_column_config()
        except (AttributeError, Exception):
            # Fallback to default widths if backend doesn't support it
            return {
                "merchant_width_pct": 25,
                "account_width_pct": 15,
            }

    def refresh_view(self, force_rebuild: bool = True) -> None:
        """
        Refresh the current view.

        This is the core view refresh logic that was previously in MoneyflowTUI.
        Now it's testable business logic that delegates rendering to the view.

        Args:
            force_rebuild: If True, rebuild columns (view mode changed).
                          If False, update rows only (smooth update for same view).

        The business logic here decides:
        - What data to show (based on state.view_mode)
        - What columns/rows to prepare (using ViewPresenter)
        - Whether to rebuild or smooth update

        The view implementation handles:
        - How to render the table
        - How to clear columns/rows
        - Widget management
        """
        if self.data_manager is None or self.data_manager.df is None:
            return

        # Prepare view data based on current state
        if self.state.view_mode in [
            ViewMode.MERCHANT,
            ViewMode.CATEGORY,
            ViewMode.GROUP,
            ViewMode.ACCOUNT,
        ]:
            # All aggregate views use the same pattern
            view_data = self._prepare_aggregate_view(self.state.view_mode)
            if view_data is None:
                return

        elif self.state.view_mode == ViewMode.DETAIL:
            filtered_df = self.state.get_filtered_df()
            if filtered_df is None:
                return

            # Apply drill-down filters (can have multiple levels)
            # Apply in order: merchant → category → group → account
            txns = filtered_df

            if self.state.selected_merchant:
                txns = self.data_manager.filter_by_merchant(txns, self.state.selected_merchant)

            if self.state.selected_category:
                txns = self.data_manager.filter_by_category(txns, self.state.selected_category)

            if self.state.selected_group:
                txns = self.data_manager.filter_by_group(txns, self.state.selected_group)

            if self.state.selected_account:
                txns = self.data_manager.filter_by_account(txns, self.state.selected_account)

            # Check if sub-grouping is active (drilled down with aggregation)
            if self.state.is_drilled_down() and self.state.sub_grouping_mode:
                # Show aggregated view within drill-down
                sub_group_map = {
                    ViewMode.CATEGORY: (self.data_manager.aggregate_by_category, "category"),
                    ViewMode.GROUP: (self.data_manager.aggregate_by_group, "group"),
                    ViewMode.ACCOUNT: (self.data_manager.aggregate_by_account, "account"),
                    ViewMode.MERCHANT: (self.data_manager.aggregate_by_merchant, "merchant"),
                }

                aggregate_func, field_name = sub_group_map[self.state.sub_grouping_mode]
                agg = aggregate_func(txns)

                # Apply sorting with secondary sort key for deterministic ordering
                sort_col = self.state.sort_by.value
                if sort_col == "amount":
                    sort_col = "total"
                elif sort_col in ["merchant", "category", "group", "account"]:
                    sort_col = field_name

                descending = ViewPresenter.should_sort_descending(
                    sort_col, self.state.sort_direction
                )
                if not agg.is_empty():
                    # Use secondary sort by field_name for deterministic ordering
                    # when primary sort values are equal (e.g., same amount)
                    agg = agg.sort([sort_col, field_name], descending=[descending, False])

                self.state.current_data = agg

                # Get pending edit IDs for flags
                pending_edit_ids = {edit.transaction_id for edit in self.data_manager.pending_edits}

                view_data = ViewPresenter.prepare_aggregation_view(
                    agg,
                    field_name,
                    self.state.sort_by,
                    self.state.sort_direction,
                    detail_df=txns,
                    pending_edit_ids=pending_edit_ids,
                    selected_group_keys=self.state.selected_group_keys,
                    column_config=self._get_column_config(),
                    display_labels=self._get_display_labels(),
                )
            else:
                # Show detail view (normal behavior)
                # Sort
                if not txns.is_empty():
                    sort_field = self.state.sort_by.value
                    descending = ViewPresenter.should_sort_descending(
                        sort_field, self.state.sort_direction
                    )
                    txns = txns.sort(sort_field, descending=descending)

                self.state.current_data = txns

                # Get pending edit IDs
                pending_txn_ids = {edit.transaction_id for edit in self.data_manager.pending_edits}

                view_data = ViewPresenter.prepare_transaction_view(
                    txns,
                    self.state.sort_by,
                    self.state.sort_direction,
                    self.state.selected_ids,
                    pending_txn_ids,
                    column_config=self._get_column_config(),
                    display_labels=self._get_display_labels(),
                )
        else:
            return

        # Delegate rendering to view - it handles the details of clearing/rebuilding
        self.view.update_table(
            columns=view_data["columns"], rows=view_data["rows"], force_rebuild=force_rebuild
        )

        # Update other UI elements
        self.view.update_breadcrumb(self.state.get_breadcrumb(self._get_display_labels()))

        # Calculate stats
        filtered_df = self.state.get_filtered_df()
        if filtered_df is not None and not filtered_df.is_empty():
            # Exclude hidden from totals
            non_hidden_df = filtered_df.filter(~filtered_df["hideFromReports"])

            income_df = non_hidden_df.filter(pl.col("group") == "Income")
            total_income = float(income_df["amount"].sum()) if not income_df.is_empty() else 0.0
            expense_df = non_hidden_df.filter(
                (pl.col("group") != "Income") & (pl.col("group") != "Transfers")
            )
            total_expenses = float(expense_df["amount"].sum()) if not expense_df.is_empty() else 0.0
            net_savings = total_income + total_expenses

            stats_text = (
                f"{len(filtered_df):,} txns | "
                f"Income: ${total_income:,.2f} | "
                f"Expenses: ${total_expenses:,.2f} | "
                f"Savings: ${net_savings:,.2f}"
            )
            self.view.update_stats(stats_text)
        else:
            self.view.update_stats("0 txns | No data in view")

        # Update action hints
        hints_text = self._get_action_hints()
        self.view.update_hints(hints_text)

        # Update pending changes
        count = len(self.data_manager.pending_edits)
        self.view.update_pending_changes(count)

    def _prepare_aggregate_view(self, view_mode: ViewMode):
        """
        Prepare aggregated view data (merchant, category, group, or account).

        This helper eliminates 64 lines of duplication from refresh_view.
        The pattern is identical for all aggregate views:
        1. Get filtered data
        2. Aggregate by field
        3. Sort by current sort field
        4. Prepare view data

        Args:
            view_mode: Which aggregate view to prepare

        Returns:
            dict: View data with columns and rows, or None if no data
        """
        filtered_df = self.state.get_filtered_df()
        if filtered_df is None:
            return None

        # Map view mode to aggregation method and field name
        aggregation_map = {
            ViewMode.MERCHANT: (self.data_manager.aggregate_by_merchant, "merchant"),
            ViewMode.CATEGORY: (self.data_manager.aggregate_by_category, "category"),
            ViewMode.GROUP: (self.data_manager.aggregate_by_group, "group"),
            ViewMode.ACCOUNT: (self.data_manager.aggregate_by_account, "account"),
        }

        aggregate_func, field_name = aggregation_map[view_mode]
        agg = aggregate_func(filtered_df)

        # Apply sorting with secondary sort key for deterministic ordering
        sort_col = self.state.sort_by.value

        # Map sort field to actual column name in aggregation DataFrame
        if sort_col == "amount":
            sort_col = "total"  # Aggregations use "total" not "amount"
        elif sort_col in ["merchant", "category", "group", "account"]:
            # Use the grouping field name (e.g., "merchant" column in merchant aggregation)
            sort_col = field_name
        # else: "count" stays as "count"

        descending = ViewPresenter.should_sort_descending(sort_col, self.state.sort_direction)
        if not agg.is_empty():
            # Use secondary sort by field_name for deterministic ordering
            # when primary sort values are equal (e.g., same amount/count)
            agg = agg.sort([sort_col, field_name], descending=[descending, False])

        self.state.current_data = agg

        # Get pending edit transaction IDs for flags column
        pending_edit_ids = {edit.transaction_id for edit in self.data_manager.pending_edits}

        return ViewPresenter.prepare_aggregation_view(
            agg,
            field_name,
            self.state.sort_by,
            self.state.sort_direction,
            detail_df=filtered_df,
            pending_edit_ids=pending_edit_ids,
            selected_group_keys=self.state.selected_group_keys,
            column_config=self._get_column_config(),
            display_labels=self._get_display_labels(),
        )

    # View mode switching operations
    def switch_to_merchant_view(self):
        """Switch to merchant aggregation view."""
        self.state.view_mode = ViewMode.MERCHANT
        self.state.selected_merchant = None
        self.state.selected_category = None
        self.state.selected_group = None
        self.state.selected_account = None
        self.state.clear_selection()  # Clear all multi-select
        # Reset sort to valid field for aggregate views (now includes field name)
        if self.state.sort_by not in [SortMode.MERCHANT, SortMode.COUNT, SortMode.AMOUNT]:
            self.state.sort_by = SortMode.AMOUNT
        self.refresh_view()

    def switch_to_category_view(self):
        """Switch to category aggregation view."""
        self.state.view_mode = ViewMode.CATEGORY
        self.state.selected_merchant = None
        self.state.selected_category = None
        self.state.selected_group = None
        self.state.selected_account = None
        self.state.clear_selection()  # Clear all multi-select
        if self.state.sort_by not in [SortMode.CATEGORY, SortMode.COUNT, SortMode.AMOUNT]:
            self.state.sort_by = SortMode.AMOUNT
        self.refresh_view()

    def switch_to_group_view(self):
        """Switch to group aggregation view."""
        self.state.view_mode = ViewMode.GROUP
        self.state.selected_merchant = None
        self.state.selected_category = None
        self.state.selected_group = None
        self.state.selected_account = None
        self.state.clear_selection()  # Clear all multi-select
        if self.state.sort_by not in [SortMode.GROUP, SortMode.COUNT, SortMode.AMOUNT]:
            self.state.sort_by = SortMode.AMOUNT
        self.refresh_view()

    def switch_to_account_view(self):
        """Switch to account aggregation view."""
        self.state.view_mode = ViewMode.ACCOUNT
        self.state.selected_merchant = None
        self.state.selected_category = None
        self.state.selected_group = None
        self.state.selected_account = None
        self.state.clear_selection()  # Clear all multi-select
        if self.state.sort_by not in [SortMode.ACCOUNT, SortMode.COUNT, SortMode.AMOUNT]:
            self.state.sort_by = SortMode.AMOUNT
        self.refresh_view()

    def switch_to_detail_view(self, set_default_sort: bool = True):
        """
        Switch to transaction detail view (ungrouped).

        Args:
            set_default_sort: If True, set default sort (Date descending)
        """
        self.state.view_mode = ViewMode.DETAIL
        self.state.selected_merchant = None
        self.state.selected_category = None
        self.state.selected_group = None
        self.state.selected_account = None
        self.state.clear_selection()  # Clear all multi-select
        if set_default_sort:
            self.state.sort_by = SortMode.DATE
            self.state.sort_direction = SortDirection.DESC
        self.refresh_view()

    def cycle_grouping(self) -> Optional[str]:
        """
        Cycle through aggregation views (Merchant → Category → Group → Account).

        Returns:
            View name if changed, None if at end of cycle
        """
        view_name = self.state.cycle_grouping()
        if view_name:
            self.refresh_view()
        return view_name

    # Sorting operations
    def toggle_sort_field(self) -> str:
        """
        Toggle to next sort field based on current view mode.

        Returns:
            Display name of new sort field
        """
        # Determine effective view mode (sub_grouping_mode takes precedence when drilled down)
        effective_view_mode = self.state.view_mode
        if self.state.sub_grouping_mode and self.state.is_drilled_down():
            # In subgroup view - use sub_grouping_mode to determine sort options
            effective_view_mode = self.state.sub_grouping_mode

        new_sort, display = self.get_next_sort_field(effective_view_mode, self.state.sort_by)
        self.state.sort_by = new_sort
        self.refresh_view()
        return display

    def reverse_sort(self) -> str:
        """
        Reverse the current sort direction.

        Returns:
            Display name of new direction ("Ascending" or "Descending")
        """
        self.state.reverse_sort()
        self.refresh_view()
        return "Descending" if self.state.sort_direction == SortDirection.DESC else "Ascending"

    # Time navigation operations
    def set_timeframe_this_year(self):
        """Set view to current year."""
        self.state.set_timeframe(TimeFrame.THIS_YEAR)
        self.refresh_view()

    def set_timeframe_all_time(self):
        """Set view to all time."""
        self.state.set_timeframe(TimeFrame.ALL_TIME)
        self.refresh_view()

    def set_timeframe_this_month(self):
        """Set view to current month."""
        self.state.set_timeframe(TimeFrame.THIS_MONTH)
        self.refresh_view()

    def select_month(self, month: int) -> str:
        """
        Select a specific month of the current year.

        Args:
            month: Month number (1-12)

        Returns:
            Description of the selected time range
        """
        today = date_type.today()
        date_range = TimeNavigator.get_month_range(today.year, month)

        self.state.set_timeframe(
            TimeFrame.CUSTOM, start_date=date_range.start_date, end_date=date_range.end_date
        )
        self.refresh_view()
        return date_range.description

    def navigate_prev_period(self) -> tuple[bool, Optional[str]]:
        """
        Navigate to previous time period.

        Returns:
            Tuple of (should_fallback_to_year, description)
            - should_fallback_to_year: True if in all-time view (no prev period)
            - description: Time range description if navigated
        """
        if self.state.start_date is None:
            # In all-time view, signal to fallback to current year
            return (True, None)

        date_range = TimeNavigator.previous_period(self.state.start_date, self.state.end_date)
        self.state.set_timeframe(
            TimeFrame.CUSTOM, start_date=date_range.start_date, end_date=date_range.end_date
        )
        self.refresh_view()
        return (False, date_range.description)

    def navigate_next_period(self) -> tuple[bool, Optional[str]]:
        """
        Navigate to next time period.

        Returns:
            Tuple of (should_fallback_to_year, description)
            - should_fallback_to_year: True if in all-time view (no next period)
            - description: Time range description if navigated
        """
        if self.state.start_date is None:
            # In all-time view, signal to fallback to current year
            return (True, None)

        date_range = TimeNavigator.next_period(self.state.start_date, self.state.end_date)
        self.state.set_timeframe(
            TimeFrame.CUSTOM, start_date=date_range.start_date, end_date=date_range.end_date
        )
        self.refresh_view()
        return (False, date_range.description)

    # Data access methods (read-only)
    def get_filtered_df(self):
        """Get filtered DataFrame for current view."""
        return self.state.get_filtered_df()

    def get_current_data(self):
        """Get current view data (aggregated or detail)."""
        return self.state.current_data

    def get_merchant_suggestions(self) -> list[str]:
        """
        Get list of all merchants for autocomplete.

        Returns merchants from both:
        - Cached historical merchants (refreshed daily)
        - Currently loaded transactions (includes recent edits)
        """
        return self.data_manager.get_all_merchants_for_autocomplete()

    def get_categories(self) -> dict:
        """Get category map."""
        return self.data_manager.categories

    def get_pending_changes_count(self) -> int:
        """Get count of pending edits."""
        return self.data_manager.get_stats()["pending_changes"]

    def get_pending_edits(self):
        """Get pending edits for review."""
        return self.data_manager.pending_edits

    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes."""
        return self.get_pending_changes_count() > 0

    def get_view_mode(self) -> ViewMode:
        """Get current view mode."""
        return self.state.view_mode

    def get_selected_ids(self) -> set:
        """Get currently selected transaction IDs."""
        return self.state.selected_ids

    # Search and filtering operations
    def apply_search(self, query: str) -> int:
        """
        Apply search query.

        Args:
            query: Search query string

        Returns:
            Count of filtered results
        """
        self.state.set_search(query)
        self.refresh_view()
        filtered = self.state.get_filtered_df()
        return len(filtered) if filtered is not None else 0

    def clear_search(self):
        """Clear search query."""
        self.state.set_search("")
        self.refresh_view()

    def apply_filters(self, show_transfers: bool, show_hidden: bool):
        """Apply visibility filters."""
        self.state.show_transfers = show_transfers
        self.state.show_hidden = show_hidden
        self.refresh_view()

    def toggle_selection(self, txn_id: str) -> int:
        """
        Toggle transaction selection.

        Args:
            txn_id: Transaction ID to toggle

        Returns:
            Total count of selected transactions
        """
        self.state.toggle_selection(txn_id)
        return len(self.state.selected_ids)

    def clear_selection(self):
        """Clear all selections."""
        self.state.clear_selection()

    def drill_down(self, item_name: str, cursor_position: int, scroll_y: float = 0.0):
        """
        Drill down into an item (merchant/category/group/account).

        Args:
            item_name: Name of item to drill into
            cursor_position: Current cursor position to save for go_back
            scroll_y: Current scroll position to save for go_back
        """
        self.state.drill_down(item_name, cursor_position, scroll_y)
        self.refresh_view()

    def go_back(self) -> tuple[bool, int, float]:
        """
        Go back to previous view.

        Returns:
            Tuple of (success, cursor_position, scroll_y)
            - success: True if went back, False if already at top
            - cursor_position: Where to restore cursor
            - scroll_y: Where to restore scroll position
        """
        success, cursor_position, scroll_y = self.state.go_back()
        if success:
            self.refresh_view()
        return (success, cursor_position, scroll_y)

    def get_next_sort_field(
        self, view_mode: ViewMode, current_sort: SortMode
    ) -> tuple[SortMode, str]:
        """
        Determine the next sort field when user toggles sorting.

        This is pure business logic - a state machine for sort field cycling.
        Different cycling behavior for detail view vs aggregate views.

        Args:
            view_mode: Current view mode
            current_sort: Current sort field

        Returns:
            Tuple of (new_sort_mode, display_name)

        Detail view cycles through 5 fields:
            Date → Merchant → Category → Account → Amount → Date (loop)

        Aggregate views cycle through 3 fields:
            Name → Count → Amount → Name (loop)
            where Name is the grouping field (Merchant/Category/Group/Account)
        """
        if view_mode == ViewMode.DETAIL:
            # 5-field cycle for transaction detail view
            if current_sort == SortMode.DATE:
                return (SortMode.MERCHANT, "Merchant")
            elif current_sort == SortMode.MERCHANT:
                return (SortMode.CATEGORY, "Category")
            elif current_sort == SortMode.CATEGORY:
                return (SortMode.ACCOUNT, "Account")
            elif current_sort == SortMode.ACCOUNT:
                return (SortMode.AMOUNT, "Amount")
            else:  # AMOUNT or anything else
                return (SortMode.DATE, "Date")
        else:
            # Aggregate views cycle: Field name → Count → Amount → Field name
            # Map view mode to its field SortMode
            view_to_field_sort = {
                ViewMode.MERCHANT: (SortMode.MERCHANT, "Merchant"),
                ViewMode.CATEGORY: (SortMode.CATEGORY, "Category"),
                ViewMode.GROUP: (SortMode.GROUP, "Group"),
                ViewMode.ACCOUNT: (SortMode.ACCOUNT, "Account"),
            }

            field_sort, field_name = view_to_field_sort.get(view_mode, (SortMode.COUNT, "Count"))

            # Cycle through: Field → Count → Amount → Field
            if current_sort == field_sort:
                return (SortMode.COUNT, "Count")
            elif current_sort == SortMode.COUNT:
                return (SortMode.AMOUNT, "Amount")
            else:
                return (field_sort, field_name)

    def _get_action_hints(self) -> str:
        """Get action hints text based on current view mode."""
        sort_name = self.state.sort_by.value.capitalize()

        if self.state.view_mode == ViewMode.MERCHANT:
            return f"Enter=Drill | Space=Select | m=✏️ Merchant (bulk) | c=✏️ Category (bulk) | s=Sort({sort_name}) | g=Group"
        elif self.state.view_mode in [ViewMode.CATEGORY, ViewMode.GROUP]:
            return f"Enter=Drill | Space=Select | m=✏️ Merchant (bulk) | c=✏️ Category (bulk) | s=Sort({sort_name}) | g=Group"
        elif self.state.view_mode == ViewMode.ACCOUNT:
            return f"Enter=Drill | Space=Select | m=✏️ Merchant (bulk) | c=✏️ Category (bulk) | s=Sort({sort_name}) | g=Group"
        else:  # DETAIL
            # Check if we're in a drilled-down view or ungrouped view
            if (
                self.state.selected_merchant
                or self.state.selected_category
                or self.state.selected_group
                or self.state.selected_account
            ):
                return "Esc/g=Back | m=✏️ Merchant | c=✏️ Category | h=Hide | Space=Select | Ctrl-A=SelectAll"
            else:
                return "g=Group | m=✏️ Merchant | c=✏️ Category | h=Hide | Space=Select | Ctrl-A=SelectAll"

    def queue_category_edits(self, transactions_df, new_category_id: str) -> int:
        """
        Queue category edits for a set of transactions.

        This is pure business logic - no UI dependencies. Can be tested independently.

        Args:
            transactions_df: Polars DataFrame of transactions to edit
            new_category_id: New category ID to apply

        Returns:
            int: Number of edits queued
        """
        count = 0
        for txn in transactions_df.iter_rows(named=True):
            self.data_manager.pending_edits.append(
                TransactionEdit(
                    transaction_id=txn["id"],
                    field="category",
                    old_value=txn["category_id"],
                    new_value=new_category_id,
                    timestamp=datetime.now(),
                )
            )
            count += 1
        return count

    def queue_merchant_edits(self, transactions_df, old_merchant: str, new_merchant: str) -> int:
        """
        Queue merchant edits for a set of transactions.

        This is pure business logic - no UI dependencies. Can be tested independently.

        Args:
            transactions_df: Polars DataFrame of transactions to edit
            old_merchant: Original merchant name (for documentation, not used in logic)
            new_merchant: New merchant name to apply

        Returns:
            int: Number of edits queued
        """
        count = 0
        for txn in transactions_df.iter_rows(named=True):
            self.data_manager.pending_edits.append(
                TransactionEdit(
                    transaction_id=txn["id"],
                    field="merchant",
                    old_value=txn["merchant"],  # Use actual current value from transaction
                    new_value=new_merchant,
                    timestamp=datetime.now(),
                )
            )
            count += 1
        return count

    def queue_hide_toggle_edits(self, transactions_df) -> int:
        """
        Queue hide/unhide toggle edits for a set of transactions.

        This toggles the hideFromReports flag for each transaction.
        This is pure business logic - no UI dependencies. Can be tested independently.

        Args:
            transactions_df: Polars DataFrame of transactions to toggle

        Returns:
            int: Number of edits queued
        """
        count = 0
        for txn in transactions_df.iter_rows(named=True):
            current_hidden = txn.get("hideFromReports", False)
            self.data_manager.pending_edits.append(
                TransactionEdit(
                    transaction_id=txn["id"],
                    field="hide_from_reports",
                    old_value=current_hidden,
                    new_value=not current_hidden,
                    timestamp=datetime.now(),
                )
            )
            count += 1
        return count

    def handle_commit_result(
        self,
        success_count: int,
        failure_count: int,
        edits: List[TransactionEdit],
        saved_state: dict,
        cache_filters: dict = None,
    ) -> None:
        """
        Handle commit results and update local state accordingly.

        This is the CRITICAL data integrity logic that prevents corruption.
        Previously this was in _review_and_commit() in app.py, mixed with
        modal handling and retry logic.

        **The Rule:**
        - If ANY commits failed → DO NOT apply edits locally
        - Only if ALL succeed → Apply edits and clear pending list

        This separation allows testing the data integrity logic without
        dealing with network/session issues.

        Args:
            success_count: Number of successful commits
            failure_count: Number of failed commits
            edits: List of edits that were attempted
            saved_state: View state to restore after commit
            cache_filters: Optional dict with year/since filters for cache

        Side effects:
            - May update data_manager.df and state.transactions_df
            - May clear data_manager.pending_edits
            - May update cache
            - Calls refresh_view() with force_rebuild=False
        """
        logger.info(f"handle_commit_result: {success_count} succeeded, {failure_count} failed")

        # CRITICAL: Only apply changes locally if ALL commits succeeded
        if failure_count > 0:
            logger.warning(f"Commit had {failure_count} failures - NOT applying edits locally")
            # Some or all commits failed - DO NOT apply to local state
            # This prevents data corruption where UI shows changes that didn't save
            # Note: View already restored in app.py before commit started
            # Just refresh to ensure UI shows current (unchanged) state
            logger.debug("Failure path - refreshing view (state already restored in app.py)")
            self.refresh_view(force_rebuild=False)
        else:
            logger.info("All commits succeeded - applying edits locally")
            # All commits succeeded - safe to apply to local state

            # Apply edits to local DataFrames for instant UI update
            # Use CommitOrchestrator to apply all edits (fully tested)
            self.data_manager.df = CommitOrchestrator.apply_edits_to_dataframe(
                self.data_manager.df,
                edits,
                self.data_manager.categories,
                self.data_manager.apply_category_groups,
            )

            # Also update state DataFrame
            if self.state.transactions_df is not None:
                self.state.transactions_df = CommitOrchestrator.apply_edits_to_dataframe(
                    self.state.transactions_df,
                    edits,
                    self.data_manager.categories,
                    self.data_manager.apply_category_groups,
                )

            # Clear pending edits on success
            self.data_manager.pending_edits.clear()
            logger.info("Cleared pending edits")

            # Update cache with edited data (if caching is enabled)
            if self.cache_manager and cache_filters:
                try:
                    logger.debug("Updating cache with committed changes")
                    self.cache_manager.save_cache(
                        transactions_df=self.data_manager.df,
                        categories=self.data_manager.categories,
                        category_groups=self.data_manager.category_groups,
                        year=cache_filters.get("year"),
                        since=cache_filters.get("since"),
                    )
                except Exception as e:
                    # Cache update failed - not critical, just log
                    logger.warning(f"Cache update failed: {e}", exc_info=True)

            # Refresh to show updated data (smooth update)
            # Note: View already restored in app.py before commit started
            logger.debug(
                f"Success path - refreshing to show updated data. Current view_mode={self.state.view_mode}, selected_category={self.state.selected_category}"
            )
            self.refresh_view(force_rebuild=False)
            logger.debug(f"After refresh: view_mode={self.state.view_mode}")

    def get_transactions_from_selected_groups(self, group_by_field: str) -> pl.DataFrame:
        """
        Get all transactions from selected groups in aggregate view.

        Args:
            group_by_field: Field to filter by ('merchant', 'category', 'group', 'account')

        Returns:
            DataFrame of all transactions from selected groups
        """
        if not self.state.selected_group_keys:
            return pl.DataFrame()

        filtered_df = self.state.get_filtered_df()
        if filtered_df is None:
            return pl.DataFrame()

        # Filter to transactions in any of the selected groups
        all_txns = pl.DataFrame()
        for group_key in self.state.selected_group_keys:
            if group_by_field == "merchant":
                group_txns = self.data_manager.filter_by_merchant(filtered_df, group_key)
            elif group_by_field == "category":
                group_txns = self.data_manager.filter_by_category(filtered_df, group_key)
            elif group_by_field == "group":
                group_txns = self.data_manager.filter_by_group(filtered_df, group_key)
            elif group_by_field == "account":
                group_txns = self.data_manager.filter_by_account(filtered_df, group_key)
            else:
                continue

            if all_txns.is_empty():
                all_txns = group_txns
            else:
                all_txns = pl.concat([all_txns, group_txns])

        return all_txns
