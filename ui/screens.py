from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.widgets import Input, Button, Label
from textual.containers import Horizontal, Vertical
from core.config import FeedConfig

class AddFeedScreen(ModalScreen):
    """Screen for adding a new feed."""
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Add New Feed", id="modal-title"),
            Input(placeholder="Feed Name", id="name"),
            Input(placeholder="RSS URL", id="url"),
            Input(placeholder="Tag", id="tag"),
            Input(placeholder="Subtag", id="subtag"),
            Horizontal(
                Button("Save", variant="success", id="save"),
                Button("Cancel", variant="error", id="cancel"),
                classes="buttons"
            ),
            id="dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            name = self.query_one("#name", Input).value
            url = self.query_one("#url", Input).value
            tag = self.query_one("#tag", Input).value
            subtag = self.query_one("#subtag", Input).value
            
            if name and url and tag:
                self.dismiss(FeedConfig(name, url, tag, subtag))
        else:
            self.dismiss(None)

from textual import on

class SearchScreen(ModalScreen):
    """Screen for searching articles."""
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Search Articles", id="modal-title"),
            Input(placeholder="Search query (e.g., 'python')", id="search_query"),
            Horizontal(
                Button("Search", variant="primary", id="do_search"),
                Button("Cancel", variant="error", id="cancel_search"),
                classes="buttons"
            ),
            id="dialog"
        )
    
    def on_mount(self) -> None:
        self.query_one("#search_query", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "do_search":
            query = self.query_one("#search_query", Input).value
            self.dismiss(query if query else None)
        elif event.button.id == "cancel_search":
            self.dismiss(None)

    @on(Input.Submitted, "#search_query")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value
        self.dismiss(query if query else None)
