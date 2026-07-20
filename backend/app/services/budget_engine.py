"""
Deterministic budget allocation engine.

This is the fix for the 57% consistency finding from the recommendation
evaluation harness: an LLM was generating the actual dollar allocations,
so re-running the same request could produce a different budget. That's
not acceptable for a number a user might act on financially.

compute_budget_allocation() is a pure function: same inputs always
produce the same output. No LLM call happens here. Claude's role (see
ClaudeService._explain_allocation) is now strictly to write a prose
explanation of a result it did not compute and cannot change.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ENGINE_VERSION = "budget-engine-v1"


@dataclass
class AllocationResult:
    allocations: dict[str, dict]
    buffer_reserved: float
    spendable: float
    unallocated_remainder: float
    non_negotiables_constrained: bool  # True if non-negotiables alone exceeded spendable
    engine_version: str = ENGINE_VERSION
    # Which role tiers (if any) couldn't be fully funded. v1 never
    # populates this (stays [] via the default) -- it only ever tracked
    # the non-negotiable tier via non_negotiables_constrained above. v2
    # populates it for every tier (fixed_essential, variable_essential,
    # savings_or_debt), since a squeezed variable_essential or savings
    # tier is just as real a signal as a squeezed fixed_essential one,
    # and callers like scenario_simulation_service need to see all of it.
    constrained_tiers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "allocations": self.allocations,
            "buffer_reserved": self.buffer_reserved,
            "spendable": self.spendable,
            "unallocated_remainder": self.unallocated_remainder,
            "non_negotiables_constrained": self.non_negotiables_constrained,
            "engine_version": self.engine_version,
            "constrained_tiers": self.constrained_tiers,
        }


def compute_budget_allocation(
    spendable: float,
    buffer_reserved: float,
    spending_by_category: dict[str, float],
    non_negotiables: list[str],
) -> AllocationResult:
    """
    Allocation logic, in order:
    1. Non-negotiable categories are funded first, from their own
       historical spend. If a non-negotiable has no historical spend on
       record, it's allocated $0 -- this engine does not invent an amount
       for data it doesn't have. That's a deliberate change from the old
       behavior (both the LLM and the old mock fallback would substitute
       a plausible-looking number here, which is exactly the kind of
       silent invention this whole rework exists to remove).
    2. If non-negotiables alone exceed the spendable amount, they're
       scaled down proportionally to fit -- the budget cannot go negative,
       even for required categories. This is flagged in the result rather
       than hidden.
    3. Whatever's left is split among the remaining categories,
       proportional to historical spend share. Categories with no
       historical weight split the remainder evenly rather than getting $0.
    """
    spending_by_category = dict(spending_by_category or {})
    non_neg_set = list(dict.fromkeys(non_negotiables or []))  # de-dupe, keep order

    non_neg_requested = {cat: max(spending_by_category.get(cat, 0.0), 0.0) for cat in non_neg_set}
    total_non_neg_requested = sum(non_neg_requested.values())

    constrained = total_non_neg_requested > spendable > 0
    if constrained:
        scale = spendable / total_non_neg_requested
        non_neg_allocated = {cat: round(amt * scale, 2) for cat, amt in non_neg_requested.items()}
        remaining = 0.0
    else:
        non_neg_allocated = {cat: round(amt, 2) for cat, amt in non_neg_requested.items()}
        remaining = max(round(spendable - total_non_neg_requested, 2), 0.0)

    allocations: dict[str, dict] = {
        cat: {"allocated": non_neg_allocated.get(cat, 0.0), "is_non_neg": True}
        for cat in non_neg_set
    }

    other_categories = {cat: amt for cat, amt in spending_by_category.items() if cat not in non_neg_set}
    total_other = sum(other_categories.values())

    if other_categories and remaining > 0:
        if total_other > 0:
            for cat, amt in other_categories.items():
                share = amt / total_other
                allocations[cat] = {"allocated": round(remaining * share, 2), "is_non_neg": False}
        else:
            # Historical amounts are all zero/missing -- no weight to go
            # on, so split evenly rather than dropping the remainder.
            even_share = round(remaining / len(other_categories), 2)
            for cat in other_categories:
                allocations[cat] = {"allocated": even_share, "is_non_neg": False}
    elif other_categories:
        for cat in other_categories:
            allocations.setdefault(cat, {"allocated": 0.0, "is_non_neg": False})

    total_allocated = sum(v["allocated"] for v in allocations.values())
    unallocated_remainder = round(spendable - total_allocated, 2)

    return AllocationResult(
        allocations=allocations,
        buffer_reserved=buffer_reserved,
        spendable=spendable,
        unallocated_remainder=unallocated_remainder,
        non_negotiables_constrained=constrained,
    )


ENGINE_VERSION_V2 = "budget-engine-v2"
ROLE_PRIORITY_ORDER = ["fixed_essential", "variable_essential", "savings_or_debt"]


def _fund_tier(requested: dict[str, float], remaining: float) -> tuple[dict[str, float], float, bool]:
    """
    Fund each category in this tier up to its own requested amount --
    unlike the final discretionary tier, this does NOT stretch to
    consume all of `remaining`. If the tier's combined total exceeds
    what's left, every category in the tier is scaled down proportionally
    together, rather than funding some in full and leaving others at
    zero (same fairness principle v1 already used for non-negotiables).
    """
    total_requested = sum(requested.values())
    if total_requested <= 0:
        return {}, remaining, False
    if total_requested > remaining:
        scale = remaining / total_requested if remaining > 0 else 0.0
        allocated = {cat: round(amt * scale, 2) for cat, amt in requested.items()}
        return allocated, 0.0, True
    allocated = {cat: round(amt, 2) for cat, amt in requested.items()}
    return allocated, round(remaining - total_requested, 2), False


def compute_budget_allocation_v2(
    spendable: float,
    buffer_reserved: float,
    spending_by_category: dict[str, float],
    category_roles: dict[str, str],
) -> AllocationResult:
    """
    Same determinism and no-invented-amounts guarantees as
    compute_budget_allocation (v1), but funds categories in role-priority
    order instead of a flat non-negotiable/everything-else binary:

        1. fixed_essential    -- funded first (e.g. rent)
        2. variable_essential -- funded next, at its own baseline (e.g. groceries)
        3. savings_or_debt    -- funded next, BEFORE discretionary spending
        4. discretionary (+ any role not listed above) -- gets whatever's
           left, split proportionally to historical weight (the same
           "stretch to fill the remainder" behavior v1 applied to every
           non-fixed category)

    This closes a real gap in v1: a "Savings" category was just another
    "other" category competing proportionally with Dining and Shopping
    for leftover money -- there was no actual prioritization, despite
    what reasoning text elsewhere implies. Tiers 2-3 are capped to their
    own requested amount (scaled down together if a tier can't be fully
    funded) rather than stretched to consume everything left, so surplus
    money reaches savings instead of piling into an already-funded
    essential category.

    Known limitation: non_negotiables_constrained only flags tier 1
    (fixed_essential) being underfunded, for backward compatibility with
    v1's field semantics. constrained_tiers lists every tier that came
    up short (fixed_essential, variable_essential, and/or
    savings_or_debt) -- use that when a caller needs to know about a
    squeezed variable_essential or savings tier, not just fixed_essential.
    """
    spending_by_category = dict(spending_by_category or {})
    category_roles = dict(category_roles or {})

    tiers: dict[str, dict[str, float]] = {role: {} for role in ROLE_PRIORITY_ORDER}
    discretionary_requested: dict[str, float] = {}
    for cat, amt in spending_by_category.items():
        role = category_roles.get(cat, "discretionary")
        amt = max(amt, 0.0)
        if role in tiers:
            tiers[role][cat] = amt
        else:
            discretionary_requested[cat] = amt

    allocations: dict[str, dict] = {}
    remaining = spendable
    non_negotiables_constrained = False
    constrained_tiers: list[str] = []
    for role in ROLE_PRIORITY_ORDER:
        allocated, remaining, constrained = _fund_tier(tiers[role], remaining)
        is_non_neg = role == "fixed_essential"
        if constrained:
            constrained_tiers.append(role)
        if is_non_neg and constrained:
            non_negotiables_constrained = True
        for cat, amt in allocated.items():
            allocations[cat] = {"allocated": amt, "is_non_neg": is_non_neg}
        for cat in tiers[role]:
            allocations.setdefault(cat, {"allocated": 0.0, "is_non_neg": is_non_neg})

    total_discretionary = sum(discretionary_requested.values())
    if discretionary_requested and remaining > 0:
        if total_discretionary > 0:
            for cat, amt in discretionary_requested.items():
                share = amt / total_discretionary
                allocations[cat] = {"allocated": round(remaining * share, 2), "is_non_neg": False}
        else:
            even_share = round(remaining / len(discretionary_requested), 2)
            for cat in discretionary_requested:
                allocations[cat] = {"allocated": even_share, "is_non_neg": False}
    else:
        for cat in discretionary_requested:
            allocations.setdefault(cat, {"allocated": 0.0, "is_non_neg": False})

    total_allocated = sum(v["allocated"] for v in allocations.values())
    unallocated_remainder = round(spendable - total_allocated, 2)

    return AllocationResult(
        allocations=allocations,
        buffer_reserved=buffer_reserved,
        spendable=spendable,
        unallocated_remainder=unallocated_remainder,
        non_negotiables_constrained=non_negotiables_constrained,
        engine_version=ENGINE_VERSION_V2,
        constrained_tiers=constrained_tiers,
    )


def validate_allocation(
    allocations: dict[str, dict], spendable: float, non_negotiables: list[str]
) -> tuple[bool, list[str]]:
    """
    Structural correctness check. Returns (is_valid, issues). issues is
    always populated with anything worth knowing, even non-fatal ones
    (e.g. a non-negotiable funded at $0 because there's no data for it is
    a warning, not a failure -- the engine can't invent money).
    """
    issues: list[str] = []

    total_allocated = sum(v.get("allocated", 0) for v in allocations.values())
    if total_allocated > spendable + 0.01:
        issues.append(f"total_allocated ({total_allocated:.2f}) exceeds spendable ({spendable:.2f})")

    for cat, alloc in allocations.items():
        if alloc.get("allocated", 0) < -0.001:
            issues.append(f"{cat}: negative allocation ({alloc.get('allocated')})")

    for cat in non_negotiables or []:
        if cat not in allocations:
            issues.append(f"non-negotiable '{cat}' missing from allocations entirely")
        elif not allocations[cat].get("is_non_neg"):
            issues.append(f"non-negotiable '{cat}' present but not flagged is_non_neg")
        elif allocations[cat].get("allocated", 0) == 0:
            issues.append(f"WARNING: non-negotiable '{cat}' funded at $0 (no historical data)")

    hard_failures = [i for i in issues if not i.startswith("WARNING")]
    return len(hard_failures) == 0, issues


def diff_allocations(previous: dict[str, dict] | None, current: dict[str, dict]) -> list[dict]:
    """
    Category-level diff between last month's allocation and this month's,
    for the "why this changed" explanation. Returns a list of
    {category, previous_amount, current_amount, delta} for every category
    that changed by more than a cent, sorted by absolute delta descending.
    """
    if not previous:
        return []

    changes = []
    all_categories = set(previous.keys()) | set(current.keys())
    for cat in all_categories:
        prev_amt = previous.get(cat, {}).get("allocated", 0.0)
        curr_amt = current.get(cat, {}).get("allocated", 0.0)
        delta = round(curr_amt - prev_amt, 2)
        if abs(delta) >= 0.01:
            changes.append({
                "category": cat,
                "previous_amount": round(prev_amt, 2),
                "current_amount": round(curr_amt, 2),
                "delta": delta,
            })

    return sorted(changes, key=lambda c: abs(c["delta"]), reverse=True)
