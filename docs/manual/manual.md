# SnakeOil2 user manual

SnakeOil2 is a polyphonic synthesizer with **two complete oscillator banks** in every voice. You play it from a
MIDI keyboard. Each bank has its own oscillators, noise, filter and envelopes; a Mix control blends the banks, and
Detune and Width set how far apart they sound.

## 1. The sound path

Every note plays on **Bank A** and **Bank B** at once:

```
OSC1 (saw / square) --> modulation --> OSC2 ---+
noise --------------------------------------+--> 12 dB low-pass --> amp envelope --> Bank volume
                          (filter envelope, key tracking, velocity, LFOs, mod matrix move the cutoff)
```

The two banks are then blended (Mix), pushed apart in pitch (Detune) and in the stereo field (Width), and run
through chorus, delay and reverb, then master volume, an optional auto limiter and a soft clipper.

## 2. A bank

### OSC1

- **Saw** and **Square** are two toggles. Switch on one, both (the square is added to the saw at half level, with its high part at the top of the saw so the two add) or neither (OSC1 is then
  silent, which is useful when you only want OSC2).
- **PWM** sets the pulse width of the square between 25% and 75% (0.5 is a plain square).
- **Sq Lvl** sets how much of the square is added when both Saw and Square are on (0-1, default 0.5, as in
  V1). At 0 you hear the plain saw. It has no effect when only one wave is on.
- **Level** sets how loud OSC1 is in the mix. OSC1 always acts as the modulator for OSC2, whatever its level.
- **Oct -1** plays OSC1 one octave down (on by default).

### OSC2

- **Wave** chooses one of four shapes: reverse saw, inverted triangle, sine, square.
- **PWM** (square only), **Level**, **Coarse** (-12..+12 semitones), **Fine** (+/-0.5 cent) and **Oct +1**
  (OSC2 one octave up, on by default).

### Modulation

One knob per bank chooses how OSC1 drives OSC2. The amount is always full.

| Mode | What you hear |
|---|---|
| OFF | OSC2 runs on its own. |
| FM | OSC1 phase-modulates OSC2: bright, metallic sidebands. |
| AM | OSC1 amplitude-modulates OSC2: tremolo that is fast enough to become a new timbre. The carrier is never fully silent (OSC2 stays at half level when OSC1 is silent). |
| RING | Ring modulation: OSC2 is silent whenever OSC1 is silent. |
| SYNC | Hard sync: every OSC1 cycle restarts OSC2, giving the classic sync sweep when you change OSC2 Coarse. |

With both OSC1 toggles off, FM leaves OSC2 untouched, AM halves it, RING silences it and SYNC still follows
OSC1's silent phase.

### Noise

A **Level** dial and a **Color** choice (white, pink, brown). The noise goes through the bank's filter and amp
envelope, so a short envelope gives percussive bursts.

### Filter

A 12 dB per octave resonant low-pass. **Cutoff** (20 Hz-20 kHz; 20 kHz means the filter is bypassed),
**Reso**, **Env Amt** (-1..+1: how far the filter envelope moves the cutoff, up to 6 octaves), **Key Trk**
(the cutoff follows the note, 1.00 = one octave per octave) and **Vel>Cut** (harder playing opens the filter).

### Envelopes

**Filter Env** and **Amp Env**, each with sliders A, D, S, R (attack 1 ms-5 s, decay 1 ms-5 s, sustain 0-1,
release 1 ms-10 s). The amp envelope also scales with velocity.

### Output

**Volume** is the bank's level into the blend.

## 3. Between the banks

- **Mix** crossfades equally loud: 0 is bank A only, 1 is bank B only, 0.5 is both.
- **Detune** (0-50 cents) lowers bank A and raises bank B by half the amount each.
- **Width** (0-1) pans bank A left and bank B right. At 0 both banks sit in the centre.

## 4. LFOs and the mod matrix

There are two LFOs, each with a **Rate** (0.05-20 Hz) and a **Wave** (sine, triangle, saw, square, random,
random-glide). An LFO has no output of its own: it moves something only when you route it in the **mod matrix**.

The matrix has eight rows: **Source | Scale | Destination**.

- **Sources:** Note Number (middle C is 0), LFO 1, LFO 2, Mod Wheel, Aftertouch.
- **Scale** runs from -100% to +100%.
- **Destinations** exist once per bank (prefixed `A:` or `B:`): OSC1 Level, PWM and Sq Level, OSC2 Level, Tune, Fine and
  PWM, Noise Level, Bank Volume, Cutoff, Resonance, Env Amount, Key Trk, Vel>Cut, the filter and amp envelope
  times, and **Pitch**. Global destinations: Mix, Detune, Width, Tempo, LFO 1 Rate, LFO 2 Rate, Chorus Depth,
  Delay Time, Feedback and Tone, Reverb Amount, Size and Damping.

