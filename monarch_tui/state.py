"""
App state management with change tracking and undo/redo support.
"""
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Any, Optional, List, Dict
import polars as pl


class ViewMode(Enum):
    """Available view modes for transaction aggregation."""
    MERCHANT = "merchant"
    CATEGORY = "category"
    GROUP = "group"
    DETAIL = "detail"


class SortMode(Enum):
    """Sorting options for transactions."""
    AMOUNT_DESC = "amount_desc"
    AMOUNT_ASC = "amount_asc"
    DATE_DESC = "date_desc"
    DATE_ASC = "date_asc"
    COUNT_DESC = "count_desc"


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
    Central app state with undo/redo support.
    """
    # Data
    transactions_df: Optional[pl.DataFrame] = None
    categories: Dict[str, Any] = field(default_factory=dict)
    category_groups: Dict[str, Any] = field(default_factory=dict)
    merchants: Dict[str, Any] = field(default_factory=dict)

    # View state
    view_mode: ViewMode = ViewMode.MERCHANT
    sort_mode: SortMode = SortMode.COUNT_DESC
    time_frame: TimeFrame = TimeFrame.THIS_YEAR

    # Time filtering
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    # Navigation
    selected_merchant: Optional[str] = None
    selected_category: Optional[str] = None
    selected_group: Optional[str] = None
    selected_row: int = 0

    # Multi-select for bulk operations
    selected_ids: set[str] = field(default_factory=set)

    # Search/filter
    search_query: str = ""

    # Change tracking
    pending_edits: List[TransactionEdit] = field(default_factory=list)
    undo_stack: List[TransactionEdit] = field(default_factory=list)
    redo_stack: List[TransactionEdit] = field(default_factory=list)

    # UI state
    loading: bool = False
    error_message: Optional[str] = None
    status_message: Optional[str] = None

    def add_edit(self, transaction_id: str, field: str, old_value: Any, new_value: Any):
        """Add a pending edit to the change tracker."""
        edit = TransactionEdit(
            transaction_id=transaction_id,
            field=field,
            old_value=old_value,
            new_value=new_value
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

    def set_timeframe(self, timeframe: TimeFrame, start_date: Optional[date] = None, end_date: Optional[date] = None):
        """Set the time frame for filtering transactions."""
        self.time_frame = timeframe

        if timeframe == TimeFrame.CUSTOM:
            self.start_date = start_date
            self.end_date = end_date
        elif timeframe == TimeFrame.THIS_YEAR:
            today = date.today()
            self.start_date = date(today.year, 1, 1)
            self.end_date = date(today.year, 12, 31)
        elif timeframe == TimeFrame.THIS_MONTH:
            today = date.today()
            self.start_date = date(today.year, today.month, 1)
            # Last day of month
            if today.month == 12:
                self.end_date = date(today.year, 12, 31)
            else:
                next_month = date(today.year, today.month + 1, 1)
                from datetime import timedelta
                self.end_date = next_month - timedelta(days=1)
        else:  # ALL_TIME
            self.start_date = None
            self.end_date = None

    def toggle_sort(self):
        """Cycle through sort modes: COUNT -> DATE -> AMOUNT -> COUNT."""
        if self.sort_mode == SortMode.COUNT_DESC:
            self.sort_mode = SortMode.DATE_DESC
        elif self.sort_mode == SortMode.DATE_DESC:
            self.sort_mode = SortMode.AMOUNT_DESC
        else:
            self.sort_mode = SortMode.COUNT_DESC

    def get_filtered_df(self) -> Optional[pl.DataFrame]:
        """Get filtered DataFrame based on current state."""
        if self.transactions_df is None:
            return None

        df = self.transactions_df

        # Apply time filter
        if self.start_date and self.end_date:
            df = df.filter(
                (pl.col("date") >= self.start_date) &
                (pl.col("date") <= self.end_date)
            )

        # Apply search filter
        if self.search_query:
            query = self.search_query.lower()
            df = df.filter(
                pl.col("merchant").str.to_lowercase().str.contains(query) |
                pl.col("category").str.to_lowercase().str.contains(query)
            )

        # Apply view-specific filters
        if self.view_mode == ViewMode.DETAIL:
            if self.selected_merchant:
                df = df.filter(pl.col("merchant") == self.selected_merchant)
            elif self.selected_category:
                df = df.filter(pl.col("category") == self.selected_category)
            elif self.selected_group:
                df = df.filter(pl.col("group") == self.selected_group)

        return df
