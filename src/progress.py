"""終端機即時狀態面板：顯示每個 Agent 元件目前做到哪裡。"""

from __future__ import annotations

from collections import OrderedDict
from contextlib import AbstractContextManager
from time import monotonic

from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


STATUS_STYLE = {
    "pending": ("○ 等待中", "grey50"),
    "done": ("✓ 完成", "bright_green"),
    "failed": ("✗ 失敗", "bright_red"),
    "skipped": ("— 未走此分支", "grey50"),
}
SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
NODE_LABELS = {
    "evidence": "collect_evidence",
    "quality": "quality_review",
    "security": "security_review",
    "tests": "test_impact_review",
    "summary": "write_recommendation",
    "route": "conditional edge",
    "human_review": "human_review",
    "merge_candidate": "merge_candidate",
    "end": "END",
}


def supports_full_screen(console: Console) -> bool:
    """只在支援 alternate screen 的終端機使用全螢幕動畫。

    Windows Terminal 與新版 PowerShell 可以使用；舊版 Windows Console 則改用
    Rich 的一般 Live 模式，避免畫面閃爍、亂碼或結束後看不到輸出。
    """
    return bool(console.is_terminal and not getattr(console, "legacy_windows", False))


class ReviewDashboard(AbstractContextManager["ReviewDashboard"]):
    """以 Rich Live 在終端機顯示即時 PR 審查狀態。"""

    def __init__(self) -> None:
        self.console = Console()
        self.started_at = monotonic()
        self.frame = 0
        self.steps: OrderedDict[str, tuple[str, str, str]] = OrderedDict(
            [
                ("mcp_access", ("GitHub MCP：PR 存取檢查", "pending", "尚未驗證")),
                ("evidence", ("LangChain：蒐集 PR 證據", "pending", "等待 MCP 驗證")),
                ("quality", ("LangGraph Node：程式品質", "pending", "等待證據")),
                ("security", ("LangGraph Node：資安風險", "pending", "等待證據")),
                ("tests", ("LangGraph Node：測試影響", "pending", "等待證據")),
                ("summary", ("LangGraph Node：彙整建議", "pending", "等待平行審查")),
                ("route", ("LangGraph Edge：最終分流", "pending", "等待風險判定")),
                ("human_review", ("LangGraph Node：人工審查", "pending", "等待條件分流")),
                ("merge_candidate", ("LangGraph Node：合併候選", "pending", "等待條件分流")),
                ("end", ("LangGraph：END", "pending", "等待工作流完成")),
            ]
        )
        self.live = Live(
            self.render(),
            console=self.console,
            screen=supports_full_screen(self.console),
            refresh_per_second=12,
        )

    def __enter__(self) -> "ReviewDashboard":
        self.live.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.live.stop()

    def update(self, key: str, state: str, detail: str) -> None:
        label, _, _ = self.steps[key]
        self.steps[key] = (label, state, detail)
        self.live.update(self.render())

    def tick(self) -> None:
        """讓 spinner 與經過秒數持續變化，不會像程式卡住。"""
        self.frame = (self.frame + 1) % len(SPINNER_FRAMES)
        self.live.update(self.render())

    def _state(self, key: str) -> str:
        return self.steps[key][1]

    def _status(self, state: str) -> tuple[str, str]:
        if state == "running":
            return f"{SPINNER_FRAMES[self.frame]} 執行中", "bold bright_yellow"
        return STATUS_STYLE[state]

    def _node(self, key: str) -> Panel:
        state = self._state(key)
        status, style = self._status(state)
        return Panel(
            Align.center(Text(NODE_LABELS[key], justify="center", style=style), vertical="middle"),
            title=status,
            border_style=style,
            height=3,
            padding=(0, 1),
        )

    def _connector(self, keys: tuple[str, ...], glyph: str) -> Align:
        states = [self._state(key) for key in keys]
        if "failed" in states:
            style = "bright_red"
        elif "running" in states:
            style = "bold bright_yellow"
        elif all(state in {"done", "skipped"} for state in states):
            style = "bright_green"
        else:
            style = "grey50"
        # 多行連接線要逐行置中；否則只有一個 ▼ 的第二行會黏在長橫線左側。
        return Align.center(Text(glyph, style=style, justify="center"))

    def _row(self, keys: tuple[str, ...]) -> Table:
        row = Table.grid(expand=True, padding=(0, 1))
        for _ in keys:
            row.add_column(ratio=1)
        row.add_row(*(self._node(key) for key in keys))
        return row

    def _graph(self) -> RenderableType:
        graph = Table.grid(expand=True, padding=0)
        graph.add_column(ratio=1)
        graph.add_row(Align.center(Panel("START", border_style="bright_green", width=22)))
        graph.add_row(self._connector(("evidence",), "│\n▼"))
        graph.add_row(Align.center(self._node("evidence")))
        graph.add_row(self._connector(("quality", "security", "tests"), "┌──────────────┼──────────────┐\n▼              ▼              ▼"))
        graph.add_row(self._row(("quality", "security", "tests")))
        graph.add_row(self._connector(("quality", "security", "tests"), "└──────────────┼──────────────┘\n▼"))
        graph.add_row(Align.center(self._node("summary")))
        graph.add_row(self._connector(("route",), "│\n▼"))
        graph.add_row(Align.center(self._node("route")))
        graph.add_row(self._connector(("human_review", "merge_candidate"), "┌────────────────────┴────────────────────┐\n▼                                         ▼"))
        graph.add_row(self._row(("human_review", "merge_candidate")))
        graph.add_row(self._connector(("end",), "└────────────────────┬────────────────────┘\n▼"))
        graph.add_row(Align.center(self._node("end")))
        return graph

    def _activity(self) -> Panel:
        active = [value for value in self.steps.values() if value[1] in {"running", "failed"}]
        if not active:
            completed = [value for value in self.steps.values() if value[1] == "done"]
            active = [completed[-1] if completed else next(iter(self.steps.values()))]
        lines = Text()
        for index, (label, state, detail) in enumerate(active):
            status, style = self._status(state)
            if index:
                lines.append("\n")
            lines.append(f"{status}  {label} — ", style=style)
            lines.append(detail, style="white")
        return Panel(lines, title="目前階段", border_style="bright_yellow" if any(item[1] == "running" for item in active) else "blue")

    def render(self) -> Panel:
        elapsed = int(monotonic() - self.started_at)
        return Panel(
            Group(
                Text(f"GitHub PR Review Agent  ·  已執行 {elapsed}s", style="bold white"),
                Text("黃色＝目前執行　綠色＝完成　紅色＝失敗　灰色＝等待／未走分支", style="dim"),
                self._activity(),
                Panel(self._graph(), title="LangGraph 工作流", border_style="cyan"),
            ),
            border_style="blue",
            title="即時 LangGraph 執行狀態",
        )


_dashboard: ReviewDashboard | None = None


def set_dashboard(dashboard: ReviewDashboard | None) -> None:
    """讓 LangGraph Node 可更新本次執行的面板。"""
    global _dashboard
    _dashboard = dashboard


def update_step(key: str, state: str, detail: str) -> None:
    """沒有 Dashboard 時保持靜默，讓單元測試不受終端機介面影響。"""
    if _dashboard is not None:
        _dashboard.update(key, state, detail)
