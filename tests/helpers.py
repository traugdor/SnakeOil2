import numpy as np


def alias_power(x, f, sr):
    """Power of ``x`` outside the harmonics of ``f``. ``len(x)`` must be ``sr`` samples and ``f`` an integer Hz
    so the signal is exactly periodic in the window and every harmonic falls on one FFT bin."""
    assert len(x) == sr and float(f).is_integer()
    spec = np.abs(np.fft.rfft(x)) ** 2
    harm = np.zeros(len(spec), dtype=bool)
    for k in range(0, len(spec), int(f)):
        harm[k] = True
    return float(spec[~harm].sum())


def naive_phase(f, sr):
    inc = f / sr
    return np.mod(inc * np.arange(sr, dtype=np.float64), 1.0), inc
