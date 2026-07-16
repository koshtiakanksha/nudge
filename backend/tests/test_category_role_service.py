from app.services.category_role_service import (
    ROLE_DISCRETIONARY,
    ROLE_FIXED_ESSENTIAL,
    ROLE_SAVINGS_OR_DEBT,
    ROLE_UNCLASSIFIED,
    ROLE_VARIABLE_ESSENTIAL,
    infer_role,
    is_non_negotiable,
    roles_for_categories,
)


def test_rent_defaults_to_fixed_essential():
    assert infer_role("Rent") == ROLE_FIXED_ESSENTIAL


def test_groceries_defaults_to_variable_essential():
    assert infer_role("Groceries") == ROLE_VARIABLE_ESSENTIAL


def test_dining_defaults_to_discretionary():
    assert infer_role("Dining") == ROLE_DISCRETIONARY


def test_savings_defaults_to_savings_or_debt():
    assert infer_role("Savings") == ROLE_SAVINGS_OR_DEBT


def test_unrecognized_category_is_unclassified_not_discretionary():
    assert infer_role("Pottery Classes") == ROLE_UNCLASSIFIED


def test_explicit_fixed_category_type_overrides_a_normally_discretionary_name():
    # A user could mark "Dining" as fixed (e.g. a meal plan) -- the
    # explicit override should win over the name-based default.
    assert infer_role("Dining", category_type="fixed") == ROLE_FIXED_ESSENTIAL


def test_flexible_category_type_does_not_override_defaults():
    # "flexible" is the column's default value, not necessarily a
    # deliberate choice -- name-based inference should still apply.
    assert infer_role("Rent", category_type="flexible") == ROLE_FIXED_ESSENTIAL


def test_roles_for_categories_applies_user_overrides_selectively():
    roles = roles_for_categories(
        ["Rent", "Dining", "Groceries"],
        category_types={"Dining": "fixed"},
    )
    assert roles == {
        "Rent": ROLE_FIXED_ESSENTIAL,
        "Dining": ROLE_FIXED_ESSENTIAL,
        "Groceries": ROLE_VARIABLE_ESSENTIAL,
    }


def test_only_fixed_essential_is_non_negotiable_today():
    assert is_non_negotiable(ROLE_FIXED_ESSENTIAL) is True
    assert is_non_negotiable(ROLE_VARIABLE_ESSENTIAL) is False
    assert is_non_negotiable(ROLE_SAVINGS_OR_DEBT) is False
    assert is_non_negotiable(ROLE_DISCRETIONARY) is False
