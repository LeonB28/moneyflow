"""
App state management with change tracking and undo/redo support.

This module contains the central AppState class that holds all application state
including view mode, filters, selections, and pending edits. State should be data,
not operations - complex operations belong in separate service classes.
"""

from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, date
from enum import Enum
from typing import Any, Optional, List, Dict
import polars as pl

from .time_navigator import TimeNavigator


class ViewMode(Enum):
    """Available view modes for transaction aggregation."""

    MERCHANT = "merchant"
    CATEGORY = "category"
    GROUP = "group"
    ACCOUNT = "account"
    DETAIL = "detail"


class SortMode(Enum):
    """Sorting options for transactions."""

    COUNT = "count"
    AMOUNT = "amount"
    DATE = "date"
    MERCHANT = "merchant"
    CATEGORY = "category"
    GROUP = "group"
    ACCOUNT = "account"


class SortDirection(Enum):
    """Sort direction."""

    DESC = "desc"
    ASC = "asc"


class TimeFrame(Enum):
    """Time frame for filtering transactions."""

    ALL_TIME = "all_time"
    THIS_YEAR = "this_year"
    THIS_MONTH = "this_month"
    CUSTOM = "custom"


@dataclass
class TransactionEdit:
    """
    Represents a pending transaction edit.

    Tracks a single change to a transaction (merchant, category, or hide flag)
    before it's committed to the backend API.
    """

    transaction_id: str
    field: str  # 'merchant', 'category', 'hide_from_reports'
    old_value: Any
    new_value: Any
    timestamp: datetime = dataclass_field(default_factory=datetime.now)  # When edit was queued


