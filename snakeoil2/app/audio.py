"""Audio output: a sounddevice stream whose callback drains the event queue and renders the engine."""
import time

import numpy as np

from .events import apply_event


def render_callback(engine, queue, outdata, frames, now):
    """Fill ``outdata`` (frames x channels). Never raises: any failure becomes silence."""
    try:
        for event in queue.drain():
            apply_event(engine, event)
        block = engine.process(frames, now)
        channels = outdata.shape[1]
        if channels == 1:
            outdata[:, 0] = block.mean(axis=1)
        else:
            outdata[:, :2] = block
            if channels > 2:
                outdata[:, 2:] = 0.0
    except Exception:
        outdata[:] = 0.0


class AudioOutput:
    """Output stream. ``info`` is the dict from ``audio_backend.resolve_output`` (or None for the default)."""

    def __init__(self, engine, queue, info=None, blocksize=0):
        self.engine, self.queue = engine, queue
        self.info = info or {"device": None, "extra_settings": None}
        self.blocksize = blocksize
        self.xruns = 0
        self._stream = None

    def _callback(self, outdata, frames, time_info, status):
        if status.output_underflow:
            self.xruns += 1
        render_callback(self.engine, self.queue, outdata, frames, time.perf_counter())

    def start(self):
        import sounddevice as sd

        self._stream = sd.OutputStream(
            samplerate=self.engine.sr, blocksize=self.blocksize, device=self.info["device"], channels=2,
            dtype="float32", latency="low", callback=self._callback, extra_settings=self.info["extra_settings"])
        self._stream.start()

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
