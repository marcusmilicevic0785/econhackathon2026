import json

import pytest

from econhack import common


def test_existing_raw_file_with_changed_hash_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "ROOT", tmp_path)
    monkeypatch.setattr(common, "RAW", tmp_path / "data" / "raw")
    common.RAW.mkdir(parents=True)
    source = common.RAW / "test.csv"
    source.write_text("altered\n")
    (tmp_path / "data" / "manifest.json").write_text(json.dumps({"data/raw/test.csv": {"sha256": "wrong"}}))
    with pytest.raises(ValueError, match="altered"):
        common.fetch("https://example.test/test.csv", "test.csv", "test", "test")


def test_credentials_are_removed_from_manifest_urls():
    url = common.public_url("https://example.test/data?get=NAME&key=secret&token=hidden")
    assert "secret" not in url and "hidden" not in url
    assert "get=NAME" in url


def test_profile_rejects_duplicate_join_keys(tmp_path, monkeypatch):
    import pandas as pd
    monkeypatch.setattr(common, "OUTPUTS", tmp_path)
    with pytest.raises(ValueError, match="duplicated"):
        common.profile(pd.DataFrame({"geoid": ["1", "1"]}), "sample", ["geoid"])


def test_redownload_cannot_silently_replace_pinned_source(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(common, "ROOT", tmp_path)
    monkeypatch.setattr(common, "RAW", tmp_path / "data" / "raw")
    common.RAW.mkdir(parents=True)
    (tmp_path / "data" / "manifest.json").write_text(json.dumps({"data/raw/pinned.csv": {"sha256": "original"}}))
    response = SimpleNamespace(content=b"changed source bytes\n", url="https://example.test/source", headers={}, raise_for_status=lambda: None)
    monkeypatch.setattr(common.requests, "get", lambda *args, **kwargs: response)
    monkeypatch.setattr(common.time, "sleep", lambda seconds: None)
    with pytest.raises(RuntimeError, match="changed from pinned checksum"):
        common.fetch("https://example.test/source", "pinned.csv", "source", "public")
    assert not (common.RAW / "pinned.csv").exists()
    assert json.loads((tmp_path / "data" / "manifest.json").read_text())["data/raw/pinned.csv"]["sha256"] == "original"
