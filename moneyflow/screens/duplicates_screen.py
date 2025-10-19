"""Duplicates detection and review screen."""

from typing import Optional, Set

import polars as pl
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import DataTable, Label, Static

from .edit_screens import DeleteConfirmationScreen
from .transaction_detail_screen import TransactionDetailScreen


class DuplicatesScreen(Screen):
    """Screen to review and handle duplicate transactions."""

    BINDINGS = [
        Binding("i", "show_details", "Details", show=True, key_display="i"),
        Binding("d", "delete_transaction", "Delete", show=True, key_display="d"),
        Binding("h", "toggle_hide", "Hide/Unhide", show=True, key_display="h"),
        Binding("space", "toggle_select", "Select", show=True, key_display="Space"),
        Binding("escape", "close", "Close", show=True, key_display="Esc"),
    ]

    CSS = """
    DuplicatesScreen {
        background: $surface;
    }

    #duplicates-container {
        height: 100%;
        padding: 1 2;
    }

    #duplicates-header {
        height: 3;
        background: $panel;
        padding: 1;
        margin-bottom: 1;
    }

    #duplicates-title {
        text-style: bold;
        color: $warning;
    }

    #duplicates-help {
        color: $text-muted;
        margin-top: 1;
    }

    #duplicates-table {
        height: 1fr;
        border: solid $warning;
    }

    #duplicates-footer {
        height: 3;
        background: $panel;
        padding: 1;
        dock: bottom;
    }

    .action-hint {
        color: $text-muted;
    }
    """

    def __init__(self, duplicates_df: pl.DataFrame, groups: list, full_df: pl.DataFrame):
        super().__init__()
        self.duplicates_df = duplicates_df
        self.duplicate_groups = groups
        self.full_df = full_df
        # Map table row index to transaction ID for lookups
        self.row_to_txn_id: dict[int, str] = {}
        # Track selected transaction IDs
        self.selected_ids: Set[str] = set()
        # Track which transactions have pending changes
        self.pending_deletes: Set[str] = set()
        self.pending_hides: Set[str] = set()

    def compose(self) -> ComposeResult:
        with Container(id="duplicates-container"):
            with Container(id="duplicates-header"):
                yield Label(
                    f"🔍 Found {len(self.duplicates_df)} potential duplicates "
                    f"in {len(self.duplicate_groups)} groups",
                    id="duplicates-title",
                )
                yield Static(
                    "Space=Select | Enter=Details | d=Delete | h=Hide | Esc=Close",
                    id="duplicates-help",
                )

            yield DataTable(id="duplicates-table", cursor_type="row", zebra_stripes=True)

            with Container(id="duplicates-footer"):
                yield Static("", id="status-line", classes="action-hint")

    async def on_mount(self) -> None:
        """Populate the duplicates table."""
        table = self.query_one("#duplicates-table", DataTable)

        # Add columns
        table.add_column("", key="flags", width=3)  # For selection/status flags
        table.add_column("Group", key="group", width=6)
        table.add_column("Date", key="date", width=12)
        table.add_column("Merchant", key="merchant", width=25)
        table.add_column("Amount", key="amount", width=12)
        table.add_column("Account", key="account", width=20)

        # Add rows grouped by duplicate sets
        row_idx = 0
        for group_num, group_ids in enumerate(self.duplicate_groups, 1):
            for txn_id in group_ids:
                # Find transaction in full dataframe
                txn_rows = self.full_df.filter(pl.col("id") == txn_id)
                if len(txn_rows) > 0:
                    txn = txn_rows.row(0, named=True)

                    # Build flags string
                    flags = ""
                    if txn.get("hideFromReports", False):
                        flags += "H"

                    table.add_row(
                        flags,
                        f"#{group_num}",
                        str(txn["date"]),
                        txn["merchant"],
                        f"${txn['amount']:,.2f}",
                        txn["account"],
                    )

                    # Store mapping
                    self.row_to_txn_id[row_idx] = txn_id
                    row_idx += 1

        self.update_status_line()

    def update_status_line(self) -> None:
        """Update the status line with current selection/pending changes."""
        status_parts = []

        if len(self.selected_ids) > 0:
            status_parts.append(f"✓ {len(self.selected_ids)} selected")

        if len(self.pending_deletes) > 0:
            status_parts.append(f"🗑 {len(self.pending_deletes)} to delete")

        if len(self.pending_hides) > 0:
            status_parts.append(f"👁 {len(self.pending_hides)} to hide/unhide")

        status_line = self.query_one("#status-line", Static)
        if status_parts:
            status_line.update(" | ".join(status_parts))
        else:
            status_line.update(
                "↑/↓=Navigate | Space=Select | Enter=Details | d=Delete | h=Hide | Esc=Close"
            )

    def get_current_transaction_id(self) -> Optional[str]:
        """Get the transaction ID of the currently selected row."""
        table = self.query_one("#duplicates-table", DataTable)
        if table.cursor_row < 0:
            return None
        return self.row_to_txn_id.get(table.cursor_row)

    def get_current_transaction_data(self) -> Optional[dict]:
        """Get the full transaction data for the current row."""
        txn_id = self.get_current_transaction_id()
        if not txn_id:
            return None

        txn_rows = self.full_df.filter(pl.col("id") == txn_id)
        if len(txn_rows) > 0:
            return dict(txn_rows.row(0, named=True))
        return None

    def refresh_table(self) -> None:
        """Refresh the table to show updated flags."""
        table = self.query_one("#duplicates-table", DataTable)
        saved_cursor = table.cursor_row

        # Update each row's flags
        for row_idx, txn_id in self.row_to_txn_id.items():
            txn_rows = self.full_df.filter(pl.col("id") == txn_id)
            if len(txn_rows) > 0:
                txn = txn_rows.row(0, named=True)

                # Build flags string
                flags = ""
                if txn_id in self.selected_ids:
                    flags += "✓"
                if txn.get("hideFromReports", False) or txn_id in self.pending_hides:
                    flags += "H"
                if txn_id in self.pending_deletes:
                    flags += "D"

                # Update the row
                table.update_cell_at((row_idx, 0), flags)

        # Restore cursor
        if saved_cursor >= 0 and saved_cursor < table.row_count:
            table.move_cursor(row=saved_cursor)

    def action_toggle_select(self) -> None:
        """Toggle selection of current transaction."""
        txn_id = self.get_current_transaction_id()
        if not txn_id:
            return

        if txn_id in self.selected_ids:
            self.selected_ids.remove(txn_id)
        else:
            self.selected_ids.add(txn_id)

        self.refresh_table()
        self.update_status_line()

    def action_show_details(self) -> None:
        """Show transaction details modal."""
        txn_data = self.get_current_transaction_data()
        if not txn_data:
            return

        self.app.push_screen(TransactionDetailScreen(txn_data))

    async def action_delete_transaction(self) -> None:
        """Delete the current transaction(s) with confirmation."""
        # Get transactions to delete
        if len(self.selected_ids) > 0:
            to_delete = list(self.selected_ids)
        else:
            txn_id = self.get_current_transaction_id()
            if not txn_id:
                return
            to_delete = [txn_id]

        # Show confirmation
        confirmed = await self.push_screen(
            DeleteConfirmationScreen(transaction_count=len(to_delete)), wait_for_dismiss=True
        )

        if confirmed:
            # Mark for deletion (would be committed by main app)
            for txn_id in to_delete:
                self.pending_deletes.add(txn_id)

            self.selected_ids.clear()
            self.refresh_table()
            self.update_status_line()

            self.notify(
                f"Marked {len(to_delete)} transaction(s) for deletion. "
                "Note: Deletes are not yet committed to API.",
                severity="warning",
                timeout=5,
            )

    def action_toggle_hide(self) -> None:
        """Toggle hide from reports for current transaction(s)."""
        # Get transactions to toggle
        if len(self.selected_ids) > 0:
            to_toggle = list(self.selected_ids)
        else:
            txn_id = self.get_current_transaction_id()
            if not txn_id:
                return
            to_toggle = [txn_id]

        # Toggle hide status
        for txn_id in to_toggle:
            if txn_id in self.pending_hides:
                self.pending_hides.remove(txn_id)
            else:
                self.pending_hides.add(txn_id)

        self.selected_ids.clear()
        self.refresh_table()
        self.update_status_line()

        self.notify(
            f"Toggled hide status for {len(to_toggle)} transaction(s). "
            "Note: Changes are not yet committed to API.",
            severity="warning",
            timeout=3,
        )

    def action_close(self) -> None:
        """Close the duplicates screen."""
        # Return the pending changes to the main app
        result = {
            "pending_deletes": list(self.pending_deletes),
            "pending_hides": list(self.pending_hides),
        }
        self.dismiss(result)

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key) - show details."""
        event.stop()  # Prevent main app's handler from running
        self.action_show_details()  # Not async, don't await
