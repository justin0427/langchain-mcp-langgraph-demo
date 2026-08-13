"""LangGraph assembly and risk-based routing."""

from typing import Literal

from langgraph.graph import END, START, StateGraph

from .progress import update_step
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
    return "human_review" if state["risk_level"] == "HIGH" else "merge_candidate"


def human_review_node(_: PullRequestState) -> dict:
    update_step("route", "done", "HIGH RISK → 人工審查")
    return {"outcome": "需要人工審查：此工具不會自行留言、合併或修改 GitHub 資料。"}


def merge_candidate_node(_: PullRequestState) -> dict:
    update_step("route", "done", "LOW RISK → 可考慮合併")
    return {"outcome": "可考慮合併：仍應由 repository 維護者完成最終確認。"}


def build_workflow():
    builder = StateGraph(PullRequestState)
    builder.add_node("collect_evidence", collect_evidence_node)
    builder.add_node("quality_review", quality_review_node)
    builder.add_node("security_review", security_review_node)
    builder.add_node("test_impact_review", test_impact_review_node)
    builder.add_node("write_recommendation", write_recommendation_node, defer=True)
    builder.add_node("human_review", human_review_node)
    builder.add_node("merge_candidate", merge_candidate_node)

    builder.add_edge(START, "collect_evidence")
    builder.add_edge("collect_evidence", "quality_review")
    builder.add_edge("collect_evidence", "security_review")
    builder.add_edge("collect_evidence", "test_impact_review")
    builder.add_edge("quality_review", "write_recommendation")
    builder.add_edge("security_review", "write_recommendation")
    builder.add_edge("test_impact_review", "write_recommendation")
    builder.add_conditional_edges("write_recommendation", route_after_recommendation)
    builder.add_edge("human_review", END)
    builder.add_edge("merge_candidate", END)
    return builder.compile()
