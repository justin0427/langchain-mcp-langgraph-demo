"""將最終 State 寫成可閱讀、可分享的 Markdown 審查報告。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .state import PullRequestState


def build_markdown_report(state: PullRequestState) -> str:
    """把 Graph 最後的 State 整理成一份 Markdown 報告。"""
    findings = "\n\n".join(state["findings"])
    return f"""# PR 合併前審查報告

- Repository：`{state['repository']}`
- Pull Request：`#{state['pull_number']}`
- 風險等級：`{state['risk_level']}`
- 產生時間：{datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')}

## LangChain 蒐集的 PR 證據

{state['evidence']}

## LangGraph 平行審查

{findings}

## 合併前建議

{state['recommendation']}

## 最終分流

{state['outcome']}
"""


def save_markdown_report(project_root: Path, state: PullRequestState) -> Path:
    """將報告存到 reports/，不覆蓋同一個 PR 的歷史結果。"""
    reports_dir = project_root / "reports"
    reports_dir.mkdir(exist_ok=True)
    safe_repository = state["repository"].replace("/", "-")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = reports_dir / f"{safe_repository}-pr-{state['pull_number']}-{timestamp}.md"
    report_path.write_text(build_markdown_report(state), encoding="utf-8")
    return report_path
