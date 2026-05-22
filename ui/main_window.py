from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DirectoryTree, Button, ContentSwitcher, ListView
from textual.containers import Horizontal, Container
from textual import work, on
from pathlib import Path
from slugify import slugify

from core.config import AppConfig, FeedConfig
from core.logic import update_all_feeds
from core.addon_manager import manager as addon_manager
from .widgets import FilteredDirectoryTree, ArticleItem, LoadMoreItem, FocusableMarkdown
from .screens import AddFeedScreen, SearchScreen

class FeedApp(App):
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("u", "update_feeds", "Update Feeds"),
        ("a", "add_feed", "Add Feed"),
        ("q", "quit", "Quit"),
        ("escape", "back", "Back"),
        ("/", "search", "Search"),
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
        self.search_query = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            yield FilteredDirectoryTree(self.config.data_dir, id="sidebar")
            with ContentSwitcher(id="content-area", initial="article-list"):
                yield ListView(id="article-list")
                yield FocusableMarkdown(id="article-reader")
        with Horizontal(id="footer-btns"):
            yield Button("Update Feeds", variant="primary", id="btn-update")
            yield Button("Add Feed", variant="default", id="btn-add")
            yield Button("Search", variant="default", id="btn-search")
        yield Footer()

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Called when a directory is selected in the Sidebar."""
        self.current_dir = event.path
        self.current_limit = 50
        self.search_query = None
        self.refresh_article_list()
        self.query_one("#content-area", ContentSwitcher).current = "article-list"

    def _search_dir(self, dir_path: Path, tag: str, subtag: str, query: str, slug_query: str):
        items = []
        addon = addon_manager.get_addon_for_tag(tag, subtag)
        if addon and hasattr(addon, 'search_articles'):
            items.extend(addon.search_articles(dir_path, query, limit=self.current_limit))
        else:
            for path in dir_path.glob("*.md"):
                name_lower = path.name.lower()
                if query in name_lower or slug_query in name_lower:
                    item = ArticleItem(path)
                    try:
                        date_part, time_part = item.date.split(" ")
                        day, month, year = date_part.split("/")
                        sort_key = f"{year}-{month}-{day} {time_part}"
                    except:
                        sort_key = item.date
                    items.append((item, sort_key))
        return items

    def refresh_article_list(self) -> None:
        """Reload the article list from the current directory."""
        list_view = self.query_one("#article-list", ListView)
        list_view.clear()
        
        items_with_dates = []
        has_more = False

        if getattr(self, "search_query", None):
            query = self.search_query.lower()
            slug_query = slugify(query).lower()
            data_dir_path = Path(self.config.data_dir).resolve()
            
            for tag_dir in data_dir_path.iterdir():
                if not tag_dir.is_dir(): continue
                items_with_dates.extend(self._search_dir(tag_dir, tag_dir.name, "", query, slug_query))
                for sub_dir in tag_dir.iterdir():
                    if sub_dir.is_dir():
                        items_with_dates.extend(self._search_dir(sub_dir, tag_dir.name, sub_dir.name, query, slug_query))
            
            items_with_dates.sort(key=lambda x: x[1], reverse=True)
            if len(items_with_dates) > self.current_limit:
                has_more = True
                items_with_dates = items_with_dates[:self.current_limit]
        else:
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
                self.query_one("#article-reader", FocusableMarkdown).update(content)
                self.query_one("#content-area", ContentSwitcher).current = "article-reader"
                self.query_one("#article-reader", FocusableMarkdown).focus()
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
        try:
            rel_path = self.current_dir.relative_to(Path(self.config.data_dir).resolve())
            parts = rel_path.parts
            tag = parts[0] if len(parts) > 0 else None
            subtag = parts[1] if len(parts) > 1 else None
        except ValueError:
            try:
                rel_path = self.current_dir.relative_to(Path(self.config.data_dir))
                parts = rel_path.parts
                tag = parts[0] if len(parts) > 0 else None
                subtag = parts[1] if len(parts) > 1 else None
            except ValueError:
                tag, subtag = None, None

        if tag:
            msg = f"Updating feeds in '{tag}{'/' + subtag if subtag else ''}'..."
        else:
            msg = "Updating all feeds..."
            
        self.notify(msg)
        
        try:
            new_count = await update_all_feeds(self.config, tag, subtag)
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

    def action_search(self) -> None:
        def check_query(query: str | None):
            if query:
                self.search_query = query
                self.current_limit = 50
                self.refresh_article_list()
                self.query_one("#content-area", ContentSwitcher).current = "article-list"
                self.query_one("#article-list").focus()

        self.push_screen(SearchScreen(), check_query)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-update":
            self.action_update_feeds()
        elif event.button.id == "btn-add":
            self.action_add_feed()
        elif event.button.id == "btn-search":
            self.action_search()
