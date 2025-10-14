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

from typing import Optional, List
from .view_interface import IViewPresenter
from .state import AppState, ViewMode, SortMode, SortDirection, TransactionEdit
from .data_manager import DataManager
from .formatters import ViewPresenter
from .commit_orchestrator import CommitOrchestrator
from .logging_config import get_logger

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
        self,
        view: IViewPresenter,
        state: AppState,
        data_manager: DataManager,
        cache_manager = None
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
        if self.state.view_mode in [ViewMode.MERCHANT, ViewMode.CATEGORY, ViewMode.GROUP, ViewMode.ACCOUNT]:
            # All aggregate views use the same pattern
            view_data = self._prepare_aggregate_view(self.state.view_mode)
            if view_data is None:
                return

        elif self.state.view_mode == ViewMode.DETAIL:
            filtered_df = self.state.get_filtered_df()
            if filtered_df is None:
                return

            # Apply drill-down filters
            if self.state.selected_merchant:
                txns = self.data_manager.filter_by_merchant(filtered_df, self.state.selected_merchant)
            elif self.state.selected_category:
                txns = self.data_manager.filter_by_category(filtered_df, self.state.selected_category)
            elif self.state.selected_group:
                txns = self.data_manager.filter_by_group(filtered_df, self.state.selected_group)
            elif self.state.selected_account:
                txns = self.data_manager.filter_by_account(filtered_df, self.state.selected_account)
            else:
                txns = filtered_df

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
            )
        else:
            return

        # Delegate rendering to view - it handles the details of clearing/rebuilding
        self.view.update_table(
            columns=view_data["columns"],
            rows=view_data["rows"],
            force_rebuild=force_rebuild
        )

        # Update other UI elements
        self.view.update_breadcrumb(self.state.get_breadcrumb())

        # Calculate stats
        filtered_df = self.state.get_filtered_df()
        if filtered_df is not None and not filtered_df.is_empty():
            # Exclude hidden from totals
            non_hidden_df = filtered_df.filter(filtered_df["hideFromReports"] == False)
            import polars as pl
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

        # Apply sorting
        sort_col = self.state.sort_by.value
        if sort_col == "amount":
            sort_col = "total"  # Aggregations use "total" not "amount"
        descending = ViewPresenter.should_sort_descending(sort_col, self.state.sort_direction)
        if not agg.is_empty():
            agg = agg.sort(sort_col, descending=descending)

        self.state.current_data = agg
        return ViewPresenter.prepare_aggregation_view(
            agg, field_name, self.state.sort_by, self.state.sort_direction
        )

    # View mode switching operations
    def switch_to_merchant_view(self):
        """Switch to merchant aggregation view."""
        self.state.view_mode = ViewMode.MERCHANT
        self.state.selected_merchant = None
        self.state.selected_category = None
        self.state.selected_group = None
        self.state.selected_account = None
        # Reset sort to valid field for aggregate views
        if self.state.sort_by not in [SortMode.COUNT, SortMode.AMOUNT]:
            self.state.sort_by = SortMode.AMOUNT
        self.refresh_view()

    def switch_to_category_view(self):
        """Switch to category aggregation view."""
        self.state.view_mode = ViewMode.CATEGORY
        self.state.selected_merchant = None
        self.state.selected_category = None
        self.state.selected_group = None
        self.state.selected_account = None
        if self.state.sort_by not in [SortMode.COUNT, SortMode.AMOUNT]:
            self.state.sort_by = SortMode.AMOUNT
        self.refresh_view()

    def switch_to_group_view(self):
        """Switch to group aggregation view."""
        self.state.view_mode = ViewMode.GROUP
        self.state.selected_merchant = None
        self.state.selected_category = None
        self.state.selected_group = None
        self.state.selected_account = None
        if self.state.sort_by not in [SortMode.COUNT, SortMode.AMOUNT]:
            self.state.sort_by = SortMode.AMOUNT
        self.refresh_view()

    def switch_to_account_view(self):
        """Switch to account aggregation view."""
        self.state.view_mode = ViewMode.ACCOUNT
        self.state.selected_merchant = None
        self.state.selected_category = None
        self.state.selected_group = None
        self.state.selected_account = None
        if self.state.sort_by not in [SortMode.COUNT, SortMode.AMOUNT]:
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
        new_sort, display = self.get_next_sort_field(self.state.view_mode, self.state.sort_by)
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

    def get_next_sort_field(self, view_mode: ViewMode, current_sort: SortMode) -> tuple[SortMode, str]:
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

        Aggregate views toggle between 2 fields:
            Count ↔ Amount
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
            # Aggregate views toggle between count and amount
            if current_sort == SortMode.COUNT:
                return (SortMode.AMOUNT, "Amount")
            else:
                return (SortMode.COUNT, "Count")

    def _get_action_hints(self) -> str:
        """Get action hints text based on current view mode."""
        sort_name = self.state.sort_by.value.capitalize()

        if self.state.view_mode == ViewMode.MERCHANT:
            return f"Enter=Drill down | m=Edit merchant (bulk) | s=Sort({sort_name}) | g=Change grouping | ←/→=Change period"
        elif self.state.view_mode in [ViewMode.CATEGORY, ViewMode.GROUP]:
            return f"Enter=Drill down | r=Recategorize (bulk) | s=Sort({sort_name}) | g=Change grouping | ←/→=Change period"
        elif self.state.view_mode == ViewMode.ACCOUNT:
            return f"Enter=Drill down | s=Sort({sort_name}) | g=Change grouping | ←/→=Change period"
        else:  # DETAIL
            return f"s=Sort({sort_name}) | i=Info | m=Edit Merchant | r=Recategorize | h=Hide/Unhide | d=Delete | Space=Select"

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
        from datetime import datetime
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
        from datetime import datetime
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
        from datetime import datetime
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
        cache_filters: dict = None
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
            self.state.restore_view_state(saved_state)
            self.refresh_view(force_rebuild=False)  # Smooth update, same view
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

            # Restore view state and refresh to show updated data (smooth, no flash)
            self.state.restore_view_state(saved_state)
            self.refresh_view(force_rebuild=False)
