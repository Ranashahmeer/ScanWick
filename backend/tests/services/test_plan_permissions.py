from app.services.plan_permissions import AccessLevel, all_features_by_category, get_access


def test_get_access_fails_closed_for_unknown_feature():
    assert get_access("not.a.real.feature", "premium").level == AccessLevel.NONE


def test_get_access_fails_closed_for_unknown_tier():
    assert get_access("ecommerce.net_margin_dashboard", "enterprise").level == AccessLevel.NONE


def test_get_access_fails_closed_for_none_tier():
    """An unpersisted User() object leaves subscription_tier unset (None)
    until it's actually flushed through the DB default -- this must still
    deny access rather than silently allow it."""
    assert get_access("ecommerce.net_margin_dashboard", None).level == AccessLevel.NONE


def test_net_margin_dashboard_is_none_at_free_and_full_above():
    assert get_access("ecommerce.net_margin_dashboard", "free").level == AccessLevel.NONE
    assert get_access("ecommerce.net_margin_dashboard", "basic").level == AccessLevel.FULL
    assert get_access("ecommerce.net_margin_dashboard", "premium").level == AccessLevel.FULL


def test_loan_readiness_is_three_way_tiered():
    free = get_access("bank.loan_readiness", "free")
    basic = get_access("bank.loan_readiness", "basic")
    premium = get_access("bank.loan_readiness", "premium")
    assert free.level == AccessLevel.LIMITED and free.detail == "Grade only (A/B/C/D)"
    assert basic.level == AccessLevel.LIMITED and basic.detail == "Score + grade + tier"
    assert premium.level == AccessLevel.FULL


def test_all_features_by_category_covers_every_pdf_category():
    grouped = all_features_by_category()
    assert set(grouped.keys()) == {
        "Platform / General",
        "E-Commerce Analyzer",
        "Bank Statement Analyzer",
    }
    assert all(grouped.values())  # every category has at least one feature
