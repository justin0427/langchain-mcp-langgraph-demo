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


def test_ollama_check_verifies_the_course_cloud_model(monkeypatch, tmp_path, capsys) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

    requests = []
    monkeypatch.setattr(lab_helper, "ROOT", tmp_path)
    monkeypatch.setattr(
        lab_helper,
        "urlopen",
        lambda request, **_kwargs: (requests.append(request) or FakeResponse()),
    )
    monkeypatch.setattr(
        lab_helper.json,
        "load",
        lambda _response: {"message": {"content": "OK"}},
    )

    lab_helper.check_ollama()

    assert requests[0].full_url == "http://localhost:11434/api/chat"
    assert b'"model": "gemma4:cloud"' in requests[0].data
    assert "gemma4:cloud 可使用" in capsys.readouterr().out
