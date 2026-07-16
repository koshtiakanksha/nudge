"""
Category role classification.

Assigns each spending category a planning role -- fixed_essential,
variable_essential, discretionary, or savings_or_debt -- because the
role determines how a category should be treated in budgeting. Rent
shouldn't get a volatility buffer the way Dining should; savings should
be goal-driven rather than inferred from past spending. This is the
groundwork category_profile_service.py and budget_allocation_engine_v2
(later steps) will build on.

Deliberately additive, not a replacement for BudgetCategory
.category_type's existing "fixed"/"flexible" binary -- that field still
drives the current v1 allocation engine unchanged. An explicit
category_type of "fixed" is respected as an override (the user marked
it non-negotiable) and always maps to fixed_essential regardless of
what the name-based default would say. "flexible" is NOT treated as an
override, since it's the column's default value rather than necessarily
a deliberate choice -- name-based defaults apply instead.

Anything unrecognized falls to "unclassified", not "discretionary" --
assuming an unrecognized category is safe to deprioritize is a worse
default than asking.
"""
from __future__ import annotations

ROLE_FIXED_ESSENTIAL = "fixed_essential"
ROLE_VARIABLE_ESSENTIAL = "variable_essential"
ROLE_DISCRETIONARY = "discretionary"
ROLE_SAVINGS_OR_DEBT = "savings_or_debt"
ROLE_UNCLASSIFIED = "unclassified"

ALL_ROLES = [
    ROLE_FIXED_ESSENTIAL,
    ROLE_VARIABLE_ESSENTIAL,
    ROLE_DISCRETIONARY,
    ROLE_SAVINGS_OR_DEBT,
    ROLE_UNCLASSIFIED,
]

DEFAULT_ROLE_BY_CATEGORY = {
    "Rent": ROLE_FIXED_ESSENTIAL,
    "Utilities": ROLE_FIXED_ESSENTIAL,
    "Utilities & Bills": ROLE_FIXED_ESSENTIAL,
    "Insurance": ROLE_FIXED_ESSENTIAL,
    "Health": ROLE_FIXED_ESSENTIAL,
    "Healthcare": ROLE_VARIABLE_ESSENTIAL,
    "Groceries": ROLE_VARIABLE_ESSENTIAL,
    "Transportation": ROLE_VARIABLE_ESSENTIAL,
    "Education": ROLE_VARIABLE_ESSENTIAL,
    "Dining": ROLE_DISCRETIONARY,
    "Shopping": ROLE_DISCRETIONARY,
    "Entertainment": ROLE_DISCRETIONARY,
    "Travel": ROLE_DISCRETIONARY,
    "Subscriptions": ROLE_DISCRETIONARY,
    "Fees": ROLE_DISCRETIONARY,
    "Savings": ROLE_SAVINGS_OR_DEBT,
    "Debt Payments": ROLE_SAVINGS_OR_DEBT,
    "Other": ROLE_UNCLASSIFIED,
}


def infer_role(category_name: str, category_type: str | None = None) -> str:
    """
    category_type, if given, is the existing BudgetCategory.category_type
    value ("fixed" or "flexible") for this category. An explicit "fixed"
    is honored as an override to fixed_essential -- if a user manually
    marked a category non-negotiable, that decision wins regardless of
    what the category is named.
    """
    if category_type == "fixed":
        return ROLE_FIXED_ESSENTIAL
    return DEFAULT_ROLE_BY_CATEGORY.get(category_name, ROLE_UNCLASSIFIED)


def roles_for_categories(category_names: list[str], category_types: dict[str, str] | None = None) -> dict[str, str]:
    """Batch version of infer_role. category_types maps category name ->
    the user's existing BudgetCategory.category_type, when known."""
    category_types = category_types or {}
    return {name: infer_role(name, category_types.get(name)) for name in category_names}


def is_non_negotiable(role: str) -> bool:
    """fixed_essential is the only role the current (v1) allocation
    engine treats specially -- it only understands a binary is_non_neg
    flag. variable_essential, savings_or_debt, and discretionary are all
    folded into the same proportional remainder for now. That changes
    once budget_allocation_engine_v2 exists and can treat each role
    differently instead of just fixed-vs-everything-else."""
    return role == ROLE_FIXED_ESSENTIAL


category_role_service = {
    "infer_role": infer_role,
    "roles_for_categories": roles_for_categories,
    "is_non_negotiable": is_non_negotiable,
}
