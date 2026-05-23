import sqlite3
import webbrowser
from pathlib import Path
from datetime import datetime
import re
from markdownify import markdownify

from textual.widgets import ListItem, Label
from textual.app import ComposeResult

def get_db_path(data_dir: str, tag: str, subtag: str) -> Path:
    target_dir = Path(data_dir) / tag
    target_dir.mkdir(parents=True, exist_ok=True)
    if subtag:
        (target_dir / subtag).mkdir(exist_ok=True)
        db_name = f"telegram_{subtag}.db"
    else:
        db_name = "telegram.db"
    return target_dir / db_name

def init_db(db_path: Path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_name TEXT,
            text_content TEXT,
            embedded_link TEXT,
            telegram_link TEXT,
            date TEXT,
            sort_date TEXT,
            is_read INTEGER DEFAULT 0,
            UNIQUE(telegram_link)
        )
    ''')
    conn.commit()
    conn.close()

class TelegramMessageItem(ListItem):
    def __init__(self, db_path: Path, entry_id: int, feed_name: str, text_content: str, embedded_link: str, telegram_link: str, date: str, is_read: bool, sort_date: str):
        super().__init__()
        self.db_path = db_path
        self.entry_id = entry_id
        self.feed_name = feed_name
        self.text_content = text_content
        self.embedded_link = embedded_link
        self.telegram_link = telegram_link
        self.date = date
        self.is_read = is_read
        self.sort_date = sort_date
        
        # Apply padding and allow multi-line height natively
        self.styles.height = "auto"
        self.styles.padding = (1, 1)

    def compose(self) -> ComposeResult:
        # Provide header with feed name and date
        header_text = f"[#ffb86c]{self.feed_name}[/] - {self.date}"
        if self.embedded_link:
            header_text += " (🔗 Link Available)"
            
        yield Label(header_text, id="source", classes="read" if self.is_read else "unread")
        
        content_label = Label(self.text_content, id="title", classes="read" if self.is_read else "unread")
        content_label.styles.height = "auto"
        content_label.styles.margin = (0, 0, 1, 0)
        yield content_label

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            try:
                self.query_one("#title").add_class("read").remove_class("unread")
                self.query_one("#source").add_class("read").remove_class("unread")
            except Exception:
                pass
            
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("UPDATE entries SET is_read = 1 WHERE id = ?", (self.entry_id,))
            conn.commit()
            conn.close()
            
    def on_select(self):
        if self.embedded_link:
            webbrowser.open(self.embedded_link)

def update_feeds(data_dir: str, tag: str, subtag: str) -> int:
    import urllib.request
    from bs4 import BeautifulSoup
    from core.config import AppConfig
    
    config = AppConfig.load("config.yml")
    new_count = 0
    
    for feed in config.feeds:
        if feed.tag != tag:
            continue
        if subtag and feed.subtag != subtag:
            continue
            
        if "t.me/s/" not in feed.url:
            continue
            
        db_path = get_db_path(data_dir, feed.tag, feed.subtag)
        init_db(db_path)
        
        try:
            req = urllib.request.Request(feed.url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                html = response.read().decode('utf-8')
                
            soup = BeautifulSoup(html, 'html.parser')
            messages = soup.find_all('div', class_='tgme_widget_message')
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            for m in messages:
                text_div = m.find('div', class_='tgme_widget_message_text')
                time_tag = m.find('time')
                link_tag = m.find('a', class_='tgme_widget_message_date')
                
                # Check for image only (no text div)
                if not text_div:
                    continue
                    
                # Extract text using BeautifulSoup's get_text with newlines
                text_content = text_div.get_text(separator='\n').strip()
                if not text_content:
                    continue
                    
                # Find embedded link
                embedded_link = ""
                url_match = re.search(r'https?://[^\s]+', text_content)
                if url_match:
                    embedded_link = url_match.group(0)
                    
                telegram_link = link_tag['href'] if link_tag else ""
                
                # Format dates
                now = datetime.now()
                formatted_date = now.strftime("%d/%m/%Y %H:%M")
                sort_date = now.strftime("%Y-%m-%d %H:%M:%S")
                
                if time_tag and time_tag.has_attr('datetime'):
                    try:
                        # e.g. "2026-05-22T12:34:52+00:00"
                        dt = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
                        formatted_date = dt.strftime("%d/%m/%Y %H:%M")
                        sort_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pass
                        
                c.execute("SELECT id FROM entries WHERE telegram_link = ?", (telegram_link,))
                if c.fetchone():
                    continue
                    
                c.execute('''
                    INSERT INTO entries (feed_name, text_content, embedded_link, telegram_link, date, sort_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (feed.name, text_content, embedded_link, telegram_link, formatted_date, sort_date))
                new_count += 1
                
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error fetching telegram web preview {feed.url}: {e}")
            
    return new_count

def load_articles(current_dir: Path, tag: str, subtag: str, limit: int = 50):
    if subtag:
        db_paths = [current_dir.parent / f"telegram_{subtag}.db"]
    else:
        db_paths = list(current_dir.glob("telegram_*.db"))
        if (current_dir / "telegram.db").exists():
            db_paths.append(current_dir / "telegram.db")
            
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
            
        c.execute("SELECT id, feed_name, text_content, embedded_link, telegram_link, date, is_read, sort_date FROM entries ORDER BY sort_date DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        
        for row in rows:
            item = TelegramMessageItem(
                db_path=db_path,
                entry_id=row[0],
                feed_name=row[1],
                text_content=row[2],
                embedded_link=row[3],
                telegram_link=row[4],
                date=row[5],
                is_read=bool(row[6]),
                sort_date=row[7]
            )
            items.append((item, item.sort_date))
            
    items.sort(key=lambda x: x[1], reverse=True)
    return items[:limit]
