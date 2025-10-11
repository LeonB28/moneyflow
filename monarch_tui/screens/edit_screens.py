"""Edit screens for transaction modifications."""

from textual.app import ComposeResult
from textual.events import Key
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Button, Input, Label, Static, ListView, ListItem


class EditMerchantScreen(ModalScreen):
    """Modal for editing merchant name."""

    CSS = """
    EditMerchantScreen {
        align: center middle;
    }

    #edit-dialog {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 2 4;
    }

    #edit-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .edit-label {
        margin-top: 1;
        color: $text;
    }

    .edit-input {
        margin-bottom: 1;
    }

    #button-container {
        layout: horizontal;
        width: 100%;
        align: center middle;
        margin-top: 1;
    }

    #button-container Button {
        margin: 0 1;
    }
    """

    def __init__(self, current_merchant: str, transaction_count: int = 1):
        super().__init__()
        self.current_merchant = current_merchant
        self.transaction_count = transaction_count

    def compose(self) -> ComposeResult:
        with Container(id="edit-dialog"):
            if self.transaction_count > 1:
                yield Label(
                    f"✏️  Edit Merchant ({self.transaction_count} transactions)",
                    id="edit-title"
                )
            else:
                yield Label("✏️  Edit Merchant", id="edit-title")

            yield Label("Current merchant:", classes="edit-label")
            yield Static(self.current_merchant, classes="edit-label")

            yield Label("New merchant name:", classes="edit-label")
            yield Input(
                placeholder="Enter new merchant name",
                value=self.current_merchant,
                id="merchant-input",
                classes="edit-input"
            )

            with Container(id="button-container"):
                yield Button("Save", variant="primary", id="save-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    async def on_mount(self) -> None:
        """Focus the input when screen loads."""
        self.query_one("#merchant-input", Input).focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            new_merchant = self.query_one("#merchant-input", Input).value.strip()
            if new_merchant and new_merchant != self.current_merchant:
                self.dismiss(new_merchant)
            else:
                self.dismiss(None)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        new_merchant = event.value.strip()
        if new_merchant and new_merchant != self.current_merchant:
            self.dismiss(new_merchant)
        else:
            self.dismiss(None)

    def on_key(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "escape":
            self.dismiss(None)


class SelectCategoryScreen(ModalScreen):
    """Modal for selecting a category."""

    CSS = """
    SelectCategoryScreen {
        align: center middle;
    }

    #category-dialog {
        width: 60;
        height: 30;
        border: thick $primary;
        background: $surface;
        padding: 2 4;
    }

    #category-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #category-list {
        height: 1fr;
        border: solid $panel;
        margin: 1 0;
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

    def __init__(self, categories: dict, current_category_id: str = None):
        super().__init__()
        self.categories = categories
        self.current_category_id = current_category_id
        self.selected_category_id = None

    def compose(self) -> ComposeResult:
        with Container(id="category-dialog"):
            yield Label("📋 Select Category", id="category-title")

            with VerticalScroll(id="category-list"):
                for cat_id, cat_data in sorted(
                    self.categories.items(),
                    key=lambda x: x[1]["name"]
                ):
                    cat_name = cat_data["name"]
                    is_current = " (current)" if cat_id == self.current_category_id else ""
                    yield ListItem(Label(f"{cat_name}{is_current}"), id=f"cat-{cat_id}")

            with Container(id="button-container"):
                yield Button("Cancel", variant="default", id="cancel-button")

    async def on_list_item_selected(self, event: ListView.ItemSelected) -> None:
        """Handle category selection."""
        # Extract category ID from item id
        item_id = str(event.item.id)
        if item_id.startswith("cat-"):
            category_id = item_id[4:]  # Remove "cat-" prefix
            self.dismiss(category_id)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-button":
            self.dismiss(None)

    def on_key(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "escape":
            self.dismiss(None)


class DeleteConfirmationScreen(ModalScreen):
    """Confirmation dialog for deleting transactions."""

    CSS = """
    DeleteConfirmationScreen {
        align: center middle;
    }

    #delete-dialog {
        width: 50;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 2 4;
    }

    #delete-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }

    #delete-message {
        text-align: center;
        color: $text;
        margin-bottom: 2;
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

    def __init__(self, transaction_count: int = 1):
        super().__init__()
        self.transaction_count = transaction_count

    def compose(self) -> ComposeResult:
        with Container(id="delete-dialog"):
            yield Label("⚠️  Delete Transaction?", id="delete-title")

            if self.transaction_count > 1:
                yield Static(
                    f"Are you sure you want to delete {self.transaction_count} transactions?\n"
                    "This action CANNOT be undone!",
                    id="delete-message"
                )
            else:
                yield Static(
                    "Are you sure you want to delete this transaction?\n"
                    "This action CANNOT be undone!",
                    id="delete-message"
                )

            with Container(id="button-container"):
                yield Button("Cancel", variant="primary", id="cancel-button")
                yield Button("Delete", variant="error", id="delete-button")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-button":
            self.dismiss(False)
        elif event.button.id == "delete-button":
            self.dismiss(True)

    def on_key(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "escape":
            self.dismiss(False)
