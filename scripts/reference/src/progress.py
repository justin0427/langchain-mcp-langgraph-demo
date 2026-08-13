"""終端機即時狀態面板：顯示每個 Agent 元件目前做到哪裡。"""

from __future__ import annotations

from collections import OrderedDict
from contextlib import AbstractContextManager
from time import monotonic

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


STATUS_STYLE = {"pending": ("○ 等待中", "dim"), "done": ("✓ 完成", "green"), "failed": ("✗ 失敗", "red")}
SPINNER_FRAMES = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")


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
            ]
        )
        self.live = Live(self.render(), console=self.console, screen=True, refresh_per_second=12)

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

    def render(self) -> Panel:
        table = Table(expand=True, show_header=True, header_style="bold cyan")
        table.add_column("元件", ratio=3)
        table.add_column("狀態", width=12)
        table.add_column("目前動作", ratio=4)
        for label, state, detail in self.steps.values():
            if state == "running":
                status, style = f"{SPINNER_FRAMES[self.frame]} 處理中", "yellow"
            else:
                status, style = STATUS_STYLE[state]
            table.add_row(label, Text(status, style=style), detail)
        elapsed = int(monotonic() - self.started_at)
        return Panel(
            Group(
                Text(f"GitHub PR Review Agent  ·  已執行 {elapsed}s", style="bold white"),
                Text("處理中圖示持續跳動代表程式仍在工作。", style="dim"),
                table,
            ),
            border_style="blue",
            title="即時執行狀態",
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
