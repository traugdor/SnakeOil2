import os
from pathlib import Path


def config_dir(override=None):
    if override:
        base = Path(override)
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home())) / "snakeoil2"
    else:
        base = Path.home() / ".config" / "snakeoil2"
    base.mkdir(parents=True, exist_ok=True)
    return base


def patches_dir(config):
    d = Path(config) / "patches"
    d.mkdir(parents=True, exist_ok=True)
    return d
