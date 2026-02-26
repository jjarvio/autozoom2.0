import yaml
from pathlib import Path

class Config:
    def __init__(self, path="config.yaml"):
        self.path = Path(path)
        self.data = {}

        self.load()

    def load(self):
        if not self.path.exists():
            raise FileNotFoundError(f"Config file not found: {self.path}")

        with open(self.path, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

    def get(self, *keys, default=None):
        value = self.data
        for k in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(k)
        return value if value is not None else default
