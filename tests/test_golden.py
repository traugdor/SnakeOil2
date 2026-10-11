import json
import pathlib

import numpy as np
import pytest

from tests.golden_scenarios import SCENARIOS
from tests.scenario import render_scenario

GOLDEN = pathlib.Path(__file__).parent / "golden"


def test_every_scenario_has_golden_files_and_no_orphans():
    names = {p.name[:-len(".f32")] for p in GOLDEN.glob("*.f32")}
    assert names == set(SCENARIOS)


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_scenario_matches_golden(name):
    sc = SCENARIOS[name]
    stored = json.loads((GOLDEN / (name + ".scenario.json")).read_text())
    assert stored == json.loads(json.dumps(sc)), "scenario changed: rerun tools/make_golden.py on purpose"
    expect = np.fromfile(GOLDEN / (name + ".f32"), dtype="<f4").reshape(-1, 2)
    got = render_scenario(sc)
    assert got.shape == expect.shape
    assert np.allclose(got, expect, atol=1e-5)


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_scenario_is_audible_finite_and_in_range(name):
    got = render_scenario(SCENARIOS[name])
    assert np.all(np.isfinite(got)) and np.abs(got).max() <= 1.0 and np.abs(got).max() > 1e-4
