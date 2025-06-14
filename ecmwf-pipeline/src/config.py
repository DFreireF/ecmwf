# src/config.py
import yaml
from pathlib import Path
def load_config(path: Path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)