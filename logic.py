import httpx
import feedparser
import os
from pathlib import Path
from datetime import datetime
from markdownify import markdownify as md
from slugify import slugify
import yaml
from models import FeedConfig, AppConfig

async def fetch_feed(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True)
        return feedparser.parse(response.text)

def sanitize_filename(name: str) -> str:
    return slugify(name)

def save_entry(entry: dict, feed_config: FeedConfig, data_dir: str) -> bool:
    # Prepare directory
    target_dir = Path(data_dir) / feed_config.tag
    if feed_config.subtag:
        target_dir = target_dir / feed_config.subtag
    target_dir.mkdir(parents=True, exist_ok=True)

    # Prepare metadata
    title = entry.get("title", "No Title")
    author = entry.get("author", "Unknown Author")
    link = entry.get("link", "")
    published = entry.get("published", "")
    
    # Create filename: YYYY-MM-DD_FeedName_Title.md
    # Try to get a date
    dt = None
    if "published_parsed" in entry and entry.published_parsed:
        dt = datetime(*entry.published_parsed[:6])
    else:
        dt = datetime.now()

    date_str = dt.strftime("%Y-%m-%d")
    formatted_date = dt.strftime("%d/%m/%Y %H:%M")

    safe_title = sanitize_filename(title)
    filename = f"{date_str}_{slugify(feed_config.name)}_{safe_title}.md"
    file_path = target_dir / filename

    if file_path.exists():
        return False # Already exists

    # Convert content to Markdown
    content_html = ""
    if "content" in entry:
        content_html = entry.content[0].value
    elif "summary" in entry:
        content_html = entry.summary
    
    content_md = md(content_html)

    if content_md == "### Abbonati per leggere anche":
        return False

    # Frontmatter
    frontmatter = {
        "title": title,
        "author": author,
        "url": link,
        "date": formatted_date,
        "feed": feed_config.name
    }

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        yaml.safe_dump(frontmatter, f, allow_unicode=True)
        f.write("---\n\n")
        f.write(content_md)
    
    return True

async def update_all_feeds(config: AppConfig) -> int:
    new_count = 0
    for feed in config.feeds:
        try:
            parsed = await fetch_feed(feed.url)
            for entry in parsed.entries:
                if save_entry(entry, feed, config.data_dir):
                    new_count += 1
        except Exception as e:
            print(f"Error fetching {feed.name}: {e}")
    return new_count
