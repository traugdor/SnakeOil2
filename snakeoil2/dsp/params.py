"""The declarative parameter table: one row per control, shared by engine, patches and GUI."""
import math
from dataclasses import dataclass

from . import constants as C
from .destinations import DEST_NAMES, SOURCE_NAMES

CONTINUOUS, TOGGLE, CHOICE = "continuous", "toggle", "choice"


@dataclass(frozen=True)
class ParamDef:
    id: str
    label: str
    group: str
    kind: str
    default: object
    lo: float = 0.0
    hi: float = 1.0
    choices: tuple = ()
    scale: str = "linear"      # "linear" or "log" (GUI mapping only)
    stored: bool = True        # False: not saved in patches


def _cont(pid, label, group, default, lo, hi, scale="linear", stored=True):
    return ParamDef(pid, label, group, CONTINUOUS, float(default), float(lo), float(hi), (), scale, stored)


def _toggle(pid, label, group, default, stored=True):
    return ParamDef(pid, label, group, TOGGLE, bool(default), stored=stored)


def _choice(pid, label, group, choices, default, stored=True):
    return ParamDef(pid, label, group, CHOICE, default, choices=tuple(choices), stored=stored)


def _bank(prefix, name):
    def g(part):
        return "Bank %s / %s" % (name, part)

    p = prefix + "_"
    out = [
        _toggle(p + "osc1_saw", "Saw", g("OSC1"), True),
        _toggle(p + "osc1_square", "Square", g("OSC1"), False),
        _cont(p + "osc1_pwm", "PWM", g("OSC1"), 0.5, 0.0, 1.0),
        _cont(p + "osc1_level", "Level", g("OSC1"), 0.7, 0.0, 1.0),
        _toggle(p + "osc1_octave_down", "Oct -1", g("OSC1"), True),
        _choice(p + "osc2_wave", "Wave", g("OSC2"), C.OSC2_WAVES, "square"),
        _cont(p + "osc2_pwm", "PWM", g("OSC2"), 0.5, 0.0, 1.0),
        _cont(p + "osc2_level", "Level", g("OSC2"), 0.5, 0.0, 1.0),
        _cont(p + "osc2_coarse", "Coarse", g("OSC2"), 0.0, -12.0, 12.0),
        _cont(p + "osc2_fine", "Fine", g("OSC2"), 0.0, -0.5, 0.5),
        _toggle(p + "osc2_octave_up", "Oct +1", g("OSC2"), True),
        _choice(p + "mod_mode", "Mod", g("Modulation"), C.MOD_MODES, "OFF"),
        _cont(p + "noise_level", "Level", g("Noise"), 0.0, 0.0, 1.0),
        _choice(p + "noise_color", "Color", g("Noise"), C.NOISE_COLORS, "white"),
        _cont(p + "cutoff", "Cutoff", g("Filter"), 2000.0, 20.0, 20000.0, "log"),
        _cont(p + "resonance", "Reso", g("Filter"), 0.0, 0.0, 1.0),
        _cont(p + "flt_amount", "Env Amt", g("Filter"), 0.0, -1.0, 1.0),
        _cont(p + "keytrack", "Key Trk", g("Filter"), 0.0, 0.0, 1.0),
        _cont(p + "vel_cutoff", "Vel>Cut", g("Filter"), 0.0, 0.0, 1.0),
    ]
    for part, adsr in (("Filter Env", C.DEFAULT_FLT_ADSR), ("Amp Env", C.DEFAULT_AMP_ADSR)):
        key = "flt" if part == "Filter Env" else "amp"
        out += [
            _cont("%s%s_attack" % (p, key), "A", g(part), adsr[0], C.AMP_TIME_MIN, C.AMP_ATTACK_MAX, "log"),
            _cont("%s%s_decay" % (p, key), "D", g(part), adsr[1], C.AMP_TIME_MIN, C.AMP_DECAY_MAX, "log"),
            _cont("%s%s_sustain" % (p, key), "S", g(part), adsr[2], 0.0, 1.0),
            _cont("%s%s_release" % (p, key), "R", g(part), adsr[3], C.AMP_TIME_MIN, C.AMP_RELEASE_MAX, "log"),
        ]
    out.append(_cont(p + "volume", "Volume", g("Output"), 0.8, 0.0, 1.0))
    return out


