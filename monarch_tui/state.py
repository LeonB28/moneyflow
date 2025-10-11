"""Application state management."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
import polars as pl


class ViewMode(Enum):
    """Current view mode."""
    MERCHANTS = "merchants"
    CATEGORIES = "categories"
    GROUPS = "groups"
    TRANSACTIONS = "transactions"


class SortMode(Enum):
    """Sort order for aggregations."""
    COUNT = "count"
    AMOUNT = "amount"
    NAME = "name"


@dataclass
class AppState:
    """
    Central application state.

    This tracks the current view, filters, selections, etc.
    """

    # Current view
    view_mode: ViewMode = ViewMode.MERCHANTS
    sort_mode: SortMode = SortMode.COUNT

    # Current drill-down context
    selected_merchant: Optional[str] = None
    selected_category: Optional[str] = None
    selected_group: Optional[str] = None

    # Time range filter
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    # Search/filter
    search_query: str = ""

    # Multi-selection for bulk operations
    selected_rows: List[int] = field(default_factory=list)

    # Data cache
    current_data: Optional[pl.DataFrame] = None
    current_row_index: int = 0

    def toggle_sort(self) -> None:
        """Toggle between count and amount sorting."""
        if self.sort_mode == SortMode.COUNT:
            self.sort_mode = SortMode.AMOUNT
        else:
            self.sort_mode = SortMode.COUNT

    def reset_selection(self) -> None:
        """Clear multi-selection."""
        self.selected_rows.clear()

    def toggle_row_selection(self, row_index: int) -> None:
        """Toggle selection of a row."""
        if row_index in self.selected_rows:
            self.selected_rows.remove(row_index)
        else:
            self.selected_rows.append(row_index)

    def is_row_selected(self, row_index: int) -> bool:
        """Check if a row is selected."""
        return row_index in self.selected_rows

    def drill_down(self, item_name: str) -> None:
        """Drill down into an item based on current view."""
        if self.view_mode == ViewMode.MERCHANTS:
            self.selected_merchant = item_name
            self.view_mode = ViewMode.TRANSACTIONS
        elif self.view_mode == ViewMode.CATEGORIES:
            self.selected_category = item_name
            self.view_mode = ViewMode.TRANSACTIONS
        elif self.view_mode == ViewMode.GROUPS:
            self.selected_group = item_name
            self.view_mode = ViewMode.TRANSACTIONS

        self.current_row_index = 0
        self.reset_selection()

    def go_back(self) -> bool:
        """
        Go back to previous view.

        Returns:
            True if went back, False if already at top level
        """
        if self.view_mode == ViewMode.TRANSACTIONS:
            # Determine which aggregation view to return to
            if self.selected_merchant:
                self.view_mode = ViewMode.MERCHANTS
                self.selected_merchant = None
            elif self.selected_category:
                self.view_mode = ViewMode.CATEGORIES
                self.selected_category = None
            elif self.selected_group:
                self.view_mode = ViewMode.GROUPS
                self.selected_group = None
            else:
                # Default to merchants
                self.view_mode = ViewMode.MERCHANTS

            self.current_row_index = 0
            self.reset_selection()
            return True

        return False

    def get_breadcrumb(self) -> str:
        """Get breadcrumb trail for current state."""
        parts = []

        if self.view_mode == ViewMode.MERCHANTS:
            parts.append("Merchants")
        elif self.view_mode == ViewMode.CATEGORIES:
            parts.append("Categories")
        elif self.view_mode == ViewMode.GROUPS:
            parts.append("Groups")
        elif self.view_mode == ViewMode.TRANSACTIONS:
            if self.selected_merchant:
                parts.append(f"Merchants > {self.selected_merchant}")
            elif self.selected_category:
                parts.append(f"Categories > {self.selected_category}")
            elif self.selected_group:
                parts.append(f"Groups > {self.selected_group}")
            else:
                parts.append("Transactions")

        return " | ".join(parts)
