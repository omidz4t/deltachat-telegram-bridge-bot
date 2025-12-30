import yaml
from pathlib import Path

def load_config():
    config_path = Path("config.yml")
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {}

def save_config(config):
    config_path = Path("config.yml")
    if not config_path.exists():
        config_path.touch()
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f)
