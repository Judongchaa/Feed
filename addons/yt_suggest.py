import sqlite3
import webbrowser
from pathlib import Path
from datetime import datetime
from textual.widgets import ListItem, Label
from textual.app import ComposeResult
import yt_dlp
import logging
logger = logging.getLogger("yt_suggest")

def _setup_logger():
    if not getattr(logger, "setup_done", False):
        from core.addon_manager import manager
        addon_config = manager.addons_config.get("yt_suggest", {})
        if addon_config.get("logging", False):
            logger.setLevel(logging.INFO)
            fh = logging.FileHandler(manager.addons_dir / "yt_suggest.log")
            fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(fh)
        else:
            logger.addHandler(logging.NullHandler())
        logger.setup_done = True

def get_db_path(data_dir: str, tag: str, subtag: str) -> Path:
    target_dir = Path(data_dir) / tag
    target_dir.mkdir(parents=True, exist_ok=True)
    if subtag:
        (target_dir / subtag).mkdir(exist_ok=True)
        db_name = f"yt_suggestions_{subtag}.db"
    else:
        db_name = "yt_suggestions.db"
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

class YoutubeSuggestionItem(ListItem):
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

    def compose(self) -> ComposeResult:
        yield Label(f"[#ffb86c]{self.feed_name}[/]", id="source")
        yield Label(self.title, id="title", classes="read" if self.is_read else "unread")

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
        webbrowser.open(self.url)

def update_feeds(data_dir: str, tag: str, subtag: str) -> int:
    """Run yt-dlp to fetch the YouTube homepage suggestions and save to SQLite."""
    _setup_logger()
    db_path = get_db_path(data_dir, tag, subtag)
    init_db(db_path)
    
    import json
    import urllib.request
    from core.addon_manager import manager
    
    addon_config = manager.addons_config.get("yt_suggest", {})
    browser = addon_config.get("browser", "firefox")
    
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'dump_single_json': True,
        'playlistend': 50,
        'cookiesfrombrowser': (browser,),
        'quiet': True,
    }
    
    new_count = 0
    now = datetime.now()
    formatted_date = now.strftime("%d/%m/%Y %H:%M")
    sort_date = now.strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Clear old suggestions so the list only reflects the current homepage
    c.execute("DELETE FROM entries")
    
    logger.info(f"Starting YouTube suggestions fetch using browser: {browser}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info("https://www.youtube.com/", download=False)
            
            entries = result.get('entries', [])
            for entry in entries:
                if not entry: continue
                try:
                    title = entry.get('title', 'Unknown Title')
                    url = entry.get('url', '')
                    uploader = entry.get('uploader')
                    
                    if not url: continue
                    
                    if not uploader:
                        # Use oEmbed to fetch the channel name quickly since flat extraction often skips it
                        try:
                            req_url = f"https://www.youtube.com/oembed?url={url}&format=json"
                            with urllib.request.urlopen(req_url) as response:
                                oembed_data = json.loads(response.read().decode())
                                uploader = oembed_data.get('author_name')
                        except Exception as e:
                            logger.debug(f"oEmbed fetch failed for {url}: {e}")
                            
                    if not uploader:
                        uploader = 'YouTube'
                    
                    # Check if exists
                    c.execute("SELECT id FROM entries WHERE url = ?", (url,))
                    if not c.fetchone():
                        c.execute('''
                            INSERT INTO entries (feed_name, title, url, date, sort_date)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (uploader, title, url, formatted_date, sort_date))
                        new_count += 1
                except Exception as e:
                    logger.error(f"Error parsing entry {url}: {e}")
    except Exception as e:
        logger.error(f"Error fetching YouTube suggestions: {e}")
        print(f"Error fetching YouTube suggestions: {e}")

    conn.commit()
    conn.close()
    
    logger.info(f"Finished fetching suggestions. New entries: {new_count}")
    return new_count

def load_articles(current_dir: Path, tag: str, subtag: str, limit: int = 50):
    if subtag:
        db_paths = [current_dir.parent / f"yt_suggestions_{subtag}.db"]
    else:
        db_paths = list(current_dir.glob("yt_suggestions_*.db"))
        # If no subtag, also include yt_suggestions.db if it exists
        if (current_dir / "yt_suggestions.db").exists():
            db_paths.append(current_dir / "yt_suggestions.db")
        
    items = []
    for db_path in db_paths:
        if not db_path.exists():
            continue
            
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries'")
        if not c.fetchone():
            conn.close()
            continue
            
        c.execute("SELECT id, feed_name, title, url, date, is_read, sort_date FROM entries ORDER BY sort_date DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        
        for row in rows:
            item = YoutubeSuggestionItem(
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
            
    items.sort(key=lambda x: x[1], reverse=True)
    return items[:limit]

def search_articles(current_dir: Path, query: str, limit: int = 50):
    db_paths = list(current_dir.glob("yt_suggestions_*.db"))
    if (current_dir / "yt_suggestions.db").exists():
        db_paths.append(current_dir / "yt_suggestions.db")
        
    items = []
    for db_path in db_paths:
        if not db_path.exists():
            continue
            
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entries'")
        if not c.fetchone():
            conn.close()
            continue
            
        c.execute("SELECT id, feed_name, title, url, date, is_read, sort_date FROM entries WHERE title LIKE ? ORDER BY sort_date DESC LIMIT ?", (f'%{query}%', limit))
        rows = c.fetchall()
        conn.close()
        
        for row in rows:
            item = YoutubeSuggestionItem(
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
            
    return items
