"""Duplicates detection and review screen."""

from textual.app import ComposeResult
from textual.events import Key
from textual.screen import Screen
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Button, Label, Static, DataTable
import polars as pl


class DuplicatesScreen(Screen):
    """Screen to review and handle duplicate transactions."""

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

    def compose(self) -> ComposeResult:
        with Container(id="duplicates-container"):
            with Container(id="duplicates-header"):
                yield Label(
                    f"🔍 Found {len(self.duplicates_df)} potential duplicates "
                    f"in {len(self.duplicate_groups)} groups",
                    id="duplicates-title"
                )
                yield Static(
                    "Review transactions below. Duplicates are grouped together.",
                    id="duplicates-help"
                )

            yield DataTable(id="duplicates-table", cursor_type="row", zebra_stripes=True)

            with Container(id="duplicates-footer"):
                yield Static(
                    "[Enter] View details | [h] Hide from reports | [d] Delete | [Esc] Close",
                    classes="action-hint"
                )

    async def on_mount(self) -> None:
        """Populate the duplicates table."""
        table = self.query_one("#duplicates-table", DataTable)

        # Add columns
        table.add_column("Group", key="group", width=6)
        table.add_column("Date", key="date", width=12)
        table.add_column("Merchant", key="merchant", width=25)
        table.add_column("Amount", key="amount", width=12)
        table.add_column("Account", key="account", width=20)
        table.add_column("ID", key="id", width=15)

        # Add rows grouped by duplicate sets
        for group_num, group_ids in enumerate(self.duplicate_groups, 1):
            for txn_id in group_ids:
                # Find transaction in full dataframe
                txn_rows = self.full_df.filter(pl.col("id") == txn_id)
                if len(txn_rows) > 0:
                    txn = txn_rows.row(0, named=True)
                    table.add_row(
                        f"#{group_num}",
                        str(txn["date"]),
                        txn["merchant"],
                        f"${txn['amount']:,.2f}",
                        txn["account"],
                        txn_id[:12] + "..."
                    )

    def on_key(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "escape":
            self.dismiss()
