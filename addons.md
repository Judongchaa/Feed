# Addon System Developer Guide

This application supports an addon system that allows developers to customize how RSS feeds with specific tags are stored and viewed within the Textual UI. 

By default, the app saves feed entries as individual Markdown files and opens them using an internal Markdown reader. The addon system allows you to intercept these behaviors.

## 1. Registering an Addon

Addons are enabled and assigned to specific tags via the `addon_config.yml` file located in the root directory.

```yaml
addons:
  my_addon_name:
    enabled: true
    tags: 
      - "CustomTag1"
      - "CustomTag2"
```

## 2. Creating an Addon Module

Create a Python script named after your addon inside the `addons/` directory. For example, `addons/my_addon_name.py`.

The module can implement two main hooks:

### Hook 1: `save_entry`
Called when fetching and saving new RSS entries. If your addon is registered for a feed's tag, it will handle the saving process.

```python
from pathlib import Path

def save_entry(entry: dict, feed_config, data_dir: str) -> bool:
    """
    Called to save a new feed entry.
    
    Args:
        entry (dict): The parsed feed entry from feedparser.
        feed_config (models.FeedConfig): The configuration of the feed being processed.
        data_dir (str): The root directory where data should be stored.
        
    Returns:
        bool: True if the entry was saved successfully (or already exists), False otherwise.
    """
    # Implement custom saving logic here (e.g., save to SQLite, JSON, API)
    # The default app expects data to be under: Path(data_dir) / feed_config.tag
    
    return True
```

### Hook 2: `load_articles`
Called by the Textual app when the user selects a folder in the sidebar matching the addon's registered tag.

```python
from pathlib import Path
from textual.widgets import ListItem, Label
from textual.app import ComposeResult

def load_articles(current_dir: Path, tag: str, subtag: str, limit: int = 50):
    """
    Called to load articles for display in the ListView.
    
    Args:
        current_dir (Path): The directory selected in the sidebar.
        tag (str): The main tag of the selected directory.
        subtag (str): The subtag, if the user clicked a sub-directory. 
                      Empty string ("") if the user clicked the main tag folder.
        limit (int): The maximum number of articles to return (defaults to 50).
                      
    Returns:
        list: A list of tuples, where each tuple is (CustomArticleItem, sort_key).
              sort_key should be a string used for descending sorting (e.g., "YYYY-MM-DD HH:MM:SS").
    """
    items = []
    # 1. Read your custom storage format
    # 2. Instantiate your custom ListItem classes
    # 3. Append (item_instance, sort_key) to the list
    return items
```

## 3. Creating Custom UI Items

To display your articles in the list, you should define a custom class inheriting from `textual.widgets.ListItem`. This allows you to define exactly how your article looks and what happens when it is clicked.

```python
import webbrowser
from textual.widgets import ListItem, Label
from textual.app import ComposeResult

class MyCustomArticleItem(ListItem):
    def __init__(self, title: str, url: str, is_read: bool):
        super().__init__()
        self.title = title
        self.url = url
        self.is_read = is_read

    def compose(self) -> ComposeResult:
        # Define the UI layout for the list item
        # Use classes like "read" or "unread" which are defined in the app's CSS
        yield Label("●", id="dot", classes="read" if self.is_read else "unread")
        yield Label(self.title, id="title", classes="read" if self.is_read else "unread")

    def mark_as_read(self):
        """Called by the app to visually and persistently mark the item as read."""
        if not self.is_read:
            self.is_read = True
            self.query_one("#dot").add_class("read").remove_class("unread")
            self.query_one("#title").add_class("read").remove_class("unread")
            
            # TODO: Update your custom storage (e.g., SQLite UPDATE) to persist this state

    def on_select(self):
        """
        Optional hook. Called when the user clicks the item in the list.
        If implemented, the app will execute this INSTEAD of trying to open a Markdown preview.
        """
        # Example: Open a browser link directly
        webbrowser.open(self.url)
```

## Summary Checklist for Addons
1. Add to `addon_config.yml`.
2. Create `addons/<name>.py`.
3. Implement `save_entry` (for custom storage).
4. Implement `load_articles` (to feed the UI).
5. Implement a custom `ListItem` subclass with an `on_select` hook (for custom interaction).
