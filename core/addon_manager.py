import yaml
import importlib.util
from pathlib import Path
import sys

class AddonManager:
    def __init__(self, config_path="addon_config.yml", addons_dir="addons"):
        self.config_path = config_path
        self.addons_dir = Path(addons_dir)
        self.addons_config = {}
        self.addons = {}
        self.tag_to_addon = {}
        self.feed_name_to_addon = {}
        self.load_config()
        self.load_addons()

    def load_config(self):
        if Path(self.config_path).exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and "addons" in data:
                    self.addons_config = data["addons"]

    def load_addons(self):
        if not self.addons_dir.exists():
            self.addons_dir.mkdir(parents=True, exist_ok=True)
            return

        for addon_name, config in self.addons_config.items():
            if not config.get("enabled", False):
                continue
            
            addon_file = self.addons_dir / f"{addon_name}.py"
            if addon_file.exists():
                module_name = f"addons.{addon_name}"
                spec = importlib.util.spec_from_file_location(module_name, addon_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    self.addons[addon_name] = module
                    
                    for tag in config.get("tags", []):
                        self.tag_to_addon[tag] = module
                        
                    for feed_name in config.get("feed_names", []):
                        self.feed_name_to_addon[feed_name] = module

    def get_addon(self, feed_name: str, tag: str, subtag: str = ""):
        if feed_name in self.feed_name_to_addon:
            return self.feed_name_to_addon[feed_name]
            
        if subtag:
            addon = self.tag_to_addon.get(f"{tag}/{subtag}")
            if addon:
                return addon
        return self.tag_to_addon.get(tag)

    def get_addon_for_tag(self, tag: str, subtag: str = ""):
        if subtag:
            addon = self.tag_to_addon.get(f"{tag}/{subtag}")
            if addon:
                return addon
        return self.tag_to_addon.get(tag)

# Singleton instance
manager = AddonManager()
