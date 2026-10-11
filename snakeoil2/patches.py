"""Patch files: JSON ``{"version", "name", "params"}`` over the parameter table. No Qt, no engine."""
import json
import os
import re
import tempfile
from pathlib import Path

from .dsp.params import PARAMS

CURRENT_VERSION = 1
INIT_NAME = "Init"
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.\-]{0,63}$")
_RESERVED = {"con", "prn", "aux", "nul"} | {"com%d" % i for i in range(1, 10)} | {"lpt%d" % i for i in range(1, 10)}
_SETTINGS = "patch_settings.json"


class PatchError(Exception):
    pass


def validate_name(name):
    if (not isinstance(name, str) or not _NAME_RE.match(name) or name.endswith((".", " "))
            or name.split(".")[0].strip().lower() in _RESERVED):
        raise PatchError("invalid patch name: %r" % (name,))
    return name


def capture(values):
    """The patch-worthy subset of a full parameter dict."""
    return {p.id: values[p.id] for p in PARAMS if p.stored}


def resolve(data):
    """Turn patch file contents into a complete parameter dict. Returns ``(values, warnings)``."""
    if not isinstance(data, dict) or not isinstance(data.get("version"), int) or not isinstance(data.get("params"), dict):
        raise PatchError("not a patch file")
    if data["version"] > CURRENT_VERSION:
        raise PatchError("patch was saved by a newer version (%d)" % data["version"])
    warnings = []
    values = PARAMS.defaults()
    for pid, raw in data["params"].items():
        if pid not in PARAMS or not PARAMS.by_id[pid].stored:
            warnings.append("ignored unknown parameter %r" % (pid,))
            continue
        try:
            values[pid] = PARAMS.coerce(pid, raw)
        except ValueError:
            warnings.append("invalid value for %s, using the default" % pid)
    return values, warnings


def _atomic_write(path, text):
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


class PatchStore:
    def __init__(self, directory):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, name):
        return self.dir / (validate_name(name) + ".json")

    def names(self):
        found = []
        for f in sorted(self.dir.glob("*.json"), key=lambda p: p.stem.lower()):
            if f.name == _SETTINGS or f.stem == INIT_NAME:
                continue
            try:
                validate_name(f.stem)
            except PatchError:
                continue
            found.append(f.stem)
        return [INIT_NAME] + found

    def load(self, name):
        if name == INIT_NAME:
            return resolve({"version": CURRENT_VERSION, "name": INIT_NAME, "params": {}})
        path = self._path(name)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise PatchError("no such patch: %s" % name)
        except (OSError, ValueError) as e:
            raise PatchError("cannot read patch %s: %s" % (name, e))
        return resolve(data)

    def save(self, name, values):
        if name == INIT_NAME:
            raise PatchError("the Init patch is read-only")
        path = self._path(name)
        data = {"version": CURRENT_VERSION, "name": name, "params": capture({**PARAMS.defaults(), **values})}
        _atomic_write(path, json.dumps(data, indent=2))

    def rename(self, old, new):
        if INIT_NAME in (old, new):
            raise PatchError("the Init patch is read-only")
        src, dst = self._path(old), self._path(new)
        if not src.exists():
            raise PatchError("no such patch: %s" % old)
        if dst.exists():
            raise PatchError("a patch named %s already exists" % new)
        os.replace(src, dst)
        if self.last_used() == old:
            self.set_last_used(new)

    def delete(self, name):
        if name == INIT_NAME:
            raise PatchError("the Init patch is read-only")
        path = self._path(name)
        if not path.exists():
            raise PatchError("no such patch: %s" % name)
        path.unlink()

    def last_used(self):
        try:
            name = json.loads((self.dir / _SETTINGS).read_text(encoding="utf-8")).get("last_used", INIT_NAME)
        except (OSError, ValueError, AttributeError):
            return INIT_NAME
        return name if name in self.names() else INIT_NAME

    def set_last_used(self, name):
        _atomic_write(self.dir / _SETTINGS, json.dumps({"last_used": name}))
