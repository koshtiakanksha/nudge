from app.ml.evaluation.recommendation_eval import _score_grounding, _score_agreement, _extract_numbers
from app.ml.evaluation.recommendation_scenarios import generate_budget_scenarios
from app.services.claude_service import claude_service


def test_scenarios_have_expected_shape():
    scenarios = generate_budget_scenarios()
    assert len(scenarios) >= 5
    for s in scenarios:
        assert "monthly_income" in s and "spending_by_category" in s


def test_extract_numbers_handles_commas_and_decimals():
    assert _extract_numbers("Reserved $1,200.50 of $4,000") == [1200.50, 4000.0]


def test_grounding_flags_hallucinated_category():
    result = {"allocations": {"Groceries": {"allocated": 100, "is_non_neg": False},
                               "MadeUpCategory": {"allocated": 50, "is_non_neg": False}},
              "reasoning": "Allocated based on history."}
    scores = _score_grounding(result, spendable=150, buffer_reserved=50,
                               spending_by_category={"Groceries": 300}, non_negotiables=[])
    assert scores["category_grounding"] == 0.5  # 1 of 2 categories hallucinated


def test_grounding_detects_over_budget_allocation():
    result = {"allocations": {"Groceries": {"allocated": 500, "is_non_neg": False}},
              "reasoning": ""}
    scores = _score_grounding(result, spendable=150, buffer_reserved=50,
                               spending_by_category={"Groceries": 300}, non_negotiables=[])
    assert scores["within_budget"] is False


def test_grounding_rewards_reasoning_that_cites_real_numbers():
    result = {"allocations": {}, "reasoning": "Reserved $50.00 of the $150.00 spendable amount."}
    scores = _score_grounding(result, spendable=150, buffer_reserved=50,
                               spending_by_category={}, non_negotiables=[])
    assert scores["reasoning_cites_real_numbers"] == 1.0


def test_grounding_empty_allocation_against_true_cold_start_is_correct():
    # No historical data, no non-negotiables -- empty allocations here is
    # the honest answer, not a failure. This was the bug: the old mock
    # used to hallucinate a fallback category set in exactly this case.
    result = {"allocations": {}, "reasoning": "No spending history yet."}
    scores = _score_grounding(result, spendable=4250, buffer_reserved=750,
                               spending_by_category={}, non_negotiables=[])
    assert scores["category_grounding"] == 1.0


def test_grounding_empty_allocation_when_data_existed_is_a_failure():
    result = {"allocations": {}, "reasoning": ""}
    scores = _score_grounding(result, spendable=150, buffer_reserved=50,
                               spending_by_category={"Groceries": 300}, non_negotiables=[])
    assert scores["category_grounding"] == 0.0


def test_agreement_needs_at_least_two_shared_categories():
    result = {"allocations": {"Groceries": {"allocated": 100}}}
    assert _score_agreement(result, {"Groceries": 300}) is None


def test_mock_budget_is_grounded_by_construction():
    # Sanity check against the real service in its default (mock) mode:
    # the rule-based fallback should never hallucinate a category.
    scenario = generate_budget_scenarios()[0]
    was_mock = claude_service.mock_mode
    claude_service.mock_mode = True
    try:
        result = claude_service.generate_budget(**scenario)
        spend_ceiling = scenario["monthly_income"] * (1 - scenario["buffer_pct"])
        buffer_reserved = round(scenario["monthly_income"] * scenario["buffer_pct"], 2)
        spendable = round(spend_ceiling - buffer_reserved, 2)
        scores = _score_grounding(
            result, spendable, buffer_reserved,
            scenario["spending_by_category"], scenario["non_negotiables"],
        )
        assert scores["category_grounding"] == 1.0
        assert scores["within_budget"] is True
    finally:
        claude_service.mock_mode = was_mock
