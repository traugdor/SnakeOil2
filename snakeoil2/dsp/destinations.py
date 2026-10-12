"""Mod-matrix sources and destination names (pure data, no imports from params)."""
from dataclasses import dataclass

SOURCE_NAMES = ("none", "Note Number", "LFO 1", "LFO 2", "Mod Wheel", "Aftertouch")
SRC_NONE, SRC_NOTE, SRC_LFO1, SRC_LFO2, SRC_WHEEL, SRC_AFTERTOUCH = range(len(SOURCE_NAMES))

RELATIVE, PITCH, RATE = "relative", "pitch", "rate"


@dataclass(frozen=True)
class Destination:
    name: str
    param_id: str   # "" for the additive pitch destinations
    kind: str       # RELATIVE, PITCH or RATE
    bank: str       # "a", "b", or "" for a global destination


BANK_DEST_KEYS = (
    ("OSC1 Level", "osc1_level"), ("OSC1 PWM", "osc1_pwm"), ("OSC1 Sq Level", "osc1_square_level"),
    ("OSC2 Level", "osc2_level"), ("OSC2 Tune", "osc2_coarse"),
    ("OSC2 Fine", "osc2_fine"), ("OSC2 PWM", "osc2_pwm"),
    ("Noise Level", "noise_level"), ("Bank Volume", "volume"),
    ("Cutoff", "cutoff"), ("Resonance", "resonance"), ("Env Amount", "flt_amount"),
    ("Key Trk", "keytrack"), ("Vel>Cut", "vel_cutoff"),
    ("Flt Attack", "flt_attack"), ("Flt Decay", "flt_decay"),
    ("Flt Sustain", "flt_sustain"), ("Flt Release", "flt_release"),
    ("Amp Attack", "amp_attack"), ("Amp Decay", "amp_decay"),
    ("Amp Sustain", "amp_sustain"), ("Amp Release", "amp_release"),
)

GLOBAL_DEST_KEYS = (
    ("Mix", "mix"), ("Detune", "detune"), ("Width", "width"), ("Tempo", "tempo_bpm"),
    ("LFO 1 Rate", "lfo1_rate"), ("LFO 2 Rate", "lfo2_rate"),
    ("Chorus Depth", "fx_chorus_depth"), ("Delay Time", "fx_delay_time"),
    ("Delay Feedback", "fx_delay_feedback"), ("Delay Tone", "fx_delay_tone"),
    ("Reverb Amount", "fx_reverb_amount"), ("Reverb Size", "fx_reverb_size"),
    ("Reverb Damping", "fx_reverb_damp"),
)


def _build():
    out = []
    for bank in ("a", "b"):
        for label, key in BANK_DEST_KEYS:
            out.append(Destination("%s: %s" % (bank.upper(), label), "%s_%s" % (bank, key), RELATIVE, bank))
        out.append(Destination("%s: Pitch" % bank.upper(), "", PITCH, bank))
    for label, pid in GLOBAL_DEST_KEYS:
        kind = RATE if pid in ("lfo1_rate", "lfo2_rate") else RELATIVE
        out.append(Destination(label, pid, kind, ""))
    return tuple(out)


DESTINATIONS = _build()
DEST_NAMES = ("none",) + tuple(d.name for d in DESTINATIONS)
DEST_BY_NAME = {d.name: d for d in DESTINATIONS}
