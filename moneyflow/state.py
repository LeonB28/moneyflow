"""
App state management with change tracking and undo/redo support.

This module contains the central AppState class that holds all application state
including view mode, filters, selections, and pending edits. State should be data,
not operations - complex operations belong in separate service classes.
"""

from dataclasses import dataclass, field
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
    """Represents a pending transaction edit."""

    transaction_id: str
    field: str  # 'merchant', 'category', 'hide_from_reports'
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.now)


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
    categories: Dict[str, Any] = field(default_factory=dict)
    category_groups: Dict[str, Any] = field(default_factory=dict)
    merchants: Dict[str, Any] = field(default_factory=dict)

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

    # Multi-select for bulk operations
    selected_ids: set[str] = field(default_factory=set)

    # Search/filter
    search_query: str = ""
    show_transfers: bool = False  # Whether to show Transfer category transactions
    show_hidden: bool = True  # Whether to show transactions hidden from reports

    # Change tracking
    pending_edits: List[TransactionEdit] = field(default_factory=list)
    undo_stack: List[TransactionEdit] = field(default_factory=list)
    redo_stack: List[TransactionEdit] = field(default_factory=list)

    # UI state
    loading: bool = False
    error_message: Optional[str] = None
    status_message: Optional[str] = None

    # Current view data (for display)
    current_data: Optional[pl.DataFrame] = None

    # Navigation history for breadcrumb and back navigation
    # Stores (view_mode, cursor_position) for restoring state on go_back
    navigation_history: List[tuple[ViewMode, int]] = field(default_factory=list)

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

    def cycle_grouping(self) -> str:
        """
        Cycle through aggregation view modes.

        Order: MERCHANT → CATEGORY → GROUP → ACCOUNT → MERCHANT

        Only works in aggregation views, not DETAIL view.

        Returns:
            Name of the new view mode for notification
        """
        # Only cycle if in an aggregation view (not DETAIL)
        if self.view_mode == ViewMode.DETAIL:
            return ""

        # Clear any drill-down selections when switching views
        self.selected_merchant = None
        self.selected_category = None
        self.selected_group = None
        self.selected_account = None

        # Reset sort to valid field for aggregate views if needed
        if self.sort_by not in [SortMode.COUNT, SortMode.AMOUNT]:
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

        Returns:
            Tuple of (success: bool, cursor_position: int)
            success=True if went back, False if already at root
            cursor_position=Row to restore cursor to (0 if none saved)
        """
        if self.view_mode == ViewMode.DETAIL:
            # Clear drill-down selections
            self.selected_merchant = None
            self.selected_category = None
            self.selected_group = None
            self.selected_account = None

            # Pop from history if available
            cursor_position = 0
            if self.navigation_history:
                previous_view, cursor_position = self.navigation_history.pop()
                self.view_mode = previous_view
            else:
                # Default back to MERCHANT view
                self.view_mode = ViewMode.MERCHANT

            return True, cursor_position

        # Already at a top-level view
        return False, 0

    def save_view_state(self) -> dict:
        """Save current view state for later restoration."""
        return {
            "view_mode": self.view_mode,
            "selected_merchant": self.selected_merchant,
            "selected_category": self.selected_category,
            "selected_group": self.selected_group,
            "selected_account": self.selected_account,
        }

    def restore_view_state(self, saved_state: dict) -> None:
        """Restore previously saved view state."""
        self.view_mode = saved_state["view_mode"]
        self.selected_merchant = saved_state["selected_merchant"]
        self.selected_category = saved_state["selected_category"]
        self.selected_group = saved_state["selected_group"]
        self.selected_account = saved_state.get("selected_account")

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
            # Show what we drilled down from
            if self.selected_merchant:
                parts.append("Merchants")
                parts.append(self.selected_merchant)
            elif self.selected_category:
                parts.append("Categories")
                parts.append(self.selected_category)
            elif self.selected_group:
                parts.append("Groups")
                parts.append(self.selected_group)
            elif self.selected_account:
                parts.append("Accounts")
                parts.append(self.selected_account)
            else:
                parts.append("Transactions")

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
