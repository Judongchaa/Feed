from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DirectoryTree, Markdown, Button, Static, Input, Label, ListView, ListItem, ContentSwitcher
from textual.containers import Horizontal, Vertical, Container
from textual.screen import ModalScreen
from textual import work, on
from pathlib import Path
import os
import yaml

from models import AppConfig, FeedConfig
from logic import update_all_feeds
from addon_manager import manager as addon_manager

class FilteredDirectoryTree(DirectoryTree):
    """A DirectoryTree that only shows directories."""
    def filter_paths(self, paths: list[Path]) -> list[Path]:
        return [path for path in paths if path.is_dir()]

from ui_components import ArticleItem, LoadMoreItem

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

class FeedApp(App):
    CSS = """
    $accent: #6272a4;
    $bg: #282a36;
    $surface: #282a36;
    $text: #f8f8f2;
    $text-muted: #6272a4;
    $selection-bg: #44475a;

    Screen {
        background: $bg;
        color: $text;
    }

    Header {
        background: transparent;
        color: $accent;
        text-style: bold;
        height: 1;
        padding: 0 1;
    }

    Footer {
        background: transparent;
        color: $text-muted;
    }

    #main-container {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 4fr;
        padding: 1 2;
    }

    #sidebar {
        border: none;
        height: 100%;
        background: transparent;
    }

    /* Customizing the DirectoryTree */
    DirectoryTree > .directory-tree--extension {
        display: none;
    }
    
    DirectoryTree > .directory-tree--folder {
        color: $accent;
    }

    DirectoryTree > .directory-tree--file {
        display: none;
    }

    #content-area {
        height: 100%;
        border-left: panel $selection-bg;
        padding-left: 2;
    }

    #article-list {
        width: 100%;
        height: 100%;
        background: transparent;
        scrollbar-gutter: stable;
    }

    ArticleItem {
        layout: horizontal;
        padding: 0 1;
        height: 1;
        background: transparent;
        border: none;
    }

    #title {
        width: 1fr;
    }

    #source {
        width: auto;
        color: $text;
    }

    #source.read {
        opacity: 0.5;
    }

    #dot {
        margin-right: 1;
        color: $accent;
    }

    #date {
        width: auto;
        color: $text-muted;
        margin-left: 2;
    }

    .unread {
        color: $text;
    }

    .read {
        color: $text-muted;
        opacity: 0.5;
    }

    /* 
       THE HIGHLIGHT (Arrow Navigation)
    */
    ArticleItem.--highlight {
        background: transparent;
    }

    ArticleItem.--highlight #title {
        text-style: bold;
    }

    ArticleItem.--highlight #dot {
        text-style: bold;
    }

    ArticleItem.--highlight #date {
        text-style: bold;
    }

    LoadMoreItem {
        layout: horizontal;
        padding: 0 1;
        height: 1;
        background: transparent;
        border: none;
        content-align: center middle;
    }

    LoadMoreItem.--highlight {
        background: $selection-bg;
    }

    .load-more-label {
        color: $accent;
        text-style: bold;
        width: 100%;
        content-align: center middle;
    }

    #article-reader {
        height: 100%;
        overflow-y: scroll;
        background: transparent;
    }

    #footer-btns {
        height: 1;
        dock: bottom;
        background: transparent;
        align: right middle;
        padding: 0 2;
    }

    #footer-btns Button {
        border: none;
        background: transparent;
        color: $text-muted;
        height: 1;
        min-width: 12;
        padding: 0 1;
        margin: 0;
    }

    #footer-btns Button:hover {
        color: $text;
        text-style: bold;
    }

    AddFeedScreen {
        align: center middle;
        background: rgba(0,0,0,0.5);
    }

    #dialog {
        width: 50;
        height: auto;
        border: none;
        background: $selection-bg;
        padding: 1 2;
    }

    #modal-title {
        width: 100%;
        content-align: center middle;
        margin-bottom: 1;
        color: $accent;
        text-style: bold;
    }

    #dialog Input {
        margin-bottom: 1;
        border: none;
        background: $bg;
        color: $text;
    }

    .buttons {
        align: right middle;
        width: 100%;
        margin-top: 1;
    }
    
    .buttons Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        ("u", "update_feeds", "Update Feeds"),
        ("a", "add_feed", "Add Feed"),
        ("q", "quit", "Quit"),
        ("escape", "back", "Back"),
        ("left", "focus_sidebar", "Focus Sidebar"),
        ("right", "focus_content", "Focus Content"),
        ("+", "load_more", "Load More"),
    ]

    def action_focus_sidebar(self) -> None:
        """Focus the directory tree on the left."""
        self.query_one("#sidebar").focus()

    def action_focus_content(self) -> None:
        """Focus the active content widget on the right."""
        switcher = self.query_one("#content-area", ContentSwitcher)
        if switcher.current == "article-list":
            self.query_one("#article-list").focus()
        else:
            self.query_one("#article-reader").focus()

    def action_load_more(self) -> None:
        """Load more articles when pressing +."""
        switcher = self.query_one("#content-area", ContentSwitcher)
        if switcher.current == "article-list":
            self.current_limit += 50
            list_view = self.query_one("#article-list", ListView)
            idx = list_view.index
            self.refresh_article_list()
            list_view.index = idx

    def __init__(self):
        super().__init__()
        self.config = AppConfig.load()
        Path(self.config.data_dir).mkdir(parents=True, exist_ok=True)
        self.current_dir = Path(self.config.data_dir)
        self.current_limit = 50

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            yield FilteredDirectoryTree(self.config.data_dir, id="sidebar")
            with ContentSwitcher(id="content-area", initial="article-list"):
                yield ListView(id="article-list")
                yield Markdown(id="article-reader")
        with Horizontal(id="footer-btns"):
            yield Button("Update Feeds", variant="primary", id="btn-update")
            yield Button("Add Feed", variant="default", id="btn-add")
        yield Footer()

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Called when a directory is selected in the Sidebar."""
        self.current_dir = event.path
        self.current_limit = 50
        self.refresh_article_list()
        self.query_one("#content-area", ContentSwitcher).current = "article-list"

    def refresh_article_list(self) -> None:
        """Reload the article list from the current directory."""
        list_view = self.query_one("#article-list", ListView)
        list_view.clear()
        
        try:
            rel_path = self.current_dir.relative_to(Path(self.config.data_dir).resolve())
            parts = rel_path.parts
            tag = parts[0] if len(parts) > 0 else ""
            subtag = parts[1] if len(parts) > 1 else ""
        except ValueError:
            try:
                rel_path = self.current_dir.relative_to(Path(self.config.data_dir))
                parts = rel_path.parts
                tag = parts[0] if len(parts) > 0 else ""
                subtag = parts[1] if len(parts) > 1 else ""
            except ValueError:
                tag, subtag = "", ""

        addon = addon_manager.get_addon_for_tag(tag, subtag)
        if addon and hasattr(addon, 'load_articles'):
            # Pass limit to the addon
            items_with_dates = addon.load_articles(self.current_dir, tag, subtag, limit=self.current_limit)
            has_more = len(items_with_dates) == self.current_limit
        else:
            md_files = list(self.current_dir.glob("*.md"))
            # Sort files by name descending to get the newest first (since names start with YYYY-MM-DD)
            md_files.sort(key=lambda p: p.name, reverse=True)
            
            has_more = len(md_files) > self.current_limit
            # Limit items
            md_files = md_files[:self.current_limit]
            
            items_with_dates = []
            
            for path in md_files:
                item = ArticleItem(path)
                # Parse DD/MM/YYYY HH:mm for sorting
                sort_key = ""
                try:
                    # Expecting "DD/MM/YYYY HH:mm"
                    date_part, time_part = item.date.split(" ")
                    day, month, year = date_part.split("/")
                    sort_key = f"{year}-{month}-{day} {time_part}"
                except:
                    sort_key = item.date
                items_with_dates.append((item, sort_key))

        # Sort descending by date string
        items_with_dates.sort(key=lambda x: x[1], reverse=True)
        
        for item, _ in items_with_dates:
            list_view.append(item)
            
        if has_more:
            list_view.append(LoadMoreItem())

    @on(ListView.Selected)
    def on_article_selected(self, event: ListView.Selected) -> None:
        """Called when an article is selected from the list."""
        if isinstance(event.item, LoadMoreItem):
            self.current_limit += 50
            # Save current scroll index so we can restore focus/scroll
            list_view = self.query_one("#article-list", ListView)
            idx = list_view.index
            self.refresh_article_list()
            # Textual will reset index on clear(), so we manually set it to where the "Load more" button was
            list_view.index = idx
            return

        if hasattr(event.item, 'on_select'):
            event.item.mark_as_read()
            event.item.on_select()
        elif isinstance(event.item, ArticleItem):
            try:
                event.item.mark_as_read()
                with open(event.item.path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.query_one("#article-reader", Markdown).update(content)
                self.query_one("#content-area", ContentSwitcher).current = "article-reader"
            except Exception as e:
                self.notify(f"Error reading file: {e}", severity="error")

    def action_back(self) -> None:
        """Navigate back to the article list when pressing Escape."""
        switcher = self.query_one("#content-area", ContentSwitcher)
        if switcher.current == "article-reader":
            switcher.current = "article-list"
            self.query_one("#article-list", ListView).focus()

    @work(exclusive=True)
    async def action_update_feeds(self) -> None:
        self.notify("Updating feeds...")
        try:
            new_count = await update_all_feeds(self.config)
            self.notify(f"Update complete! {new_count} new entries.", severity="information")
            self.query_one("#sidebar", FilteredDirectoryTree).reload()
            self.refresh_article_list()
        except Exception as e:
            self.notify(f"Update failed: {e}", severity="error")

    def action_add_feed(self) -> None:
        def check_feed(feed: FeedConfig | None):
            if feed:
                self.config.feeds.append(feed)
                self.config.save()
                self.notify(f"Added feed: {feed.name}")
                self.action_update_feeds()

        self.push_screen(AddFeedScreen(), check_feed)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-update":
            self.action_update_feeds()
        elif event.button.id == "btn-add":
            self.action_add_feed()

if __name__ == "__main__":
    app = FeedApp()
    app.run()
