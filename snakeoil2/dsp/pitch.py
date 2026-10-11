def midi_note_to_freq(note):
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def semitones_to_ratio(semitones, cents=0.0):
    return 2.0 ** ((semitones + cents / 100.0) / 12.0)
