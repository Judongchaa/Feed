import httpx
import feedparser
import os
from pathlib import Path
from datetime import datetime
from markdownify import markdownify as md
from slugify import slugify
import yaml
from core.config import FeedConfig, AppConfig
from core.addon_manager import manager as addon_manager
import asyncio

async def fetch_feed(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True)
        return feedparser.parse(response.text)

def sanitize_filename(name: str) -> str:
    return slugify(name)

def save_entry(entry: dict, feed_config: FeedConfig, data_dir: str) -> bool:
    # Check if an addon handles this tag
    addon = addon_manager.get_addon_for_tag(feed_config.tag, feed_config.subtag)
    if addon and hasattr(addon, 'save_entry'):
        return addon.save_entry(entry, feed_config, data_dir)

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

async def update_all_feeds(config: AppConfig, target_tag: str = None, target_subtag: str = None) -> int:
    new_count = 0
    for feed in config.feeds:
        if target_tag and feed.tag != target_tag:
            continue
        if target_subtag and feed.subtag != target_subtag:
            continue
            
        try:
            parsed = await fetch_feed(feed.url)
            for entry in parsed.entries:
                if save_entry(entry, feed, config.data_dir):
                    new_count += 1
        except Exception as e:
            print(f"Error fetching {feed.name}: {e}")
            
    # Update addons that define update_feeds
    for tag_key, module in addon_manager.tag_to_addon.items():
        parts = tag_key.split("/")
        tag = parts[0] if len(parts) > 0 else ""
        subtag = parts[1] if len(parts) > 1 else ""
        
        if target_tag and tag != target_tag:
            continue
        if target_subtag and subtag != target_subtag:
            continue
            
        if hasattr(module, 'update_feeds'):
            try:
                added = await asyncio.to_thread(module.update_feeds, config.data_dir, tag, subtag)
                if isinstance(added, int):
                    new_count += added
            except Exception as e:
                print(f"Error updating addon {tag_key}: {e}")

    return new_count
