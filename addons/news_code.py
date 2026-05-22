from pathlib import Path
from ui_components import ArticleItem
import yaml
import webbrowser
import re

class CodeArticleItem(ArticleItem):
    def __init__(self, path: Path):
        super().__init__(path)
        self.url = ""
        # We need to find the link. We first try to get it from the frontmatter 'url'
        # If not present, we can regex the markdown content for the first link.
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                if content.startswith("---"):
                    parts = content.split("---")
                    if len(parts) >= 3:
                        meta = yaml.safe_load(parts[1])
                        self.url = meta.get("url", "")
                        
                    # If still no URL, search the content
                    if not self.url and len(parts) >= 3:
                        body = "---".join(parts[2:])
                        match = re.search(r'\[.*?\]\((https?://.*?)\)', body)
                        if match:
                            self.url = match.group(1)
        except:
            pass

    def on_select(self):
        if self.url:
            webbrowser.open(self.url)

def load_articles(current_dir: Path, tag: str, subtag: str, limit: int = 50):
    md_files = list(current_dir.glob("*.md"))
    md_files.sort(key=lambda p: p.name, reverse=True)
    md_files = md_files[:limit]
    
    items_with_dates = []
    for path in md_files:
        item = CodeArticleItem(path)
            
        sort_key = ""
        try:
            date_part, time_part = item.date.split(" ")
            day, month, year = date_part.split("/")
            sort_key = f"{year}-{month}-{day} {time_part}"
        except:
            sort_key = item.date
            
        items_with_dates.append((item, sort_key))
        
    items_with_dates.sort(key=lambda x: x[1], reverse=True)
    return items_with_dates
