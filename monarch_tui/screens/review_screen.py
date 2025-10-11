"""Review pending changes before committing."""

from textual.app import ComposeResult
from textual.events import Key
from textual.screen import Screen
from textual.containers import Container
from textual.widgets import Button, Label, Static, DataTable


class ReviewChangesScreen(Screen):
    """Screen to review pending changes before committing to API."""

    CSS = """
    ReviewChangesScreen {
        background: $surface;
    }

    #review-container {
        height: 100%;
        padding: 1 2;
    }

    #review-header {
        height: 4;
        background: $panel;
        padding: 1;
        margin-bottom: 1;
    }

    #review-title {
        text-style: bold;
        color: $accent;
    }

    #review-help {
        color: $text-muted;
        margin-top: 1;
    }

    #changes-table {
        height: 1fr;
        border: solid $accent;
    }

    #review-footer {
        height: 3;
        background: $panel;
        padding: 1;
        dock: bottom;
    }

    .action-hint {
        color: $text-muted;
    }

    #button-container {
        layout: horizontal;
        width: 100%;
        align: center middle;
    }

    #button-container Button {
        margin: 0 1;
    }
    """

    def __init__(self, pending_edits: list):
        super().__init__()
        self.pending_edits = pending_edits

    def compose(self) -> ComposeResult:
        with Container(id="review-container"):
            with Container(id="review-header"):
                yield Label(
                    f"📝 Review {len(self.pending_edits)} Pending Change(s)",
                    id="review-title"
                )
                yield Static(
                    "Review changes below, then press C to commit or Esc to cancel",
                    id="review-help"
                )

            yield DataTable(id="changes-table", cursor_type="row", zebra_stripes=True)

            with Container(id="review-footer"):
                with Container(id="button-container"):
                    yield Button("Commit (C)", variant="primary", id="commit-button")
                    yield Button("Cancel (Esc)", variant="default", id="cancel-button")

    async def on_mount(self) -> None:
        """Populate the changes table."""
        table = self.query_one("#changes-table", DataTable)

        # Add columns
        table.add_column("Type", key="type", width=12)
        table.add_column("Transaction", key="transaction", width=15)
        table.add_column("Field", key="field", width=15)
        table.add_column("Old Value", key="old", width=25)
        table.add_column("New Value", key="new", width=25)

        # Add rows for each pending edit
        for edit in self.pending_edits:
            edit_type = "Merchant" if edit.field == "merchant" else "Category" if edit.field == "category" else "Hide"
            txn_id_short = edit.transaction_id[:12] + "..."

            old_val = str(edit.old_value)[:24]
            new_val = str(edit.new_value)[:24]

            table.add_row(
                edit_type,
                txn_id_short,
                edit.field,
                old_val,
                new_val
            )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "commit-button":
            self.dismiss(True)  # Confirm commit
        elif event.button.id == "cancel-button":
            self.dismiss(False)  # Cancel

    def on_key(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "escape":
            self.dismiss(False)  # Cancel
        elif event.key == "c":
            self.dismiss(True)  # Commit
