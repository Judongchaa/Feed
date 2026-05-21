import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any

@dataclass
class FeedConfig:
    name: str
    url: str
    tag: str
    subtag: str = ""

@dataclass
class AppConfig:
    data_dir: str
    refresh_interval_minutes: int
    feeds: List[FeedConfig] = field(default_factory=list)

    @classmethod
    def load(cls, path: str = "config.yml") -> "AppConfig":
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        
        settings = data.get("settings", {})
        feeds_data = data.get("feeds", [])
        
        feeds = [
            FeedConfig(
                name=f["name"],
                url=f["url"],
                tag=f["tag"],
                subtag=f.get("subtag", "")
            )
            for f in feeds_data
        ]
        
        return cls(
            data_dir=settings.get("data_dir", "./rss_data"),
            refresh_interval_minutes=settings.get("refresh_interval_minutes", 60),
            feeds=feeds
        )

    def save(self, path: str = "config.yml"):
        data = {
            "settings": {
                "data_dir": self.data_dir,
                "refresh_interval_minutes": self.refresh_interval_minutes
            },
            "feeds": [
                {
                    "name": f.name,
                    "url": f.url,
                    "tag": f.tag,
                    "subtag": f.subtag
                }
                for f in self.feeds
            ]
        }
        with open(path, "w") as f:
            yaml.safe_dump(data, f)
