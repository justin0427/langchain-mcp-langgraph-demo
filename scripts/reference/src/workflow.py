"""把 Node 與 Edge 組成 LangGraph，並依風險決定最後路徑。"""

from typing import Literal

from langgraph.graph import END, START, StateGraph

from .nodes import (
    collect_evidence_node,
    quality_review_node,
    security_review_node,
    test_impact_review_node,
    write_recommendation_node,
)
from .state import PullRequestState


def route_after_recommendation(
    state: PullRequestState,
) -> Literal["human_review", "merge_candidate"]:
    """條件 Edge：高風險必須交給人；其餘才列為可合併候選。"""
    return "human_review" if state["risk_level"] == "HIGH" else "merge_candidate"


def human_review_node(_: PullRequestState) -> dict:
    return {"outcome": "需要人工審查：此工具不會自行留言、合併或修改 GitHub 資料。"}


def merge_candidate_node(_: PullRequestState) -> dict:
    return {"outcome": "可考慮合併：仍應由 repository 維護者完成最終確認。"}


def build_workflow():
    """宣告 Node、平行 Edge 與條件 Edge，最後編譯成可執行的 Graph。"""
    builder = StateGraph(PullRequestState)
    builder.add_node("collect_evidence", collect_evidence_node)
    builder.add_node("quality_review", quality_review_node)
    builder.add_node("security_review", security_review_node)
    builder.add_node("test_impact_review", test_impact_review_node)
    builder.add_node("write_recommendation", write_recommendation_node, defer=True)
    builder.add_node("human_review", human_review_node)
    builder.add_node("merge_candidate", merge_candidate_node)

    # 先蒐集一次證據，再把同一份 evidence 分給三個平行審查 Node。
    builder.add_edge(START, "collect_evidence")
    builder.add_edge("collect_evidence", "quality_review")
    builder.add_edge("collect_evidence", "security_review")
    builder.add_edge("collect_evidence", "test_impact_review")
    builder.add_edge("quality_review", "write_recommendation")
    builder.add_edge("security_review", "write_recommendation")
    builder.add_edge("test_impact_review", "write_recommendation")
    # 彙整報告寫完後，依 risk_level 選擇人工審查或合併候選。
    builder.add_conditional_edges("write_recommendation", route_after_recommendation)
    builder.add_edge("human_review", END)
    builder.add_edge("merge_candidate", END)
    return builder.compile()