@dataclass
class AppState:
    """
    Central application state container.

    This class holds all state for the TUI application including:
    - Transaction data (Polars DataFrame)
    - View configuration (mode, sorting, time filters)
    - Navigation state (selected items, drill-down context)
    - Pending edits (before commit to API)
    - Search and filter settings

    The state is designed to be serializable and supports view state
    save/restore for complex navigation workflows (e.g., during commit review).

    Note: This class should primarily hold DATA, not implement complex operations.
    Business logic belongs in service classes (DataManager, FilterService, etc.).
    """

    # Data
    transactions_df: Optional[pl.DataFrame] = None
    categories: Dict[str, Any] = dataclass_field(default_factory=dict)
    category_groups: Dict[str, Any] = dataclass_field(default_factory=dict)
    merchants: Dict[str, Any] = dataclass_field(default_factory=dict)

    # View state
    view_mode: ViewMode = ViewMode.MERCHANT
    sort_by: SortMode = SortMode.AMOUNT  # What to sort by (count/amount/date)
    sort_direction: SortDirection = SortDirection.DESC  # Direction (asc/desc)
    time_frame: TimeFrame = TimeFrame.THIS_YEAR

    # Time filtering
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    # Navigation
    selected_merchant: Optional[str] = None
    selected_category: Optional[str] = None
    selected_group: Optional[str] = None
    selected_account: Optional[str] = None
    selected_row: int = 0

    # Sub-grouping when drilled down (e.g., "Merchant > Amazon (by Category)")
    # When set, shows aggregated view of filtered data instead of detail view
    # Cycles: Category → Group → Account → None (detail) → Category...
    sub_grouping_mode: Optional[ViewMode] = None

    # Multi-select for bulk operations
    selected_ids: set[str] = dataclass_field(default_factory=set)

    # Search/filter
    search_query: str = ""
    show_transfers: bool = False  # Whether to show Transfer category transactions
    show_hidden: bool = True  # Whether to show transactions hidden from reports

    # Change tracking
    pending_edits: List[TransactionEdit] = dataclass_field(default_factory=list)
    undo_stack: List[TransactionEdit] = dataclass_field(default_factory=list)
    redo_stack: List[TransactionEdit] = dataclass_field(default_factory=list)

    # UI state
    loading: bool = False
    error_message: Optional[str] = None
    status_message: Optional[str] = None

    # Current view data (for display)
    current_data: Optional[pl.DataFrame] = None

    # Navigation history for breadcrumb and back navigation
    # Stores (view_mode, cursor_position) for restoring state on go_back
    navigation_history: List[tuple[ViewMode, int]] = dataclass_field(default_factory=list)

    def add_edit(self, transaction_id: str, field: str, old_value: Any, new_value: Any):
        """Add a pending edit to the change tracker."""
        edit = TransactionEdit(
            transaction_id=transaction_id, field=field, old_value=old_value, new_value=new_value
        )
        self.pending_edits.append(edit)
        self.undo_stack.append(edit)
        # Clear redo stack when new edit is made
        self.redo_stack.clear()

    def undo_last_edit(self) -> Optional[TransactionEdit]:
        """Undo the last edit."""
        if not self.undo_stack:
            return None

        edit = self.undo_stack.pop()
        self.redo_stack.append(edit)

        # Remove from pending edits
        if edit in self.pending_edits:
            self.pending_edits.remove(edit)

        return edit

    def redo_last_edit(self) -> Optional[TransactionEdit]:
        """Redo the last undone edit."""
        if not self.redo_stack:
            return None

        edit = self.redo_stack.pop()
        self.undo_stack.append(edit)
        self.pending_edits.append(edit)

        return edit

    def clear_pending_edits(self):
        """Clear all pending edits after successful commit."""
        self.pending_edits.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()

    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes."""
        return len(self.pending_edits) > 0

    def toggle_selection(self, transaction_id: str):
        """Toggle selection of a transaction for bulk operations."""
        if transaction_id in self.selected_ids:
            self.selected_ids.remove(transaction_id)
        else:
            self.selected_ids.add(transaction_id)

    def clear_selection(self):
        """Clear all selected transactions."""
        self.selected_ids.clear()

    def set_timeframe(
        self,
        timeframe: TimeFrame,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> None:
        """
        Set the time frame for filtering transactions.

        Uses TimeNavigator for date calculations to avoid duplication
        and ensure consistency with tested logic.

        Args:
            timeframe: The time frame to set
            start_date: Start date for CUSTOM timeframe
            end_date: End date for CUSTOM timeframe

        Examples:
            >>> state = AppState()
            >>> state.set_timeframe(TimeFrame.THIS_YEAR)
            >>> state.start_date.month == 1  # January
            True
            >>> state.end_date.month == 12  # December
            True
        """
        self.time_frame = timeframe

        if timeframe == TimeFrame.CUSTOM:
            self.start_date = start_date
            self.end_date = end_date
        elif timeframe == TimeFrame.THIS_YEAR:
            date_range = TimeNavigator.get_current_year_range()
            self.start_date = date_range.start_date
            self.end_date = date_range.end_date
        elif timeframe == TimeFrame.THIS_MONTH:
            date_range = TimeNavigator.get_current_month_range()
            self.start_date = date_range.start_date
            self.end_date = date_range.end_date
        else:  # ALL_TIME
            self.start_date = None
            self.end_date = None

    def reverse_sort(self):
        """Reverse the current sort direction."""
        if self.sort_direction == SortDirection.DESC:
            self.sort_direction = SortDirection.ASC
        else:
            self.sort_direction = SortDirection.DESC

    def toggle_sort_field(self):
        """Toggle between sorting by count and amount."""
        if self.sort_by == SortMode.COUNT:
            self.sort_by = SortMode.AMOUNT
        else:
            self.sort_by = SortMode.COUNT

    def is_drilled_down(self) -> bool:
        """Check if we're currently drilled down into a specific item."""
        return any([
            self.selected_merchant,
            self.selected_category,
            self.selected_group,
            self.selected_account,
        ])

    def cycle_sub_grouping(self) -> str:
        """
        Cycle through sub-grouping modes when drilled down.

        Order: CATEGORY → GROUP → ACCOUNT → None (detail) → CATEGORY

        Skips the current top-level grouping (e.g., if drilled into merchant,
        don't offer merchant as sub-grouping).

        Returns:
            Name of the new sub-grouping mode for notification
        """
        # Define cycle order (excluding the parent grouping)
        available_modes = []

        # Add modes that aren't the current top-level view
        if self.view_mode != ViewMode.CATEGORY:
            available_modes.append(ViewMode.CATEGORY)
        if self.view_mode != ViewMode.GROUP:
            available_modes.append(ViewMode.GROUP)
        if self.view_mode != ViewMode.ACCOUNT:
            available_modes.append(ViewMode.ACCOUNT)

        # Add None for detail view
        available_modes.append(None)

        # Find current index
        try:
            current_idx = available_modes.index(self.sub_grouping_mode)
        except ValueError:
            current_idx = -1

        # Cycle to next
        next_idx = (current_idx + 1) % len(available_modes)
        self.sub_grouping_mode = available_modes[next_idx]

        # Return display name
        if self.sub_grouping_mode is None:
            return "Detail"
        elif self.sub_grouping_mode == ViewMode.CATEGORY:
            return "by Category"
        elif self.sub_grouping_mode == ViewMode.GROUP:
            return "by Group"
        elif self.sub_grouping_mode == ViewMode.ACCOUNT:
            return "by Account"
        else:
            return ""

    def cycle_grouping(self) -> str:
        """
        Cycle through grouping modes.

        If drilled down: Cycle sub-groupings within current filter
        If not drilled down: Cycle top-level aggregation views

        Returns:
            Name of the new view mode for notification
        """
        # If drilled down, cycle sub-grouping instead
        if self.is_drilled_down():
            return self.cycle_sub_grouping()

        # Only cycle if in an aggregation view (not DETAIL)
        if self.view_mode == ViewMode.DETAIL:
            return ""

        # Clear any drill-down selections when switching views
        self.selected_merchant = None
        self.selected_category = None
        self.selected_group = None
        self.selected_account = None
        self.sub_grouping_mode = None  # Clear sub-grouping too

        # Reset sort to valid field for aggregate views if needed
        # Now includes field-based sorting (MERCHANT, CATEGORY, GROUP, ACCOUNT)
        if self.sort_by not in [
            SortMode.COUNT,
            SortMode.AMOUNT,
            SortMode.MERCHANT,
            SortMode.CATEGORY,
            SortMode.GROUP,
            SortMode.ACCOUNT,
        ]:
            self.sort_by = SortMode.AMOUNT

        # Cycle through views
        if self.view_mode == ViewMode.MERCHANT:
            self.view_mode = ViewMode.CATEGORY
            return "Categories"
        elif self.view_mode == ViewMode.CATEGORY:
            self.view_mode = ViewMode.GROUP
            return "Groups"
        elif self.view_mode == ViewMode.GROUP:
            self.view_mode = ViewMode.ACCOUNT
            return "Accounts"
        elif self.view_mode == ViewMode.ACCOUNT:
            self.view_mode = ViewMode.MERCHANT
            return "Merchants"

        return ""

    def get_filtered_df(self) -> Optional[pl.DataFrame]:
        """
        Get filtered DataFrame based on current state.

        Applies multiple filters in sequence:
        1. Time range filter (start_date/end_date)
        2. Search query filter (merchant/category text search)
        3. Group filter (hide Transfers unless enabled)
        4. Hidden transactions filter (hide if show_hidden=False)
        5. Drill-down filter (if viewing specific merchant/category/etc)

        Returns:
            Filtered DataFrame or None if no data loaded

        Note: This method contains business logic (Polars operations) that
        ideally should be extracted to a FilterService for better testability.
        See SECOND_PASS_ANALYSIS.md for refactoring plan.
        """
        if self.transactions_df is None:
            return None

        df = self.transactions_df

        # Apply time filter
        if self.start_date and self.end_date:
            df = df.filter((pl.col("date") >= self.start_date) & (pl.col("date") <= self.end_date))

        # Apply search filter
        if self.search_query:
            query = self.search_query.lower()
            df = df.filter(
                pl.col("merchant").str.to_lowercase().str.contains(query)
                | pl.col("category").str.to_lowercase().str.contains(query)
            )

        # Apply group filter (hide Transfers unless enabled)
        if not self.show_transfers:
            df = df.filter(pl.col("group") != "Transfers")

        # Apply hidden filter (hide transactions marked hideFromReports unless enabled)
        if not self.show_hidden:
            df = df.filter(pl.col("hideFromReports") == False)

        # Apply view-specific filters
        if self.view_mode == ViewMode.DETAIL:
            if self.selected_merchant:
                df = df.filter(pl.col("merchant") == self.selected_merchant)
            elif self.selected_category:
                df = df.filter(pl.col("category") == self.selected_category)
            elif self.selected_group:
                df = df.filter(pl.col("group") == self.selected_group)
            elif self.selected_account:
                df = df.filter(pl.col("account") == self.selected_account)

        return df

    def drill_down(self, item_name: str, cursor_position: int = 0) -> None:
        """
        Drill down from aggregate view into transaction detail view.

        When viewing an aggregate (e.g., Merchants view) and user presses Enter
        on a row, this method saves the current view context to navigation history
        and transitions to DETAIL view filtered to that item.

        Args:
            item_name: The merchant/category/group/account name to drill into
            cursor_position: Current cursor row position to save for go_back()

        Examples:
            >>> state = AppState()
            >>> state.view_mode = ViewMode.MERCHANT
            >>> state.drill_down("Amazon", cursor_position=5)
            >>> state.view_mode
            <ViewMode.DETAIL: 'detail'>
            >>> state.selected_merchant
            'Amazon'
            >>> state.navigation_history[-1]
            (<ViewMode.MERCHANT: 'merchant'>, 5)
        """
        # Save current state to history (view mode + cursor position)
        self.navigation_history.append((self.view_mode, cursor_position))

        # Set the selected item based on current view
        if self.view_mode == ViewMode.MERCHANT:
            self.selected_merchant = item_name
            self.view_mode = ViewMode.DETAIL
        elif self.view_mode == ViewMode.CATEGORY:
            self.selected_category = item_name
            self.view_mode = ViewMode.DETAIL
        elif self.view_mode == ViewMode.GROUP:
            self.selected_group = item_name
            self.view_mode = ViewMode.DETAIL
        elif self.view_mode == ViewMode.ACCOUNT:
            self.selected_account = item_name
            self.view_mode = ViewMode.DETAIL

    def go_back(self) -> tuple[bool, int]:
        """
        Go back to previous view.

        If sub-grouping is active: Clear sub-grouping first (stay drilled down)
        If drilled down (no sub-grouping): Go back to parent view
        If at top-level: Do nothing

        Returns:
            Tuple of (success: bool, cursor_position: int)
            success=True if went back, False if already at root
            cursor_position=Row to restore cursor to (0 if none saved)
        """
        # If in sub-grouped view, clear sub-grouping first (stay drilled down)
        if self.is_drilled_down() and self.sub_grouping_mode:
            self.sub_grouping_mode = None
            return True, 0

        if self.view_mode == ViewMode.DETAIL:
            # Check if we have multiple levels of drill-down
            # Clear the deepest level first (in reverse order: Account → Group → Category → Merchant)
            if self.selected_account and not self.selected_category and not self.selected_group and not self.selected_merchant:
                # At Account level only - go back to parent
                self.selected_account = None
            elif self.selected_group and not self.selected_category and not self.selected_merchant:
                # At Group level only - go back to parent
                self.selected_group = None
            elif self.selected_category and not self.selected_merchant:
                # At Category level only - go back to parent
                self.selected_category = None
            elif self.selected_account:
                # Multi-level: clear deepest (Account)
                self.selected_account = None
                return True, 0
            elif self.selected_group:
                # Multi-level: clear deepest (Group)
                self.selected_group = None
                return True, 0
            elif self.selected_category:
                # Multi-level: clear deepest (Category)
                self.selected_category = None
                return True, 0
            elif self.selected_merchant:
                # Only Merchant selected - clear it
                self.selected_merchant = None
            else:
                # Nothing selected, shouldn't get here
                pass

            self.sub_grouping_mode = None  # Clear sub-grouping too

            # Pop from history if available
            cursor_position = 0
            if self.navigation_history:
                previous_view, cursor_position = self.navigation_history.pop()
                self.view_mode = previous_view
            else:
                # Default back to MERCHANT view
                self.view_mode = ViewMode.MERCHANT

            # Reset sort to valid field for aggregate views
            # (Detail views can have DATE, MERCHANT, CATEGORY, ACCOUNT, AMOUNT)
            # (Aggregate views have COUNT, AMOUNT, and field-based sorting)
            if self.sort_by not in [
                SortMode.COUNT,
                SortMode.AMOUNT,
                SortMode.MERCHANT,
                SortMode.CATEGORY,
                SortMode.GROUP,
                SortMode.ACCOUNT,
            ]:
                self.sort_by = SortMode.AMOUNT
                self.sort_direction = SortDirection.DESC

            return True, cursor_position

        # Already at a top-level view
        return False, 0

    def save_view_state(self) -> dict:
        """
        Save complete view state for later restoration.

        Saves everything that defines the current view including:
        - View mode and drill-down selections
        - Sort settings (column and direction)
        - Time filtering (time_frame and date range)
        - Search query
        - Filter settings (show_transfers, show_hidden)

        Used during commit review workflow to preserve the exact user context
        and return to it seamlessly after commit or cancel.
        """
        return {
            "view_mode": self.view_mode,
            "selected_merchant": self.selected_merchant,
            "selected_category": self.selected_category,
            "selected_group": self.selected_group,
            "selected_account": self.selected_account,
            "sort_by": self.sort_by,
            "sort_direction": self.sort_direction,
            "time_frame": self.time_frame,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "search_query": self.search_query,
            "show_transfers": self.show_transfers,
            "show_hidden": self.show_hidden,
        }

    def restore_view_state(self, saved_state: dict) -> None:
        """Restore complete view state including all filters and sort settings."""
        self.view_mode = saved_state["view_mode"]
        self.selected_merchant = saved_state["selected_merchant"]
        self.selected_category = saved_state["selected_category"]
        self.selected_group = saved_state["selected_group"]
        self.selected_account = saved_state.get("selected_account")
        self.sort_by = saved_state.get("sort_by", self.sort_by)
        self.sort_direction = saved_state.get("sort_direction", self.sort_direction)
        self.time_frame = saved_state.get("time_frame", self.time_frame)
        self.start_date = saved_state.get("start_date", self.start_date)
        self.end_date = saved_state.get("end_date", self.end_date)
        self.search_query = saved_state.get("search_query", self.search_query)
        self.show_transfers = saved_state.get("show_transfers", self.show_transfers)
        self.show_hidden = saved_state.get("show_hidden", self.show_hidden)

    def get_breadcrumb(self) -> str:
        """Get breadcrumb string showing current navigation path."""
        parts = []

        # Add view mode
        if self.view_mode == ViewMode.MERCHANT:
            parts.append("Merchants")
        elif self.view_mode == ViewMode.CATEGORY:
            parts.append("Categories")
        elif self.view_mode == ViewMode.GROUP:
            parts.append("Groups")
        elif self.view_mode == ViewMode.ACCOUNT:
            parts.append("Accounts")
        elif self.view_mode == ViewMode.DETAIL:
            # Show all drill-down levels (can have multiple selections for sub-grouping)
            # Order: Merchant → Category → Group → Account
            has_any_selection = False

            if self.selected_merchant:
                parts.append("Merchants")
                parts.append(self.selected_merchant)
                has_any_selection = True

            if self.selected_category:
                if not has_any_selection:
                    parts.append("Categories")
                parts.append(self.selected_category)
                has_any_selection = True

            if self.selected_group:
                if not has_any_selection:
                    parts.append("Groups")
                parts.append(self.selected_group)
                has_any_selection = True

            if self.selected_account:
                if not has_any_selection:
                    parts.append("Accounts")
                parts.append(self.selected_account)
                has_any_selection = True

            if not has_any_selection:
                parts.append("All Transactions")

            # Add sub-grouping indicator if active
            if self.sub_grouping_mode:
                if self.sub_grouping_mode == ViewMode.CATEGORY:
                    parts.append("(by Category)")
                elif self.sub_grouping_mode == ViewMode.GROUP:
                    parts.append("(by Group)")
                elif self.sub_grouping_mode == ViewMode.ACCOUNT:
                    parts.append("(by Account)")
                elif self.sub_grouping_mode == ViewMode.MERCHANT:
                    parts.append("(by Merchant)")

        # Add time frame with actual dates
        if self.time_frame == TimeFrame.THIS_YEAR and self.start_date:
            parts.append(f"Year {self.start_date.year}")
        elif self.time_frame == TimeFrame.THIS_MONTH and self.start_date:
            month_name = self.start_date.strftime("%B")  # Full month name
            year = self.start_date.year
            parts.append(f"{month_name} {year}")
        elif self.time_frame == TimeFrame.CUSTOM and self.start_date and self.end_date:
            # Check if it's a single month
            if (
                self.start_date.year == self.end_date.year
                and self.start_date.month == self.end_date.month
            ):
                month_name = self.start_date.strftime("%B")
                parts.append(f"{month_name} {self.start_date.year}")
            else:
                parts.append(f"{self.start_date} to {self.end_date}")

        # Add search indicator if active
        if self.search_query:
            parts.append(f"Search: '{self.search_query}'")

        return " > ".join(parts) if parts else "Home"
