from types import SimpleNamespace

from econhack import cli


def test_blocked_panel_returns_nonzero_exit_code(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli.sys, "argv", ["econhack", "run", "--model", "panel"])
    monkeypatch.setattr(cli.importlib, "import_module", lambda name: SimpleNamespace(run=lambda: {"status": "blocked"}))
    monkeypatch.setattr(cli, "snapshot", lambda: None)
    monkeypatch.setattr(cli, "record_status", lambda *args, **kwargs: None)
    written = []
    monkeypatch.setattr(cli, "write_json", lambda path, content: written.append(content))
    assert cli.main() == 1
    assert written[-1]["failed"] == ["panel"]
