import sqlite3
import webbrowser
from pathlib import Path
from datetime import datetime
from textual.widgets import ListItem, Label
from textual.app import ComposeResult

def get_db_path(data_dir: str, tag: str, subtag: str) -> Path:
    target_dir = Path(data_dir) / tag
    target_dir.mkdir(parents=True, exist_ok=True)
    if subtag:
        # Create an empty directory for the subtag so the DirectoryTree displays it
        (target_dir / subtag).mkdir(exist_ok=True)
    db_name = f"youtube_{subtag}.db" if subtag else "youtube.db"
    return target_dir / db_name

def init_db(db_path: Path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_name TEXT,
            title TEXT,
            url TEXT,
            date TEXT,
            sort_date TEXT,
            is_read INTEGER DEFAULT 0,
            UNIQUE(url)
        )
    ''')
    conn.commit()
    conn.close()

def save_entry(entry: dict, feed_config, data_dir: str) -> bool:
    db_path = get_db_path(data_dir, feed_config.tag, feed_config.subtag)
    init_db(db_path)
    
    title = entry.get("title", "No Title")
    url = entry.get("link", "")
    
    dt = None
    if "published_parsed" in entry and entry.published_parsed:
        dt = datetime(*entry.published_parsed[:6])
    else:
        dt = datetime.now()
        
    formatted_date = dt.strftime("%d/%m/%Y %H:%M")
    sort_date = dt.strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Check if exists
    c.execute("SELECT id FROM entries WHERE url = ?", (url,))
    if c.fetchone():
        conn.close()
        return False
        
    c.execute('''
        INSERT INTO entries (feed_name, title, url, date, sort_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (feed_config.name, title, url, formatted_date, sort_date))
    
    conn.commit()
    conn.close()
    return True

class YoutubeArticleItem(ListItem):
    SOURCE_COLORS = [
        "#ff5555", "#50fa7b", "#f1fa8c", "#bd93f9", "#ff79c6",
        "#8be9fd", "#ffb86c", "#ff9580", "#9580ff", "#80ffea"
    ]

    def __init__(self, db_path: Path, entry_id: int, feed_name: str, title: str, url: str, date: str, is_read: bool, sort_date: str):
        super().__init__()
        self.db_path = db_path
        self.entry_id = entry_id
        self.feed_name = feed_name
        self.title = title
        self.url = url
        self.date = date
        self.is_read = is_read
        self.sort_date = sort_date
        
        color_idx = hash(self.feed_name) % len(self.SOURCE_COLORS)
        self.source_color = self.SOURCE_COLORS[color_idx]

    def compose(self) -> ComposeResult:
        yield Label(f"[{self.source_color}]{self.feed_name}[/]", id="source")
        yield Label(self.title, id="title", classes="read" if self.is_read else "unread")
        yield Label(self.date, id="date")

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.query_one("#title").add_class("read")
            self.query_one("#title").remove_class("unread")
            self.query_one("#source").add_class("read")
            self.query_one("#source").remove_class("unread")
            
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("UPDATE entries SET is_read = 1 WHERE id = ?", (self.entry_id,))
            conn.commit()
            conn.close()
            
    def on_select(self):
        # Open in browser
        webbrowser.open(self.url)

def load_articles(current_dir: Path, tag: str, subtag: str, limit: int = 50):
    if subtag:
        db_paths = [current_dir.parent / f"youtube_{subtag}.db"]
    else:
        db_paths = list(current_dir.glob("youtube_*.db"))
        
    items = []
    for db_path in db_paths:
        if not db_path.exists():
            continue
            
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        # Check if table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries'")
        if not c.fetchone():
            conn.close()
            continue
            
        c.execute("SELECT id, feed_name, title, url, date, is_read, sort_date FROM entries ORDER BY sort_date DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        
        for row in rows:
            item = YoutubeArticleItem(
                db_path=db_path,
                entry_id=row[0],
                feed_name=row[1],
                title=row[2],
                url=row[3],
                date=row[4],
                is_read=bool(row[5]),
                sort_date=row[6]
            )
            items.append((item, item.sort_date))
            
    # Sort combined results descending
    items.sort(key=lambda x: x[1], reverse=True)
    
    # Return up to limit items overall to prevent huge lists when combining tags
    return items[:limit]
