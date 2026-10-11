"""One oscillator bank: OSC1 (saw/square) -> modulation -> OSC2, noise, 12 dB filter, two envelopes."""
import numpy as np

from . import noise
from .constants import (AMP_SCALE, FLT_ENV_OCTAVES, FLT_VEL_OCTAVES, FM_INDEX_MAX, FORCED_RELEASE_S,
                        NOISE_TABLE_LEN)
from .envelopes import IDLE, Envelope
from .filters import LPF_MAX_HZ, LPF_MIN_HZ, LowPass, lpf_coefficients
from .oscillators import Phase, duty_from_pwm, osc2_shape, pulse, saw
from .pitch import semitones_to_ratio


class Bank:
    def __init__(self, sr):
        self.sr = sr
        self.osc1 = Phase()
        self.osc2 = Phase()
        self.env = Envelope(sr)
        self.flt_env = Envelope(sr)
        self.lpf = LowPass(sr)
        self.note = 60
        self.velocity = 0.0
        self.gate = False
        self.noise_pos = 0
        self._last_coeffs = None

    @property
    def active(self):
        return self.env.active

    @property
    def level(self):
        return self.env.level

    def note_on(self, note, velocity, stolen, rng):
        """Start a note. ``stolen`` retriggers a still-sounding bank in place (phases, filter state
        and envelope level are kept, so there is no click)."""
        self.note = note
        self.velocity = velocity
        self.gate = True
        if stolen:
            self.env.note_on(keep_level=True)
            self.flt_env.level = 0.0
            self.flt_env.note_on()
            return
        self.noise_pos = int(rng.integers(0, NOISE_TABLE_LEN))
        self.osc1.phase = float(rng.random())
        self.osc2.phase = float(rng.random())
        self.env.note_on()
        self.flt_env.level = 0.0
        self.flt_env.note_on()
        self.lpf.reset()
        self._last_coeffs = None

    def note_off(self):
        self.gate = False
        self.env.note_off()
        self.flt_env.note_off()

    def force_release(self, seconds=FORCED_RELEASE_S):
        self.gate = False
        self.env.note_off(release_s=seconds)
        self.flt_env.note_off()

    def panic(self):
        self.gate = False
        for e in (self.env, self.flt_env):
            e.stage = IDLE
            e.level = 0.0

    def _osc1_signal(self, t, dt, p):
        """Return ``(audible, modulator)``. Layering adds the two waves (louder than either alone);
        the modulator is the layer scaled back to peak 1 so the modulation depth does not change."""
        saw_on, sq_on = p["osc1_saw"], p["osc1_square"]
        if saw_on and sq_on:
            # Juno-style layering: the pulse is high at the top of the saw's rising ramp, so the two add.
            # (A pulse that is high while the ramp is low would cancel part of the saw and sound quieter.)
            duty = duty_from_pwm(p["osc1_pwm"])
            layer = saw(t, dt) + pulse(np.mod(t + duty, 1.0), dt, duty)
            return layer, 0.5 * layer
        if saw_on:
            w = saw(t, dt)
            return w, w
        if sq_on:
            w = pulse(t, dt, duty_from_pwm(p["osc1_pwm"]))
            return w, w
        silent = np.zeros(len(t))
        return silent, silent

    def _osc2_signal(self, n, t1, f1, f2, mod, p):
        sr = self.sr
        dt2 = f2 / sr
        duty = duty_from_pwm(p["osc2_pwm"])
        wave = p["osc2_wave"]
        mode = p["mod_mode"]
        if mode == "SYNC":
            ratio = f2 / f1 if f1 > 0.0 else 1.0
            t2 = np.mod(t1 * ratio, 1.0)
            self.osc2.phase = float(np.mod((t1[-1] + f1 / sr) * ratio, 1.0))
            return osc2_shape(wave, t2, dt2, duty)
        t2 = self.osc2.advance(f2, sr, n)
        if mode == "FM":
            t2 = np.mod(t2 + mod * FM_INDEX_MAX, 1.0)
        sec = osc2_shape(wave, t2, dt2, duty)
        if mode == "AM":
            sec = sec * (0.5 + 0.5 * mod)
        elif mode == "RING":
            sec = sec * mod
        return sec

    def _noise_chunk(self, n, color):
        tbl = noise.table(color)
        size = len(tbl)
        pos = self.noise_pos % size
        end = pos + n
        if end <= size:
            chunk = tbl[pos:end]
        else:
            chunk = np.take(tbl, np.arange(pos, end), mode="wrap")
        self.noise_pos = end % size
        return chunk

    def _coeffs(self, p, env_mean):
        octaves = 0.0
        if p["flt_amount"]:
            octaves += p["flt_amount"] * FLT_ENV_OCTAVES * env_mean
        if p["keytrack"]:
            octaves += p["keytrack"] * (self.note - 60) / 12.0
        if p["vel_cutoff"]:
            octaves += p["vel_cutoff"] * FLT_VEL_OCTAVES * (self.velocity - 0.5)
        cutoff = min(max(p["cutoff"] * 2.0 ** octaves, LPF_MIN_HZ), 0.45 * self.sr)
        if cutoff >= LPF_MAX_HZ / 1.01:
            return None
        return lpf_coefficients(cutoff, p["resonance"], self.sr)

    def render(self, n, p, base_freq, extra_cents):
        sr = self.sr
        self.env.set_shape(p["amp_attack"], p["amp_decay"], p["amp_sustain"], p["amp_release"])
        self.flt_env.set_shape(p["flt_attack"], p["flt_decay"], p["flt_sustain"], p["flt_release"])
        freq = base_freq * 2.0 ** (extra_cents / 1200.0)
        limit = 0.45 * sr
        f1 = min(freq * (0.5 if p["osc1_octave_down"] else 1.0), limit)
        f2 = min(freq * semitones_to_ratio(p["osc2_coarse"], p["osc2_fine"])
                 * (2.0 if p["osc2_octave_up"] else 1.0), limit)
        t1 = self.osc1.advance(f1, sr, n)
        audible, mod = self._osc1_signal(t1, f1 / sr, p)
        level2 = p["osc2_level"]
        mix = p["osc1_level"] * audible
        if level2 > 0.0:
            mix = mix + level2 * self._osc2_signal(n, t1, f1, f2, mod, p)
        else:
            self.osc2.advance(f2, sr, n)
        if p["noise_level"] > 0.0:
            mix = mix + p["noise_level"] * self._noise_chunk(n, p["noise_color"])
        env_mean = float(np.mean(self.flt_env.process(n)))
        coeffs = self._coeffs(p, env_mean)
        if coeffs is not None:
            mix = self.lpf.process(mix, coeffs)
            self._last_coeffs = coeffs
        else:
            # Bypassed: keep the filter state following the input so there is no click when it re-enters.
            self.lpf.process(mix, self._last_coeffs or lpf_coefficients(LPF_MAX_HZ, 0.0, self.sr))
        amp = AMP_SCALE * (0.3 + 0.7 * self.velocity)
        return mix * self.env.process(n) * amp
