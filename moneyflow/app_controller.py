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

from typing import Optional
from .view_interface import IViewPresenter
from .state import AppState, ViewMode, SortMode
from .data_manager import DataManager
from .formatters import ViewPresenter


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
        data_manager: DataManager
    ):
        """
        Initialize controller.

        Args:
            view: UI implementation (TextualView, WebView, MockView, etc.)
            state: Application state
            data_manager: Data operations layer
        """
        self.view = view
        self.state = state
        self.data_manager = data_manager

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
        if self.state.view_mode == ViewMode.MERCHANT:
            filtered_df = self.state.get_filtered_df()
            if filtered_df is None:
                return
            agg = self.data_manager.aggregate_by_merchant(filtered_df)
            # Apply sorting
            sort_col = self.state.sort_by.value
            if sort_col == "amount":
                sort_col = "total"
            descending = ViewPresenter.should_sort_descending(sort_col, self.state.sort_direction)
            if not agg.is_empty():
                agg = agg.sort(sort_col, descending=descending)
            self.state.current_data = agg
            view_data = ViewPresenter.prepare_aggregation_view(
                agg, "merchant", self.state.sort_by, self.state.sort_direction
            )

        elif self.state.view_mode == ViewMode.CATEGORY:
            filtered_df = self.state.get_filtered_df()
            if filtered_df is None:
                return
            agg = self.data_manager.aggregate_by_category(filtered_df)
            sort_col = self.state.sort_by.value
            if sort_col == "amount":
                sort_col = "total"
            descending = ViewPresenter.should_sort_descending(sort_col, self.state.sort_direction)
            if not agg.is_empty():
                agg = agg.sort(sort_col, descending=descending)
            self.state.current_data = agg
            view_data = ViewPresenter.prepare_aggregation_view(
                agg, "category", self.state.sort_by, self.state.sort_direction
            )

        elif self.state.view_mode == ViewMode.GROUP:
            filtered_df = self.state.get_filtered_df()
            if filtered_df is None:
                return
            agg = self.data_manager.aggregate_by_group(filtered_df)
            sort_col = self.state.sort_by.value
            if sort_col == "amount":
                sort_col = "total"
            descending = ViewPresenter.should_sort_descending(sort_col, self.state.sort_direction)
            if not agg.is_empty():
                agg = agg.sort(sort_col, descending=descending)
            self.state.current_data = agg
            view_data = ViewPresenter.prepare_aggregation_view(
                agg, "group", self.state.sort_by, self.state.sort_direction
            )

        elif self.state.view_mode == ViewMode.ACCOUNT:
            filtered_df = self.state.get_filtered_df()
            if filtered_df is None:
                return
            agg = self.data_manager.aggregate_by_account(filtered_df)
            sort_col = self.state.sort_by.value
            if sort_col == "amount":
                sort_col = "total"
            descending = ViewPresenter.should_sort_descending(sort_col, self.state.sort_direction)
            if not agg.is_empty():
                agg = agg.sort(sort_col, descending=descending)
            self.state.current_data = agg
            view_data = ViewPresenter.prepare_aggregation_view(
                agg, "account", self.state.sort_by, self.state.sort_direction
            )

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
