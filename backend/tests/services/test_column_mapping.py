from app.models.reconciliation_reports import AnalyzerType
from app.services.column_mapping import (
    MIN_CANDIDATE_SCORE,
    compute_source_signature,
    resolve_mapping,
)


def test_exact_match_resolves_at_tier_1():
    result = resolve_mapping(["Name", "Created at", "Total"], AnalyzerType.ecommerce)
    resolved = {m.user_header: (m.canonical, m.tier) for m in result.auto_mapped}
    assert resolved["Name"] == ("external_order_id", "exact")
    assert resolved["Created at"] == ("order_date", "exact")
    assert resolved["Total"] == ("gross_revenue", "exact")
    assert result.needs_confirmation == []
    assert result.unmapped == []


def test_cash_book_style_headers_resolve_cleanly():
    """The actual target use case this whole feature exists for: a real
    shop owner's own field names, not a known platform's export."""
    result = resolve_mapping(["Date", "Item", "Qty", "Amount", "Cost", "Payment"], AnalyzerType.ecommerce)
    resolved = {m.user_header: m.canonical for m in result.auto_mapped}
    assert resolved["Date"] == "order_date"
    assert resolved["Item"] == "sku"
    assert resolved["Qty"] == "quantity"
    assert resolved["Amount"] == "gross_revenue"
    assert resolved["Cost"] == "unit_cogs"
    assert resolved["Payment"] == "payment_method"
    assert result.needs_confirmation == []
    assert result.unmapped == []


def test_money_field_never_auto_applies_on_a_fuzzy_match():
    """Launch-blocking risk flagged during design review: a fuzzy match for
    a money field must always require confirmation, even when it clears
    the score/margin thresholds that would auto-apply for any other field.
    "Sale Amt" alone scores 0.84 against gross_revenue -- above
    FUZZY_THRESHOLD (0.82) -- so this isolates MONEY_FIELDS blocking it,
    not just a below-threshold score."""
    result = resolve_mapping(["Zephyr", "Sale Amt", "Xyzabc"], AnalyzerType.ecommerce)
    assert not any(m.canonical == "gross_revenue" and m.tier == "fuzzy" for m in result.auto_mapped)
    assert any(n.candidate == "gross_revenue" for n in result.needs_confirmation)


def test_exact_match_for_a_money_field_still_auto_applies():
    """The money-field rule only blocks the fuzzy TIER -- an exact literal
    header match is still trustworthy and must not be forced through
    confirmation unnecessarily."""
    result = resolve_mapping(["Zephyr", "Amount", "Xyzabc"], AnalyzerType.ecommerce)
    assert any(m.canonical == "gross_revenue" and m.tier == "exact" for m in result.auto_mapped)
    assert result.needs_confirmation == []


def test_total_cost_header_never_auto_maps_to_unit_cogs():
    """3.8: "total cost" names a LINE total, not a per-unit cost -- it must
    never resolve straight to unit_cogs. It used to be a tier-1 exact
    synonym for unit_cogs, which (unlike tier-2 fuzzy) bypasses the
    MONEY_FIELDS confirmation requirement entirely, silently corrupting
    unit-margin/profit-leak figures. It's still a plausible unit_cogs
    candidate (real cash books do call it that), so it must surface as
    needs_confirmation, not vanish to unmapped."""
    result = resolve_mapping(["order_id", "order_date", "gross_revenue", "total cost"], AnalyzerType.ecommerce)
    assert not any(m.user_header == "total cost" for m in result.auto_mapped)
    assert any(n.user_header == "total cost" and n.candidate == "unit_cogs" for n in result.needs_confirmation)


def test_adversarial_column_collision_does_not_silently_corrupt_the_wrong_field():
    """The exact scenario design review worried about: two present columns
    that could each plausibly be `gross_revenue`. An exact match on 'Total
    Amount' must claim the field first, leaving 'Amount' (itself normally
    also an exact synonym for gross_revenue) to find its own candidate
    rather than colliding onto the same field."""
    result = resolve_mapping(["Zephyr", "Total Amount", "Amount", "Xyzabc", "Fooqux"], AnalyzerType.ecommerce)
    resolved = {m.user_header: m.canonical for m in result.auto_mapped}
    assert resolved["Total Amount"] == "gross_revenue"
    assert resolved.get("Amount") != "gross_revenue"


