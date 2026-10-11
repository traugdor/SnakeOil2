# SnakeOil2

SnakeOil2 is a dual-bank polyphonic MIDI synthesizer: a Python prototype of a future VST3. Each of its 6 voices
plays two complete oscillator banks (own OSC1/OSC2, modulation, noise, 12 dB filter, filter and amp envelopes),
blended by Mix, Detune and Width. It reuses a lot of code from SnakeOil Synth V1.

## Features

- Two banks per voice. OSC1: saw/square toggles. OSC2: reverse saw, inverted triangle, sine or PWM square.
  Per-bank modulation OFF / FM / AM / RING / SYNC (always full amount).
- 6 playable voices plus 12 tail slots for releasing notes (18 voices in all).
- Per-bank 12 dB resonant low-pass with filter envelope, key tracking and velocity; per-bank amp envelope and noise.
- Two LFOs and an 8-row mod matrix with per-bank destinations (the LFOs only act through the matrix).
- Chorus, ping-pong delay with tempo sync / MIDI clock, reverb; auto limiter; level meter; voice LEDs.
- JSON patches. Pitch bend, sustain pedal, mod wheel, aftertouch.

See `docs/manual/manual.md` for the user manual.

## Install

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[app,dev]"     # Windows; use .venv/bin/python elsewhere
```

On Linux the PortAudio system library is also needed (`sudo apt install libportaudio2`).

## Run

```bash
snakeoil2                      # GUI, all MIDI inputs
snakeoil2 --list               # MIDI inputs and audio outputs
snakeoil2 --input NAME --channel 1 --patch NAME --config-dir PATH --no-gui
snakeoil2 --hostapi ASIO|WASAPI|... --device NAME_OR_INDEX
```

## Tests

```bash
.venv/Scripts/python -m pytest -q                          # everything
.venv/Scripts/python -m pytest tests/test_bank.py -v       # one file
.venv/Scripts/python -m pytest tests/test_bank.py::test_filter_darkens_and_20k_is_bypass   # one test
```

GUI tests run headless (`QT_QPA_PLATFORM=offscreen` is set by the tests).

## Architecture

- `snakeoil2/dsp/` is a pure core (numpy/scipy only, no Qt, audio or MIDI libraries, no wall-clock time, no
  unseeded randomness). Its single entry point is `Engine`: `note_on / note_off / cc / pitch_bend / aftertouch /
  set_param / process(n, now) -> (n, 2) float32`. It is single-threaded and lock-free.
- `snakeoil2/app/` is the shell: the PySide6 GUI, the `sounddevice` stream and the `mido` MIDI input. Threads
  reach the engine only through an `EventQueue` that the audio callback drains at the start of each block.
- `snakeoil2/dsp/params.py` is a declarative parameter table that drives the engine, the patches and the GUI.
  `python tools/export_params.py` dumps it as JSON for a later C++ port.
- `tests/golden/` holds rendered audio for 26 scenarios. Regenerate with `python tools/make_golden.py` only when
  you change the sound on purpose.

## Performance

On the development machine (44.1 kHz, 256-sample blocks) six held notes with FM on in both banks and all three
effects on take about 2.9 ms per block against a 5.8 ms budget.

## License

Copyright (C) 2026 Joel Trauger.

SnakeOil2 is free software released under the GNU Affero General Public License v3.0; see the `LICENSE` file.
