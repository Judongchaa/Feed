from pathlib import Path
import yaml
from textual.widgets import ListItem, Label
from textual.app import ComposeResult

class LoadMoreItem(ListItem):
    """An item to load more articles."""
    def compose(self) -> ComposeResult:
        yield Label("Load more...", classes="load-more-label")

class ArticleItem(ListItem):
    """An item in the article list."""
    SOURCE_COLORS = [
        "#ff5555", "#50fa7b", "#f1fa8c", "#bd93f9", "#ff79c6",
        "#8be9fd", "#ffb86c", "#ff9580", "#9580ff", "#80ffea"
    ]

    def __init__(self, path: Path):
        super().__init__()
        self.path = path
        self.title = path.stem.replace("_", " ").title()
        self.date = ""
        self.feed_name = ""
        self.is_read = False
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                if content.startswith("---"):
                    parts = content.split("---")
                    if len(parts) >= 3:
                        meta = yaml.safe_load(parts[1])
                        self.title = meta.get("title", self.title)
                        self.date = meta.get("date", "")
                        self.feed_name = meta.get("feed", "Unknown")
                        self.is_read = meta.get("read", False)
        except:
            pass
        
        # Determine source color based on feed name hash
        color_idx = hash(self.feed_name) % len(self.SOURCE_COLORS)
        self.source_color = self.SOURCE_COLORS[color_idx]

    def compose(self) -> ComposeResult:
        yield Label("●", id="dot", classes="read" if self.is_read else "unread")
        yield Label(f"[{self.source_color}]{self.feed_name}[/] - ", id="source")
        yield Label(self.title, id="title", classes="read" if self.is_read else "unread")
        yield Label(self.date, id="date")

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.query_one("#dot").add_class("read")
            self.query_one("#dot").remove_class("unread")
            self.query_one("#title").add_class("read")
            self.query_one("#title").remove_class("unread")
            self.query_one("#source").add_class("read")
            
            # Update the file
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    content = f.read()
                if content.startswith("---"):
                    parts = content.split("---")
                    meta = yaml.safe_load(parts[1])
                    meta["read"] = True
                    new_content = "---\n" + yaml.safe_dump(meta) + "---\n" + "---".join(parts[2:])
                    with open(self.path, "w", encoding="utf-8") as f:
                        f.write(new_content)
            except:
                pass
