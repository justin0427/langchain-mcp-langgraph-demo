"""課堂輔助腳本的課前／課堂檢查分界。"""

from scripts import lab_helper


def test_preclass_does_not_check_github_mcp_or_token(monkeypatch) -> None:
    called: list[str] = []

    for name, (label, _) in lab_helper.CHECKS.items():
        monkeypatch.setitem(
            lab_helper.CHECKS,
            name,
            (label, lambda current=name: called.append(current)),
        )

    lab_helper.run_checks("preclass")

    assert called == ["paths", "setup", "ollama"]
    assert "env" not in called
    assert "mcp" not in called


def test_ollama_check_accepts_any_downloaded_model_without_env(
    monkeypatch, tmp_path, capsys
) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self):
            return b'{"models":[{"name":"student-choice:latest"}]}'

    monkeypatch.setattr(lab_helper, "ROOT", tmp_path)
    monkeypatch.setattr(lab_helper, "urlopen", lambda *_args, **_kwargs: FakeResponse())
    monkeypatch.setattr(
        lab_helper.json,
        "load",
        lambda _response: {"models": [{"name": "student-choice:latest"}]},
    )

    lab_helper.check_ollama()

    assert "偵測到 1 個可用模型" in capsys.readouterr().out