def test_pure_fuzzy_collision_forces_confirmation_for_a_money_candidate():
    """Neither header is an exact match here -- 'Total Amt' is a real fuzzy
    candidate for gross_revenue. It must not silently win auto-apply; a
    money field forces confirmation regardless of score/margin."""
    result = resolve_mapping(["Zephyr", "Sale Amt", "Total Amt", "Xyzabc"], AnalyzerType.ecommerce)
    assert not any(m.canonical == "gross_revenue" for m in result.auto_mapped)
    assert any(n.user_header == "Total Amt" and n.candidate == "gross_revenue" for n in result.needs_confirmation)


def test_realistic_shopify_headers_still_resolve_fully_no_regression():
    result = resolve_mapping(
        ["Name", "Created at", "Total", "Currency", "Lineitem sku", "Lineitem quantity"], AnalyzerType.ecommerce
    )
    assert result.needs_confirmation == []
    assert result.unmapped == []
    assert len(result.auto_mapped) == 6


def test_a_column_with_no_plausible_candidate_at_all_is_unmapped_not_a_forced_guess():
    result = resolve_mapping(["Zephyr", "Amount", "xyz123random"], AnalyzerType.ecommerce)
    assert "xyz123random" in [u.user_header for u in result.unmapped]
    assert not any(n.user_header == "xyz123random" for n in result.needs_confirmation)


def test_a_canonical_field_with_no_column_at_all_never_appears_in_the_result():
    """A cash book has no customer_email column whatsoever -- resolve_mapping
    must not manufacture a low-confidence guess for a field nothing could
    plausibly be a candidate for."""
    result = resolve_mapping(["Zephyr", "Amount", "Xyzabc"], AnalyzerType.ecommerce)
    all_canonicals = {m.canonical for m in result.auto_mapped} | {n.candidate for n in result.needs_confirmation}
    assert "customer_email" not in all_canonicals


def test_value_question_only_offered_for_ecommerce_gross_revenue_not_bank_amount():
    """Bank transactions have no quantity concept -- asking "per unit or
    line total" for a bank amount column would be meaningless."""
    ecommerce_result = resolve_mapping(["Name", "Created at", "Total"], AnalyzerType.ecommerce)
    assert any(q.field == "gross_revenue" for q in ecommerce_result.value_questions)

    bank_result = resolve_mapping(["Zephyr", "Amount", "Xyzabc"], AnalyzerType.bank)
    assert bank_result.value_questions == []


def test_source_signature_is_normalization_invariant():
    sig1 = compute_source_signature(["Zephyr", "Amount", "Xyzabc"], AnalyzerType.ecommerce)
    sig2 = compute_source_signature(["  zephyr  ", "AMOUNT", "xyzabc"], AnalyzerType.ecommerce)
    assert sig1 == sig2


def test_source_signature_differs_across_analyzer_type():
    """A bank CSV and an ecommerce CSV can plausibly share a near-identical
    generic header set (date, amount, description) -- the signature must
    not collide across analyzers."""
    sig_ecommerce = compute_source_signature(["date", "amount", "description"], AnalyzerType.ecommerce)
    sig_bank = compute_source_signature(["date", "amount", "description"], AnalyzerType.bank)
    assert sig_ecommerce != sig_bank


def test_source_signature_changes_when_a_column_is_added_or_removed():
    """Documented, deliberate limitation: reuse requires an identical
    header set."""
    sig_full = compute_source_signature(["Zephyr", "Amount", "Xyzabc"], AnalyzerType.ecommerce)
    sig_missing_one = compute_source_signature(["Zephyr", "Amount"], AnalyzerType.ecommerce)
    assert sig_full != sig_missing_one


def test_min_candidate_score_floor_is_respected():
    """A header that scores below the floor against every canonical field
    must be unmapped, never surfaced as a confirmation candidate nobody
    could sensibly evaluate."""
    result = resolve_mapping(["zzzzzzzzzzzzzzzzzz"], AnalyzerType.ecommerce)
    assert result.unmapped and result.unmapped[0].user_header == "zzzzzzzzzzzzzzzzzz"
    for n in result.needs_confirmation:
        assert n.confidence >= MIN_CANDIDATE_SCORE
