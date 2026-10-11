"""Band-limited oscillator waveforms (PolyBLEP / PolyBLAMP) and a phase accumulator.

All wave functions take ``t`` (float64 phases in [0, 1)) and ``dt = freq / sr``.
"""
import numpy as np

from .constants import DUTY_MAX, DUTY_MIN

OSC2_WAVE_NAMES = ("reverse saw", "inverted triangle", "sine", "square")


def poly_blep(t, dt):
    d = dt if dt > 1e-9 else 1e-9
    a = np.maximum(1.0 - t / d, 0.0)
    b = np.maximum(1.0 + (t - 1.0) / d, 0.0)
    return b * b - a * a


def _blamp(t, corner, dt):
    """Residual of a unit slope change at phase ``corner`` (in units of one sample's slope change / 6)."""
    x = (np.mod(t - corner + 0.5, 1.0) - 0.5) / dt
    ax = np.abs(x)
    return np.where(ax < 1.0, (1.0 - ax) ** 3, 0.0)


def saw(t, dt):
    return 2.0 * t - 1.0 - poly_blep(t, dt)


def reverse_saw(t, dt):
    return -saw(t, dt)


def sine(t, dt=0.0):
    return np.sin(2.0 * np.pi * t)


def pulse(t, dt, duty):
    """Band-limited pulse, DC removed and scaled to peak 1, for duty 0.25-0.75."""
    duty = min(max(duty, DUTY_MIN), DUTY_MAX)
    s = np.where(t < duty, 1.0, -1.0) + poly_blep(t, dt) - poly_blep(np.mod(t - duty, 1.0), dt)
    dc = 2.0 * duty - 1.0
    return (s - dc) / (1.0 + abs(dc))


def inverted_triangle(t, dt):
    """Triangle that starts at 0 and falls: minimum at t = 0.25, maximum at t = 0.75."""
    d = dt if dt > 1e-9 else 1e-9
    u = np.mod(t + 0.25, 1.0)
    naive = 4.0 * np.abs(u - 0.5) - 1.0
    k = 8.0 * d / 6.0
    return naive + k * _blamp(t, 0.25, d) - k * _blamp(t, 0.75, d)


def duty_from_pwm(pwm):
    """PWM control 0-1 -> duty cycle 0.25-0.75 (0.5 = plain square)."""
    p = min(max(float(pwm), 0.0), 1.0)
    return DUTY_MIN + (DUTY_MAX - DUTY_MIN) * p


def osc2_shape(wave, t, dt, duty):
    if wave == "reverse saw":
        return reverse_saw(t, dt)
    if wave == "inverted triangle":
        return inverted_triangle(t, dt)
    if wave == "sine":
        return sine(t)
    if wave == "square":
        return pulse(t, dt, duty)
    raise ValueError("unknown OSC2 wave: %r" % (wave,))


class Phase:
    """Phase accumulator: ``advance`` returns the phases of the next ``n`` samples."""

    def __init__(self):
        self.phase = 0.0

    def advance(self, freq, sr, n):
        inc = freq / sr
        t = np.mod(self.phase + inc * np.arange(n, dtype=np.float64), 1.0)
        self.phase = float(np.mod(self.phase + inc * n, 1.0))
        return t
