from src.workflow import route_after_recommendation


def test_high_risk_routes_to_human_review():
    assert route_after_recommendation({"risk_level": "HIGH"}) == "human_review"


def test_low_risk_routes_to_merge_candidate():
    assert route_after_recommendation({"risk_level": "LOW"}) == "merge_candidate"
