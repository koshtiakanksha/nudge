"""
Scenario simulation service.

Answers "what if" questions (rent increases, income drops, an
unexpected one-time expense) by re-running compute_budget_allocation_v2
with a modified input and diffing the result against the current
allocation. No new allocation logic lives here -- this is composition
of what budget_engine.py and category_role_service already provide.
Every dollar amount traces back to the same deterministic engine used
everywhere else in the budgeting flow; nothing here invents a number
Claude wouldn't be trusted to invent either.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.budget_engine import compute_budget_allocation_v2, diff_allocations

DEFAULT_BUFFER_PCT = 0.10


@dataclass
class ScenarioResult:
    scenario: str
    income_before: float
    income_after: float
    spendable_before: float
    spendable_after: float
    before_allocations: dict
    after_allocations: dict
    changes: list
    risk_level: str  # "none" | "tight" | "over_budget"
    summary: str

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "income_before": round(self.income_before, 2),
            "income_after": round(self.income_after, 2),
            "spendable_before": round(self.spendable_before, 2),
            "spendable_after": round(self.spendable_after, 2),
            "before_allocations": self.before_allocations,
            "after_allocations": self.after_allocations,
            "changes": self.changes,
            "risk_level": self.risk_level,
            "summary": self.summary,
        }


def _spendable(income_estimate: float, buffer_pct: float) -> tuple[float, float]:
    buffer_reserved = round(income_estimate * buffer_pct, 2) if income_estimate else 0.0
    spendable = max(round(income_estimate - buffer_reserved, 2), 0.0)
    return spendable, buffer_reserved


def _risk_level(before_result, after_result) -> str:
    """
    "over_budget" -- some role tier (fixed_essential, variable_essential,
    or savings_or_debt) didn't fit before but does now (this scenario is
    what broke it). Uses constrained_tiers, not just
    non_negotiables_constrained, so a squeezed Groceries or Savings tier
    counts as risk too, not only a squeezed Rent.
    "tight" -- there was room to spare before and there isn't after.
    "none" -- otherwise.
    """
    newly_constrained = set(after_result.constrained_tiers) - set(before_result.constrained_tiers)
    if newly_constrained:
        return "over_budget"
    if before_result.unallocated_remainder > 0.01 and after_result.unallocated_remainder <= 0.01:
        return "tight"
    return "none"


def _build_result(
    scenario: str,
    income_before: float,
    income_after: float,
    spendable_before: float,
    buffer_before: float,
    spendable_after: float,
    buffer_after: float,
    spending_before: dict,
    spending_after: dict,
    category_roles: dict,
    summary: str,
) -> ScenarioResult:
    before_result = compute_budget_allocation_v2(spendable_before, buffer_before, spending_before, category_roles)
    after_result = compute_budget_allocation_v2(spendable_after, buffer_after, spending_after, category_roles)
    changes = diff_allocations(before_result.allocations, after_result.allocations)
    return ScenarioResult(
        scenario=scenario,
        income_before=income_before,
        income_after=income_after,
        spendable_before=spendable_before,
        spendable_after=spendable_after,
        before_allocations=before_result.allocations,
        after_allocations=after_result.allocations,
        changes=changes,
        risk_level=_risk_level(before_result, after_result),
        summary=summary,
    )


def simulate_category_change(
    income_estimate: float,
    spending_by_category: dict,
    category_roles: dict,
    category: str,
    new_amount: float,
    buffer_pct: float = DEFAULT_BUFFER_PCT,
) -> ScenarioResult:
    """"What if <category> changes to $<new_amount>/month?" -- covers a
    rent increase, canceling a subscription (new_amount=0), or adding a
    new recurring cost."""
    old_amount = spending_by_category.get(category, 0.0)
    spending_after = dict(spending_by_category)
    canceled = new_amount <= 0
    if canceled:
        # Was: spending_after[category] = 0.0. compute_budget_allocation_v2's
        # discretionary tier falls back to "split remaining evenly
        # across every discretionary category" whenever NONE of them
        # have a nonzero requested amount -- meaning if this was the
        # only discretionary category, leaving it at $0 would hand it
        # 100% of the leftover budget instead of $0. Removing it from
        # the dict entirely is the correct signal: it no longer exists
        # in the budget, not "exists with unknown/zero data."
        spending_after.pop(category, None)
    else:
        spending_after[category] = new_amount
    spendable, buffer_reserved = _spendable(income_estimate, buffer_pct)
    direction = "increases" if new_amount > old_amount else "decreases"
    summary = f"{category} {direction} from ${old_amount:.2f} to ${new_amount:.2f}/month."
    result = _build_result(
        f"category_change:{category}", income_estimate, income_estimate,
        spendable, buffer_reserved, spendable, buffer_reserved,
        spending_by_category, spending_after, category_roles, summary,
    )
    if canceled:
        # Re-added at $0 for display purposes now that the engine has
        # already run without it in the input.
        result.after_allocations.setdefault(category, {"allocated": 0.0, "is_non_neg": False})
    return result


def simulate_income_change(
    income_estimate: float,
    new_income_estimate: float,
    spending_by_category: dict,
    category_roles: dict,
    buffer_pct: float = DEFAULT_BUFFER_PCT,
) -> ScenarioResult:
    """"What if income changes to $<new_income_estimate>/month?" --
    covers a raise, a job loss, or income dropping by some amount (the
    caller computes the target dollar figure, e.g. income * 0.9 for a
    10% drop)."""
    spendable_before, buffer_before = _spendable(income_estimate, buffer_pct)
    spendable_after, buffer_after = _spendable(new_income_estimate, buffer_pct)
    delta_pct = ((new_income_estimate - income_estimate) / income_estimate * 100) if income_estimate else 0
    direction = "rises" if new_income_estimate >= income_estimate else "falls"
    summary = f"Income {direction} from ${income_estimate:.2f} to ${new_income_estimate:.2f}/month ({delta_pct:+.0f}%)."
    return _build_result(
        "income_change", income_estimate, new_income_estimate,
        spendable_before, buffer_before, spendable_after, buffer_after,
        spending_by_category, spending_by_category, category_roles, summary,
    )


def simulate_one_time_expense(
    income_estimate: float,
    spending_by_category: dict,
    category_roles: dict,
    amount: float,
    buffer_pct: float = DEFAULT_BUFFER_PCT,
) -> ScenarioResult:
    """"What happens if I need to cover an unexpected $<amount> expense
    this month?" -- modeled as a one-time reduction in this month's
    spendable income (the money has to come from somewhere), which the
    same role-priority order then absorbs, starting from discretionary
    categories before touching essentials or savings."""
    spendable_before, buffer_reserved = _spendable(income_estimate, buffer_pct)
    spendable_after = max(spendable_before - amount, 0.0)
    summary = f"An unexpected ${amount:.2f} expense this month reduces spendable income to ${spendable_after:.2f}; the allocation below shows what absorbs it."
    return _build_result(
        "one_time_expense", income_estimate, income_estimate,
        spendable_before, buffer_reserved, spendable_after, buffer_reserved,
        spending_by_category, spending_by_category, category_roles, summary,
    )


scenario_simulation_service = {
    "simulate_category_change": simulate_category_change,
    "simulate_income_change": simulate_income_change,
    "simulate_one_time_expense": simulate_one_time_expense,
}
