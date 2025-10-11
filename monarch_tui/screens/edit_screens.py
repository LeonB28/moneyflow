"""Edit screens for transaction modifications."""

from textual.app import ComposeResult
from textual.events import Key
from textual.screen import ModalScreen
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Button, Input, Label, Static, ListView, ListItem


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

    .merchant-button {
        width: 100%;
        text-align: left;
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

            yield Label("Type new merchant name (or select below):", classes="edit-label")
            yield Input(
                placeholder="Type merchant name...",
                value=self.current_merchant,
                id="merchant-input",
                classes="edit-input"
            )

            if self.all_merchants:
                yield Static(
                    f"{len(self.all_merchants)} existing merchants",
                    id="suggestions-count"
                )
                with VerticalScroll(id="suggestions"):
                    for merchant in sorted(set(self.all_merchants))[:20]:  # Show top 20
                        if merchant and merchant != self.current_merchant:
                            yield Button(
                                merchant,
                                variant="default",
                                id=f"merch-{hash(merchant)}",
                                classes="merchant-button"
                            )

            with Container(id="button-container"):
                yield Button("Save", variant="primary", id="save-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    async def on_mount(self) -> None:
        """Focus the input when screen loads."""
        self.query_one("#merchant-input", Input).focus()

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Filter merchant suggestions as user types."""
        if event.input.id != "merchant-input" or not self.all_merchants:
            return

        query = event.value.lower().strip()
        suggestions = self.query_one("#suggestions", VerticalScroll)
        count_widget = self.query_one("#suggestions-count", Static)

        # Clear current suggestions
        await suggestions.remove_children()

        # Filter merchants
        if query and query != self.current_merchant.lower():
            matches = [
                m for m in self.all_merchants
                if m and query in m.lower() and m != self.current_merchant
            ]
        else:
            matches = [m for m in self.all_merchants if m and m != self.current_merchant]

        # Update count
        count_widget.update(f"{len(matches)} matching merchants")

        # Show top 20 matches
        for merchant in sorted(set(matches))[:20]:
            await suggestions.mount(
                Button(
                    merchant,
                    variant="default",
                    id=f"merch-{hash(merchant)}",
                    classes="merchant-button"
                )
            )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            new_merchant = self.query_one("#merchant-input", Input).value.strip()
            if new_merchant and new_merchant != self.current_merchant:
                self.dismiss(new_merchant)
            else:
                self.dismiss(None)
        elif event.button.id and event.button.id.startswith("merch-"):
            # User clicked a suggestion
            new_merchant = event.control.label
            self.query_one("#merchant-input", Input).value = new_merchant
            self.dismiss(new_merchant)

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
    """Modal for selecting a category with type-to-search."""

    CSS = """
    SelectCategoryScreen {
        align: center middle;
    }

    #category-dialog {
        width: 70;
        height: auto;
        max-height: 40;
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

    #category-results {
        height: 20;
        border: solid $panel;
        margin: 1 0;
    }

    #results-count {
        color: $text-muted;
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
        self.filtered_categories = list(categories.items())

    def compose(self) -> ComposeResult:
        with Container(id="category-dialog"):
            yield Label("📋 Select Category (type to search)", id="category-title")

            yield Input(
                placeholder="Type to filter categories...",
                id="search-input"
            )

            yield Static(
                f"{len(self.categories)} categories",
                id="results-count"
            )

            with VerticalScroll(id="category-results"):
                for cat_id, cat_data in sorted(self.categories.items(), key=lambda x: x[1]["name"]):
                    cat_name = cat_data["name"]
                    is_current = " ← current" if cat_id == self.current_category_id else ""
                    yield Button(
                        f"{cat_name}{is_current}",
                        variant="default" if cat_id != self.current_category_id else "primary",
                        id=f"cat-{cat_id}",
                        classes="category-button"
                    )

            with Container(id="button-container"):
                yield Button("Cancel", variant="default", id="cancel-button")

    async def on_mount(self) -> None:
        """Focus search input on load."""
        self.query_one("#search-input", Input).focus()

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Filter categories as user types."""
        if event.input.id != "search-input":
            return

        query = event.value.lower().strip()
        results_container = self.query_one("#category-results", VerticalScroll)
        results_count = self.query_one("#results-count", Static)

        # Clear current results
        await results_container.remove_children()

        # Filter and show matching categories
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

        # Show filtered results
        for cat_id, cat_data in sorted(matches, key=lambda x: x[1]["name"]):
            cat_name = cat_data["name"]
            is_current = " ← current" if cat_id == self.current_category_id else ""
            await results_container.mount(
                Button(
                    f"{cat_name}{is_current}",
                    variant="default" if cat_id != self.current_category_id else "primary",
                    id=f"cat-{cat_id}",
                    classes="category-button"
                )
            )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id and event.button.id.startswith("cat-"):
            category_id = event.button.id[4:]  # Remove "cat-" prefix
            self.dismiss(category_id)

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
