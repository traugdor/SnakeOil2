import json

import pytest

from snakeoil2.dsp.params import PARAMS
from snakeoil2.patches import CURRENT_VERSION, INIT_NAME, PatchError, PatchStore, capture, resolve, validate_name


def test_capture_leaves_out_master_volume_and_limiter():
    v = capture(PARAMS.defaults())
    assert "master_volume" not in v and "limiter_on" not in v and "mix" in v


def test_resolve_fills_defaults_ignores_unknown_and_replaces_bad_values():
    values, warnings = resolve({"version": 1, "name": "x", "params": {
        "mix": 0.25, "bogus": 3, "detune": float("nan"), "a_mod_mode": "NOPE", "width": "wide",
        "master_volume": 0.1, "a_cutoff": 1e9}})
    d = PARAMS.defaults()
    assert values["mix"] == 0.25
    assert values["detune"] == d["detune"] and values["a_mod_mode"] == "OFF" and values["width"] == d["width"]
    assert values["a_cutoff"] == 20000.0
    assert values["master_volume"] == d["master_volume"]       # not stored, so ignored
    assert values["b_cutoff"] == d["b_cutoff"]
    assert len(warnings) >= 4


def test_resolve_refuses_newer_versions_and_garbage():
    with pytest.raises(PatchError):
        resolve({"version": CURRENT_VERSION + 1, "name": "x", "params": {}})
    for bad in (None, [], "x", {"version": 1}, {"version": 1, "params": []}, {"params": {}}):
        with pytest.raises(PatchError):
            resolve(bad)


@pytest.mark.parametrize("name", ["../evil", "a/b", "a\\b", "..", ".hidden", "", " ", "x" * 80, "CON", "nul",
                                  "com1", "LPT9", "a:b", "tab\there", "new\nline", "trailing."])
def test_hostile_names_are_rejected(name):
    with pytest.raises(PatchError):
        validate_name(name)


@pytest.mark.parametrize("name", ["Warm Pad", "bass_01", "Lead-2", "v1.5"])
def test_good_names_are_accepted(name):
    assert validate_name(name) == name


def test_save_load_roundtrip(tmp_path):
    s = PatchStore(tmp_path)
    vals = capture(dict(PARAMS.defaults(), mix=0.9, a_mod_mode="RING"))
    s.save("Mine", vals)
    assert "Mine" in s.names() and s.names()[0] == INIT_NAME
    got, warnings = s.load("Mine")
    assert got["mix"] == 0.9 and got["a_mod_mode"] == "RING" and not warnings
    data = json.loads((tmp_path / "Mine.json").read_text())
    assert data["version"] == CURRENT_VERSION and data["name"] == "Mine"


def test_init_is_read_only_and_loads_defaults(tmp_path):
    s = PatchStore(tmp_path)
    got, _ = s.load(INIT_NAME)
    assert got == resolve({"version": 1, "name": INIT_NAME, "params": {}})[0]
    for op in (lambda: s.save(INIT_NAME, {}), lambda: s.delete(INIT_NAME), lambda: s.rename(INIT_NAME, "x"),
               lambda: s.rename("x", INIT_NAME)):
        with pytest.raises(PatchError):
            op()


def test_rename_delete_and_missing(tmp_path):
    s = PatchStore(tmp_path)
    s.save("A", capture(PARAMS.defaults()))
    s.rename("A", "B")
    assert "B" in s.names() and "A" not in s.names()
    s.save("C", capture(PARAMS.defaults()))
    with pytest.raises(PatchError):
        s.rename("B", "C")                    # target exists
    s.delete("B")
    assert "B" not in s.names()
    with pytest.raises(PatchError):
        s.load("B")
    with pytest.raises(PatchError):
        s.delete("B")


def test_corrupt_file_is_an_error_not_a_crash(tmp_path):
    (tmp_path / "Bad.json").write_text("{not json")
    s = PatchStore(tmp_path)
    assert "Bad" in s.names()
    with pytest.raises(PatchError):
        s.load("Bad")


def test_files_with_unsafe_names_on_disk_are_not_listed(tmp_path):
    (tmp_path / "con.json").write_text("{}")
    (tmp_path / "ok.json").write_text(json.dumps({"version": 1, "name": "ok", "params": {}}))
    s = PatchStore(tmp_path)
    assert "ok" in s.names() and "con" not in s.names()


def test_last_used(tmp_path):
    s = PatchStore(tmp_path)
    assert s.last_used() == INIT_NAME
    s.save("Z", capture(PARAMS.defaults()))
    s.set_last_used("Z")
    assert PatchStore(tmp_path).last_used() == "Z"
    s.delete("Z")
    assert s.last_used() == INIT_NAME
