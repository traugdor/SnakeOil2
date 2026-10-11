import numpy as np

from snakeoil2.dsp.effects import EffectChain

SR = 44100


def impulse(n=SR // 2):
    x = np.zeros((2, n))
    x[:, 0] = 1.0
    return x


def test_disabled_chain_is_a_passthrough():
    x = np.random.default_rng(1).standard_normal((2, 1000))
    assert np.array_equal(EffectChain(SR).process(x), x)


def test_chain_has_no_bitcrush():
    c = EffectChain(SR)
    assert c.order == ["chorus", "delay", "reverb"] and not hasattr(c, "bitcrush")


def test_delay_echoes_at_the_set_time():
    c = EffectChain(SR)
    c.delay.enabled = True
    c.delay.set_time_ms(100.0)
    y = c.process(impulse())
    echo = int(0.1 * SR)
    assert abs(y[0, echo]) > 0.1 and abs(y[0, echo // 2]) < 1e-9


def test_reverb_rings_after_the_input_stops():
    c = EffectChain(SR)
    c.reverb.enabled = True
    y = c.process(impulse(SR))
    assert np.abs(y[:, SR // 2:]).max() > 1e-4


def test_delay_extremes_stay_finite():
    c = EffectChain(SR)
    c.delay.enabled = True
    c.delay.set_time_ms(1.0)
    c.delay.set_feedback(0.95)
    y = c.process(np.random.default_rng(2).standard_normal((2, 20000)) * 0.1)
    assert np.all(np.isfinite(y)) and np.abs(y).max() < 100


def test_effects_are_block_size_invariant():
    def run(sizes):
        c = EffectChain(SR)
        c.chorus.enabled = c.delay.enabled = c.reverb.enabled = True
        c.delay.set_pingpong(True)
        x = np.random.default_rng(3).standard_normal((2, sum(sizes))) * 0.2
        out, pos = [], 0
        for n in sizes:
            out.append(c.process(x[:, pos:pos + n])); pos += n
        return np.concatenate(out, axis=1)

    assert np.allclose(run([2048]), run([256] * 8), atol=1e-6)
