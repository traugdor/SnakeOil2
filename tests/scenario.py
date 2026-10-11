import numpy as np

from snakeoil2.dsp.engine import Engine


def render_scenario(sc):
    block = sc.get("block", 256)
    e = Engine(block_size=block, seed=sc.get("seed", 1))
    for pid, value in sc.get("params", {}).items():
        e.set_param(pid, value)
    blocks = int(round(sc["seconds"] * e.sr / block))
    events = sorted(sc.get("events", []), key=lambda ev: ev["t"])
    out, i = [], 0
    for b in range(blocks):
        while i < len(events) and int(events[i]["t"] * e.sr / block) <= b:
            ev = events[i]; i += 1
            kind = ev["type"]
            if kind == "note_on":
                e.note_on(ev["note"], ev.get("velocity", 100))
            elif kind == "note_off":
                e.note_off(ev["note"])
            elif kind == "cc":
                e.cc(ev["control"], ev["value"])
            elif kind == "bend":
                e.pitch_bend(ev["value"])
            elif kind == "aftertouch":
                e.aftertouch(ev["value"])
            else:
                raise ValueError(kind)
        out.append(e.process(block, now=0.0))
    return np.concatenate(out)