**Scaling is relative.** The effective value is `value x (1 + sum of scale x source)`, limited to the control's
range. Cutoff at 1000 Hz with Mod Wheel +50% gives 1000 Hz with the wheel down and 1500 Hz fully up. A control
whose value is 0 stays 0 (OSC2 Level at 0 cannot be raised by the matrix), so give it a starting value first.

Two kinds of destination work differently:

- **Pitch** is added in semitones: +100% of a source moves the bank by 2 semitones. That is what makes vibrato
  possible even though Tune sits at 0.
- **LFO 1 / LFO 2 Rate** change the other LFO's speed by up to 2 octaves per 100%.

### Worked examples

**Vibrato on bank A.** Row 1: Source `LFO 1`, Scale `+15%`, Destination `A: Pitch`. Set LFO 1 to a sine at 5-6 Hz.
Bank B stays steady, which gives a gentle chorus-like beating against it.

**Mod wheel opens bank A's filter.** Set A's Cutoff to about 400 Hz. Row 1: Source `Mod Wheel`, Scale `+100%`,
Destination `A: Cutoff`. The wheel now sweeps the cutoff from 400 Hz to 800 Hz; raise the scale (or the base
cutoff) for a wider sweep.

## 5. Effects, tempo and voices

- **Chorus** (Depth), **Delay** (Time, Ping-pong, Feedback, Tone, Sync, Division) and **Reverb** (Amount, Size,
  Damping), each with its own on/off button, run in that order.
- **Tempo** is a manual BPM (40-240). A MIDI clock on any input overrides it for one second at a time; when the
  clock stops the manual tempo returns. With **Sync** on, the delay time follows the tempo and the **Division**.
- **Voices:** six notes can be held at once. A released note keeps ringing in one of twelve tail slots, so
  there are 18 voices in all. A seventh held note gives the oldest held note a very short fade-out. The six
  voice lights show held notes in green and ringing tails in amber; the readout shows how many tail slots are in
  use.

## 6. Patches

A patch is a saved sound: every control except master volume and the auto limiter. The toolbar has a patch box
(choosing a patch loads it), **Save**, **Save As...**, **Rename** and **Delete**. A `*` in the window title means
you changed something since loading or saving. **Init** is the factory sound and cannot be saved over, renamed or
deleted; use Save As... to keep a variation. Patch names may use letters, digits, spaces, `_`, `-` and `.`.

Patches are `*.json` files in the `patches` folder of the config directory (`%APPDATA%\snakeoil2` on Windows,
`~/.config/snakeoil2` elsewhere; `--config-dir` chooses another). Controls missing from a file load at their
factory value, so old patches keep working when controls are added.

## 7. MIDI

| Message | Action |
|---|---|
| Note on / off | Plays notes. Note on with velocity 0 counts as note off. |
| Velocity | Scales loudness and (with Vel>Cut) the filter. The **Velocity** switch plays everything at a fixed velocity. |
| Pitch wheel | Pitch bend, +/-2 semitones. |
| CC 1 | Mod wheel (a mod matrix source). |
| CC 64 | Sustain pedal: note-offs wait until the pedal lifts. |
| CC 120 / 121 / 123 | All sound off / reset controllers / all notes off. |
| Channel aftertouch | A mod matrix source. |
| MIDI clock, start, stop, continue | Tempo for the synced delay. |

Per-note (polyphonic) aftertouch is ignored. There is no MIDI learn: controls are changed in the window.

## 8. Master section

**Volume**, the **Velocity** switch and the **Auto Limiter**. The stereo meter shows the output level after the
soft clipper (green, yellow, red); **CLIP** lights when the signal reaches full scale before the clipper and stays
on briefly; click the meter to clear it. The limiter lowers the level at once when a peak would clip and keeps it
lowered until the sound has been silent for half a second, a patch is loaded, you switch the limiter, or you
click the **GR** readout. With the limiter on, the meter shows the limited signal.

## 9. Starting the program

```
snakeoil2                                  # GUI, all MIDI inputs
snakeoil2 --list                           # list MIDI inputs and audio outputs
snakeoil2 --input "Launchkey" --channel 1  # one MIDI port and channel
snakeoil2 --patch "Warm Pad" --no-gui      # no window, console only
snakeoil2 --hostapi WASAPI --device 3      # choose the audio output
```

On Windows the program prefers ASIO, then WASAPI, then WDM-KS, then the system default; use `--hostapi` or
`--device` to override.
