import httpx
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from slugify import slugify
from markdownify import markdownify as md
import yaml

def save_entry(entry: dict, feed_config, data_dir: str) -> bool:
    """
    Custom save_entry for Il Sole 24 Ore to fetch full article text.
    """
    target_dir = Path(data_dir) / feed_config.tag
    if feed_config.subtag:
        target_dir = target_dir / feed_config.subtag
    target_dir.mkdir(parents=True, exist_ok=True)

    title = entry.get("title", "No Title")
    author = entry.get("author", "Unknown Author")
    link = entry.get("link", "")
    
    dt = None
    if "published_parsed" in entry and entry.published_parsed:
        dt = datetime(*entry.published_parsed[:6])
    else:
        dt = datetime.now()

    date_str = dt.strftime("%Y-%m-%d")
    formatted_date = dt.strftime("%d/%m/%Y %H:%M")

    safe_title = slugify(title)
    feed_name_slug = slugify(feed_config.name)
    filename = f"{date_str}_{feed_name_slug}_{safe_title}.md"
    file_path = target_dir / filename

    if file_path.exists():
        return False # Already exists

    # Fetch the full article content
    content_md = ""
    try:
        if link:
            r = httpx.get(link, follow_redirects=True, timeout=15.0)
            soup = BeautifulSoup(r.text, 'html.parser')
            paragraphs = soup.find_all('p', class_='atext')
            
            if paragraphs:
                content_md = "\n\n".join([p.text.strip() for p in paragraphs if p.text.strip()])
                
    except Exception as e:
        print(f"Error fetching ilsole24ore article {link}: {e}")
        
    if not content_md:
        # Fallback to standard rss content
        content_html = ""
        if "content" in entry:
            content_html = entry.content[0].value
        elif "summary" in entry:
            content_html = entry.summary
        
        content_md = md(content_html)

    if content_md.strip() == "### Abbonati per leggere anche":
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
