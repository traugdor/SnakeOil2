"""Mod matrix evaluation: sources, relative scaling, additive pitch and exponential LFO-rate rows."""
from dataclasses import dataclass, field

from .constants import (LFO_RATE_CEIL, LFO_RATE_FLOOR, LFO_RATE_MOD_OCTAVES, MOD_SLOTS, MOD_SMOOTH,
                        PITCH_MOD_SEMITONES)
from .destinations import DEST_BY_NAME, PITCH, RATE, SOURCE_NAMES, SRC_NOTE


def effective(base, total, lo, hi):
    """``base * (1 + total)`` clamped to ``[lo, hi]``; a base of 0 stays 0."""
    return min(max(base * (1.0 + total), lo), hi)


def note_source(note):
    """Note number as a bipolar source: middle C = 0, clipped to [-1, 1]."""
    if note is None:
        return 0.0
    return min(max((note - 60) / 60.0, -1.0), 1.0)


def smooth(current, target, coeff=MOD_SMOOTH):
    return current + coeff * (target - current)


@dataclass
class Mods:
    values: dict = field(default_factory=dict)                       # param id -> effective value
    pitch: dict = field(default_factory=lambda: {"a": 0.0, "b": 0.0})  # bank -> semitones


class ModMatrix:
    def __init__(self, table):
        self.table = table
        self._rows = [(0, 0.0, None)] * MOD_SLOTS
        self._active = []

    def set_row(self, slot, src_name, scale, dst_name):
        if not 1 <= slot <= MOD_SLOTS:
            raise ValueError("slot out of range: %r" % (slot,))
        if src_name not in SOURCE_NAMES:
            raise ValueError("unknown source: %r" % (src_name,))
        dst = None if dst_name == "none" else DEST_BY_NAME.get(dst_name)
        if dst_name != "none" and dst is None:
            raise ValueError("unknown destination: %r" % (dst_name,))
        self._rows[slot - 1] = (SOURCE_NAMES.index(src_name), float(scale), dst)
        self._active = [(s, sc, d) for s, sc, d in self._rows if s and sc and d is not None]

    @property
    def empty(self):
        return not self._active

    @property
    def uses_note(self):
        return any(s == SRC_NOTE for s, _, _ in self._active)

    def evaluate(self, base, sources, note_src, kinds=None):
        totals = {}
        for src, scale, dst in self._active:
            if kinds is not None and dst.kind not in kinds:
                continue
            value = note_src if src == SRC_NOTE else sources[src]
            totals[dst] = totals.get(dst, 0.0) + scale * value
        mods = Mods()
        for dst, total in totals.items():
            if dst.kind == PITCH:
                mods.pitch[dst.bank] += total * PITCH_MOD_SEMITONES
            elif dst.kind == RATE:
                v = base[dst.param_id] * 2.0 ** (total * LFO_RATE_MOD_OCTAVES)
                mods.values[dst.param_id] = min(max(v, LFO_RATE_FLOOR), LFO_RATE_CEIL)
            else:
                d = self.table.by_id[dst.param_id]
                mods.values[dst.param_id] = effective(base[dst.param_id], total, d.lo, d.hi)
        return mods
