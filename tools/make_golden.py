import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from tests.golden_scenarios import SCENARIOS  # noqa: E402
from tests.scenario import render_scenario  # noqa: E402

out = pathlib.Path(__file__).resolve().parents[1] / "tests" / "golden"
out.mkdir(exist_ok=True)
for name, sc in SCENARIOS.items():
    audio = render_scenario(sc)
    audio.astype("<f4").tofile(out / (name + ".f32"))
    (out / (name + ".scenario.json")).write_text(json.dumps(sc, indent=1), encoding="utf-8")
    print(name, audio.shape)
