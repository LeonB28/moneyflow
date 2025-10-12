"""Edit screens for transaction modifications."""

from textual.app import ComposeResult
from textual.events import Key
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Button, Input, Label, Static, OptionList
from textual.widgets.option_list import Option


class EditMerchantScreen(ModalScreen):
    """Modal for editing merchant name with suggestions."""

    CSS = """
    EditMerchantScreen {
        align: center middle;
    }

    #edit-dialog {
        width: 70;
        height: auto;
        max-height: 40;
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

    #suggestions {
        height: 15;
        border: solid $panel;
        margin: 1 0;
    }

    #suggestions-count {
        color: $text-muted;
        margin: 1 0;
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

    def __init__(self, current_merchant: str, transaction_count: int = 1, all_merchants: list = None):
        super().__init__()
        self.current_merchant = current_merchant
        self.transaction_count = transaction_count
        self.all_merchants = all_merchants or []

    def compose(self) -> ComposeResult:
        with Container(id="edit-dialog"):
            if self.transaction_count > 1:
                yield Label(
                    f"✏️  Edit Merchant ({self.transaction_count} transactions)",
                    id="edit-title"
                )
            else:
                yield Label("✏️  Edit Merchant", id="edit-title")

            yield Label("Current: " + self.current_merchant, classes="edit-label")

            yield Label("Type new name or ↓ to select existing:", classes="edit-label")
            yield Input(
                placeholder="Type merchant name...",
                value=self.current_merchant,
                id="merchant-input",
                classes="edit-input"
            )

            if self.all_merchants:
                yield Static(
                    "Existing merchants (↑↓ to navigate, Enter to select):",
                    id="suggestions-count"
                )
                yield OptionList(id="suggestions")

            with Container(id="button-container"):
                yield Button("Save", variant="primary", id="save-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    async def on_mount(self) -> None:
        """Initialize suggestions list."""
        if self.all_merchants:
            await self._update_suggestions("")
        self.query_one("#merchant-input", Input).focus()

    async def _update_suggestions(self, query: str) -> None:
        """Update merchant suggestions based on query."""
        option_list = self.query_one("#suggestions", OptionList)
        count_widget = self.query_one("#suggestions-count", Static)

        # Filter merchants
        if query and query != self.current_merchant.lower():
            matches = [
                m for m in self.all_merchants
                if m and query in m.lower() and m != self.current_merchant
            ]
        else:
            matches = [m for m in self.all_merchants if m and m != self.current_merchant]

        # Update count
        count_widget.update(f"{len(matches)} matching merchants (↑↓ to navigate, Enter to select)")

        # Clear and rebuild
        option_list.clear_options()

        # Show top 20 matches
        for merchant in sorted(set(matches))[:20]:
            option_list.add_option(Option(merchant, id=merchant))

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Filter merchant suggestions as user types."""
        if event.input.id != "merchant-input" or not self.all_merchants:
            return

        query = event.value.lower().strip()
        await self._update_suggestions(query)

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle merchant selection from suggestions."""
        if event.option.id:
            # Set input value and dismiss
            self.dismiss(str(event.option.id))

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
        """Handle Enter key in input - save the typed value."""
        new_merchant = event.value.strip()
        if new_merchant and new_merchant != self.current_merchant:
            self.dismiss(new_merchant)
        else:
            self.dismiss(None)

    def on_key(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "escape":
            self.dismiss(None)
        elif event.key == "down":
            # Move focus to suggestions list
            if self.all_merchants:
                self.query_one("#suggestions", OptionList).focus()


class SelectCategoryScreen(ModalScreen):
    """Modal for selecting a category with keyboard-driven type-to-search."""

    CSS = """
    SelectCategoryScreen {
        align: center middle;
    }

    #category-dialog {
        width: 70;
        height: auto;
        max-height: 35;
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

    #search-input {
        margin: 1 0;
    }

    #category-list {
        height: 20;
        border: solid $panel;
        margin: 1 0;
    }

    #results-count {
        color: $text-muted;
        margin: 1 0;
    }
    """

    def __init__(self, categories: dict, current_category_id: str = None):
        super().__init__()
        self.categories = categories
        self.current_category_id = current_category_id
        self.category_map = {}  # Maps option index to category ID

    def compose(self) -> ComposeResult:
        with Container(id="category-dialog"):
            yield Label("📋 Select Category (type to filter, ↑↓ navigate, Enter to select)", id="category-title")

            yield Input(
                placeholder="Type to filter categories...",
                id="search-input"
            )

            yield Static(
                f"{len(self.categories)} categories",
                id="results-count"
            )

            yield OptionList(id="category-list")

    async def on_mount(self) -> None:
        """Initialize category list."""
        await self._update_category_list("")
        # Focus search input so user can immediately start typing
        self.query_one("#search-input", Input).focus()

    async def _update_category_list(self, query: str) -> None:
        """Update the category list based on search query."""
        option_list = self.query_one("#category-list", OptionList)
        results_count = self.query_one("#results-count", Static)

        # Filter categories
        if query:
            matches = [
                (cat_id, cat_data)
                for cat_id, cat_data in self.categories.items()
                if query in cat_data["name"].lower()
            ]
        else:
            matches = list(self.categories.items())

        # Update count
        results_count.update(f"{len(matches)} categories")

        # Clear and rebuild list
        option_list.clear_options()
        self.category_map.clear()

        for idx, (cat_id, cat_data) in enumerate(sorted(matches, key=lambda x: x[1]["name"])):
            cat_name = cat_data["name"]
            is_current = " ← current" if cat_id == self.current_category_id else ""
            option_list.add_option(Option(f"{cat_name}{is_current}", id=cat_id))
            self.category_map[idx] = cat_id

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Filter categories as user types."""
        if event.input.id != "search-input":
            return

        query = event.value.lower().strip()
        await self._update_category_list(query)

    async def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle category selection with Enter key."""
        if event.option.id:
            self.dismiss(str(event.option.id))

    def on_key(self, event: Key) -> None:
        """Handle keyboard shortcuts."""
        if event.key == "escape":
            self.dismiss(None)
        elif event.key == "down":
            # Move focus from input to list
            self.query_one("#category-list", OptionList).focus()
        elif event.key == "slash":
            # Focus search input when user presses /
            self.query_one("#search-input", Input).focus()


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
