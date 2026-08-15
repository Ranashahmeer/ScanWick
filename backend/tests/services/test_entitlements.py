from app.services.entitlements import gate_premium_components

_COMPONENTS = [
    {"name": "Win Rate", "score": 15, "max": 20, "_requires": "basic"},
    {"name": "Churn Risk Score", "score": 8, "max": 10, "_requires": "premium"},
]


def test_basic_tier_locks_premium_components():
    gated = gate_premium_components(_COMPONENTS, "basic")

    by_name = {c["name"]: c for c in gated}
    assert by_name["Win Rate"] == _COMPONENTS[0]  # untouched
    assert by_name["Churn Risk Score"]["locked"] is True
    assert by_name["Churn Risk Score"]["upgrade_required"] is True
    assert "score" not in by_name["Churn Risk Score"]
    assert by_name["Churn Risk Score"]["error"]["code"] == "UPGRADE_REQUIRED"


def test_premium_tier_returns_components_unchanged():
    gated = gate_premium_components(_COMPONENTS, "premium")

    assert gated == _COMPONENTS


def test_free_tier_locks_both_basic_and_premium_components():
    gated = gate_premium_components(_COMPONENTS, "free")

    by_name = {c["name"]: c for c in gated}
    assert by_name["Win Rate"]["locked"] is True
    assert by_name["Churn Risk Score"]["locked"] is True


def test_none_or_unknown_tier_locks_everything():
    """Fails closed -- an unset/unrecognized tier is treated as ranking
    below even the free tier, locking every gated component rather than
    accidentally exposing anything."""
    gated = gate_premium_components(_COMPONENTS, None)

    by_name = {c["name"]: c for c in gated}
    assert by_name["Win Rate"]["locked"] is True
    assert by_name["Churn Risk Score"]["locked"] is True
