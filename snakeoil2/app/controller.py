"""GUI-thread view of the parameters: a value mirror plus patch actions. Talks to the engine only by events."""
from PySide6.QtCore import QObject, Signal

from ..dsp.params import PARAMS
from ..patches import INIT_NAME, PatchError, capture


class Controller(QObject):
    changed = Signal(str)

    def __init__(self, queue, store):
        super().__init__()
        self.queue = queue
        self.store = store
        self.values = PARAMS.defaults()
        self.current_patch = INIT_NAME
        self.dirty = False

    def set_param(self, pid, value):
        value = PARAMS.coerce(pid, value)
        if self.values[pid] == value:
            return
        self.values[pid] = value
        self.queue.put(("param", pid, value))
        if PARAMS.by_id[pid].stored:
            self.dirty = True
        self.changed.emit(pid)

    def load_patch(self, name):
        values, warnings = self.store.load(name)
        for pid in ("master_volume", "limiter_on"):      # output stage is not part of a sound
            values[pid] = self.values[pid]
        changed = [pid for pid, v in values.items() if self.values[pid] != v]
        self.values = values
        self.queue.put(("load", dict(values)))
        self.current_patch = name
        self.dirty = False
        self.store.set_last_used(name)
        for pid in changed:
            self.changed.emit(pid)
        return warnings

    def save_patch(self, name):
        self.store.save(name, capture(self.values))
        self.current_patch = name
        self.dirty = False
        self.store.set_last_used(name)

    def save_current(self):
        self.save_patch(self.current_patch)

    def rename_patch(self, new):
        self.store.rename(self.current_patch, new)
        self.current_patch = new

    def delete_patch(self):
        self.store.delete(self.current_patch)
        self.load_patch(INIT_NAME)
