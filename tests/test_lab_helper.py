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
