from rich.console import Console

from src.progress import ReviewDashboard


def render_text(dashboard: ReviewDashboard) -> str:
    console = Console(record=True, width=100, color_system=None)
    console.print(dashboard.render())
    return console.export_text()


def test_dashboard_renders_complete_graph_and_active_parallel_nodes():
    dashboard = ReviewDashboard()
    dashboard.update("evidence", "done", "蒐證完成")
    dashboard.update("quality", "running", "分析程式品質")
    dashboard.update("security", "running", "分析資安風險")
    dashboard.update("tests", "running", "分析測試影響")

    output = render_text(dashboard)

    assert "collect_evidence" in output
    assert "quality_review" in output
    assert "security_review" in output
    assert "test_impact_review" in output
    assert "write_recommendation" in output
    assert "human_review" in output
    assert "merge_candidate" in output
    assert output.count("執行中") >= 3


def test_dashboard_marks_unused_branch_as_skipped():
    dashboard = ReviewDashboard()
    dashboard.update("route", "done", "LOW RISK → merge_candidate")
    dashboard.update("human_review", "skipped", "本次未走此分支")
    dashboard.update("merge_candidate", "running", "低風險 PR 進入合併候選")

    output = render_text(dashboard)

    assert "未走此分支" in output
    assert "merge_candidate" in output
