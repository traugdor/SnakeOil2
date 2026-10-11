"""Hybrid voice allocation: 6 playable (held) voices plus tail slots for released notes."""


def allocate(voices, playable, forced_release_s):
    """Pick the voice for a new note.

    Returns ``(voice, stolen, forced)``. First, held notes beyond ``playable - 1`` are force-released (oldest
    first), so the new note always fits among the playable voices. Then a free slot is used; if none is free the
    quietest releasing voice is stolen (voices that were not just force-released go first).
    """
    held = [v for v in voices if v.gate]
    forced = []
    while len(held) >= playable:
        oldest = min(held, key=lambda v: v.order)
        oldest.force_release(forced_release_s)
        held.remove(oldest)
        forced.append(oldest)
    for v in voices:
        if not v.active:
            return v, False, forced
    releasing = [v for v in voices if not v.gate]
    preferred = [v for v in releasing if v not in forced] or releasing
    return min(preferred, key=lambda v: (v.level, v.order)), True, forced