def _build():
    rows = _bank("a", "A") + _bank("b", "B")
    rows += [
        _cont("mix", "Mix", "Banks", 0.5, 0.0, 1.0),
        _cont("detune", "Detune", "Banks", 0.0, 0.0, C.DETUNE_MAX),
        _cont("width", "Width", "Banks", 0.0, 0.0, 1.0),
        _cont("master_volume", "Volume", "Master", 0.8, 0.0, C.MASTER_GAIN_MAX, stored=False),
        _toggle("velocity_on", "Velocity", "Master", True),
        _toggle("limiter_on", "Auto Limiter", "Master", False, stored=False),
    ]
    for n in (1, 2):
        rows += [
            _cont("lfo%d_rate" % n, "Rate", "LFO %d" % n, C.DEFAULT_LFO_RATE, C.LFO_RATE_MIN, C.LFO_RATE_MAX, "log"),
            _choice("lfo%d_wave" % n, "Wave", "LFO %d" % n, C.LFO_WAVES, "sine"),
        ]
    for i in range(1, C.MOD_SLOTS + 1):
        rows += [
            _choice("mod%d_src" % i, "Source", "Mod Matrix", SOURCE_NAMES, "none"),
            _cont("mod%d_scale" % i, "Scale", "Mod Matrix", 0.0, -1.0, 1.0),
            _choice("mod%d_dst" % i, "Destination", "Mod Matrix", DEST_NAMES, "none"),
        ]
    rows += [
        _cont("tempo_bpm", "BPM", "Tempo", C.DEFAULT_TEMPO, C.TEMPO_MIN, C.TEMPO_MAX),
        _toggle("fx_chorus_on", "Chorus", "Effects", False),
        _cont("fx_chorus_depth", "Depth", "Effects", 0.3, 0.0, 1.0),
        _toggle("fx_delay_on", "Delay", "Effects", False),
        _cont("fx_delay_time", "Time", "Effects", 300.0, 1.0, 4000.0, "log"),
        _toggle("fx_delay_pingpong", "Ping-pong", "Effects", False),
        _cont("fx_delay_feedback", "Feedback", "Effects", 0.35, 0.0, 0.95),
        _cont("fx_delay_tone", "Tone", "Effects", 0.25, 0.0, 0.9),
        _toggle("fx_delay_sync", "Sync", "Effects", False),
        _choice("fx_delay_division", "Division", "Effects", C.DELAY_DIVISION_NAMES, "1/8"),
        _toggle("fx_reverb_on", "Reverb", "Effects", False),
        _cont("fx_reverb_amount", "Amount", "Effects", 0.3, 0.0, 1.0),
        _cont("fx_reverb_size", "Size", "Effects", 0.84, 0.5, 0.98),
        _cont("fx_reverb_damp", "Damping", "Effects", 0.25, 0.0, 0.9),
    ]
    return rows


BANK_KEYS = tuple(p.id[2:] for p in _bank("a", "A"))


class ParamTable:
    def __init__(self, defs):
        self._defs = tuple(defs)
        self.by_id = {p.id: p for p in self._defs}
        if len(self.by_id) != len(self._defs):
            raise ValueError("duplicate parameter id")
        self.ids = tuple(p.id for p in self._defs)

    def __iter__(self):
        return iter(self._defs)

    def __contains__(self, pid):
        return pid in self.by_id

    def __len__(self):
        return len(self._defs)

    def defaults(self):
        return {p.id: p.default for p in self._defs}

    def groups(self):
        """Group names in first-appearance order."""
        seen = []
        for p in self._defs:
            if p.group not in seen:
                seen.append(p.group)
        return seen

    def coerce(self, pid, value):
        """Return a valid value for ``pid`` (clamped) or raise ValueError; KeyError if unknown."""
        p = self.by_id[pid]
        if p.kind == TOGGLE:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)) and value in (0, 1):
                return bool(value)
            raise ValueError("%s: not a boolean: %r" % (pid, value))
        if p.kind == CHOICE:
            if value in p.choices:
                return value
            raise ValueError("%s: not one of %s: %r" % (pid, p.choices, value))
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s: not a number: %r" % (pid, value))
        try:
            v = float(value)
        except OverflowError:
            raise ValueError("%s: out of range: too large" % pid)
        if not math.isfinite(v):
            raise ValueError("%s: not finite: %r" % (pid, value))
        return min(max(v, p.lo), p.hi)

    def export(self):
        """JSON-serialisable description, the input for a later C++ parameter generator."""
        rows = []
        for p in self._defs:
            row = {"id": p.id, "label": p.label, "group": p.group, "kind": p.kind,
                   "default": p.default, "stored": p.stored}
            if p.kind == CONTINUOUS:
                row.update(lo=p.lo, hi=p.hi, scale=p.scale)
            elif p.kind == CHOICE:
                row["choices"] = list(p.choices)
            rows.append(row)
        return rows


PARAMS = ParamTable(_build())
