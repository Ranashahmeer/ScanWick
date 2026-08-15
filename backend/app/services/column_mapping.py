"""General-purpose column-header mapping engine (the "Data Mapping Layer").

Existing ingestion (ecommerce_ingestion.py/bank_ingestion.py) only recognizes
a handful of known-platform header sets (Shopify/WooCommerce/Generic and bank
keyword lists) — anything else resolves via a narrow 4-field substring
fallback (ecommerce's `find_column`/`_FALLBACK_ROLE`) or fails silently. A
real owner's cash book with headers like "Amount"/"Cost"/"Item" mostly can't
be read at all.

This module adds a confidence-scored, four-tier resolver (exact -> fuzzy ->
needs-confirmation -> unmapped) on top of those existing maps, seeded from the
union of their own literal header values plus real-world variants documented
in the product's own mapping-layer spec. It never invents data: an unresolved
field surfaces as a named warning, it is never silently guessed at, and money
fields specifically are never allowed to auto-apply on a fuzzy match alone
(see MONEY_FIELDS below) — this is the one thing every tier must protect,
since a wrong exact-name guess for a cost column or `gross_revenue` is
correctness-critical in a way a wrong guess for `channel` is not.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional

from rapidfuzz import fuzz

from app.models.reconciliation_reports import AnalyzerType

# Auto-apply thresholds for tier 2 (fuzzy). Score is rapidfuzz's 0-100
# token_sort_ratio scaled to 0-1. MARGIN requires the best match to clearly
# beat the runner-up -- a threshold alone can't tell "Amount" and "Discount
# Amount" apart when both score highly against the same synonym list; a
# margin can.
FUZZY_THRESHOLD = 0.82
FUZZY_MARGIN = 0.10

# Below this, a header/canonical-field pair isn't a real candidate at all --
# excluded even from needs_confirmation (which is for genuine "is this a
# match?" ambiguity, not "here's the least-bad option out of nothing").
MIN_CANDIDATE_SCORE = 0.5

# Canonical fields where a wrong mapping directly corrupts a dollar figure
# rather than just a label -- these can NEVER auto-apply on a tier-2 (fuzzy)
# match, no matter how high the score or margin. Only an exact tier-1 match,
# or a previously user-confirmed ColumnMapping, is trusted for these without
# asking again. Deliberately mirrors the fields implicated in real bugs found
# this session (profit-leak/margin miscalculation from a wrong cost column).
MONEY_FIELDS: dict[AnalyzerType, set[str]] = {
    AnalyzerType.ecommerce: {
        "gross_revenue",
        "unit_cogs",
        "discount_amount",
        "refund_amount",
        "shipping_cost",
        "unit_price",
    },
    AnalyzerType.bank: {"amount", "credit_amount", "debit_amount", "balance_after"},
}

# Seeded from the union of every existing hardcoded per-platform map's real
# values (ecommerce_ingestion.py's SHOPIFY/WOOCOMMERCE/GENERIC_COLUMN_MAP,
# bank_ingestion.py's keyword lists) plus the real-world cash-book/bank-
# statement header variants documented in Scanwick_Mapping_Layer_Guide.pdf
# Part 2.2/Part 3 -- not invented, mined from real exports and the product's
# own header research.
CANONICAL_SYNONYMS: dict[AnalyzerType, dict[str, list[str]]] = {
    AnalyzerType.ecommerce: {
        "external_order_id": [
            "name", "order_id", "order id", "receipt no", "receipt number", "s/n", "sn",
            "order number", "order no",
        ],
        "order_date": [
            "created at", "order_date", "order date", "date", "sale date", "txn date",
            "transaction date", "day", "date sold",
        ],
        "gross_revenue": [
            "total", "order_total", "gross_revenue", "amount", "sale amount", "price sold",
            "selling price", "revenue", "sales", "total amount",
        ],
        "unit_cogs": [
            # 3.8: "total cost" deliberately excluded -- it names a LINE
            # total, not a per-unit cost, and this list feeds tier-1 exact
            # matching, which (unlike tier-2 fuzzy) is NOT blocked by
            # MONEY_FIELDS. An exact "total cost" header used to auto-map
            # straight to this per-unit COGS field with no confirmation at
            # all, silently corrupting unit-margin/profit-leak figures by
            # whatever the average quantity-per-order happened to be. A
            # "total cost" header now falls through to fuzzy scoring
            # instead, where unit_cogs's MONEY_FIELDS membership forces
            # needs_confirmation rather than auto-applying.
            "lineitem cogs", "item_cost_price", "cogs", "cost", "cost price",
            "buying price", "purchase price", "cost of goods",
        ],
        "original_currency": ["currency", "order_currency", "ccy"],
        "discount_amount": ["discount amount", "cart_discount", "discount_amount", "discount"],
        "refund_amount": ["refunded amount", "refunded_total", "refund_amount", "refund", "returns"],
        "shipping_cost": ["shipping", "order_shipping", "shipping_cost", "shipping cost", "delivery fee"],
        "channel": ["source name", "payment_method", "channel", "sales channel"],
        "sku": [
            "lineitem sku", "item_sku", "sku", "product", "item", "product name", "goods",
            "description", "particulars",
        ],
        "quantity": ["lineitem quantity", "item_quantity", "quantity", "qty", "units", "pcs", "number"],
        "unit_price": [
            "lineitem price", "item_cost", "unit_price", "unit selling price", "unit price",
            "price each",
        ],
        "unit_return_cost": ["lineitem return cost", "item_return_cost", "unit_return_cost", "return cost"],
        "customer_email": ["email", "billing_email", "customer_email", "customer email"],
        "processing_fees": ["processing_fee", "processing fee", "processing fees", "transaction fee"],
        "allocated_ad_spend": ["ad_spend_allocated", "ad spend", "allocated_ad_spend"],
        "category": ["category", "type", "product category", "product type"],
        "payment_method": [
            "payment method", "payment", "mode", "paid by", "payment mode", "channel",
        ],
    },
    AnalyzerType.bank: {
        "transaction_date": [
            "date", "trans date", "value date", "transaction_date", "txn date",
            "transaction date",
        ],
        "description": ["narration", "description", "details", "remarks", "particulars", "memo", "payee"],
        "amount": ["amount"],
        "credit_amount": ["credit", "deposit", "money in", "inflow", "receipt", "credits"],
        "debit_amount": ["debit", "withdrawal", "money out", "outflow", "expense", "payment", "debits"],
        "transaction_type": ["type", "drcr", "dr_cr", "indicator", "transaction_type"],
        "balance_after": ["balance", "running balance", "closing_balance", "running_balance"],
        "currency": ["currency", "ccy"],
        "account_number": [
            "account_number", "account_no", "acc_no", "acc_number", "iban", "account_id",
            "bank_account",
        ],
    },
}


@dataclass(frozen=True)
class FieldMatch:
    user_header: str
    canonical: str
    tier: str  # "exact" | "fuzzy"
    confidence: float


@dataclass(frozen=True)
class NeedsConfirmation:
    user_header: str
    candidate: Optional[str]
    confidence: float
    prompt: str


@dataclass(frozen=True)
class Unmapped:
    user_header: str
    reason: str


@dataclass(frozen=True)
class ValueQuestion:
    field: str
    question: str
    options: list[str] = field(default_factory=lambda: ["per_unit", "line_total"])


@dataclass(frozen=True)
class MappingResult:
    auto_mapped: list[FieldMatch]
    needs_confirmation: list[NeedsConfirmation]
    unmapped: list[Unmapped]
    value_questions: list[ValueQuestion]

    def to_dict(self) -> dict:
        return {
            "auto_mapped": [
                {"user_header": m.user_header, "canonical": m.canonical, "tier": m.tier, "confidence": m.confidence}
                for m in self.auto_mapped
            ],
            "needs_confirmation": [
                {
                    "user_header": n.user_header,
                    "candidate": n.candidate,
                    "confidence": n.confidence,
                    "prompt": n.prompt,
                }
                for n in self.needs_confirmation
            ],
            "unmapped": [{"user_header": u.user_header, "reason": u.reason} for u in self.unmapped],
            "value_questions": [
                {"field": v.field, "question": v.question, "options": v.options} for v in self.value_questions
            ],
        }

    def confirmed_mapping(self) -> dict[str, str]:
        """The {user_header: canonical_field} dict ready to persist/use --
        only what actually auto-resolved. Callers merge in the user's
        confirmations for needs_confirmation/unmapped rows before ingesting."""
        return {m.user_header: m.canonical for m in self.auto_mapped}


def _normalize_header(header: str) -> str:
    """Strips BOM (utf-8-sig, common in Excel-on-Windows exports), collapses
    internal whitespace, and casefolds. Applied before every match and before
    hashing -- without this, the exact messy real-world headers this feature
    targets (trailing spaces, stray non-breaking spaces) defeat both matching
    and the "zero-touch on repeat upload" goal."""
    cleaned = header.replace("﻿", "").replace("\xa0", " ")
    return " ".join(cleaned.split()).strip().lower()


# Only ecommerce's gross_revenue has a real per-unit-vs-line-total ambiguity
# (quantity * unit_price vs. an already-totaled column).
_PRIMARY_REVENUE_FIELD: dict[AnalyzerType, str] = {
    AnalyzerType.ecommerce: "gross_revenue",
}


def resolve_mapping(columns: list[str], analyzer_type: AnalyzerType) -> MappingResult:
    """Runs the four-tier resolution (exact -> fuzzy -> confirm -> unmapped),
    driven by the dataframe's actual columns (one outcome per real user
    header, matching the product spec's response shape) rather than by the
    canonical field list -- a canonical field with no plausible column at all
    (e.g. a cash book has no `loss_reason`) simply never appears anywhere in
    the result, it does not manufacture a low-confidence guess for it. Money
    fields (MONEY_FIELDS) never auto-apply on a fuzzy match regardless of
    score/margin -- they always surface as needs_confirmation unless matched
    exactly."""
    synonyms = CANONICAL_SYNONYMS.get(analyzer_type, {})
    money_fields = MONEY_FIELDS.get(analyzer_type, set())
    normalized_variants: dict[str, set[str]] = {
        canonical_field: {_normalize_header(v) for v in variants} | {_normalize_header(canonical_field)}
        for canonical_field, variants in synonyms.items()
    }
    normalized_columns = {col: _normalize_header(col) for col in columns}

    auto_mapped: list[FieldMatch] = []
    matched_headers: set[str] = set()
    matched_fields: set[str] = set()

    # Tier 1: exact match, one canonical field per header, first-come first-served.
    for canonical_field, variants in normalized_variants.items():
        if canonical_field in matched_fields:
            continue
        exact_header = next(
            (col for col, norm in normalized_columns.items() if norm in variants and col not in matched_headers),
            None,
        )
        if exact_header is not None:
            auto_mapped.append(FieldMatch(exact_header, canonical_field, "exact", 1.0))
            matched_headers.add(exact_header)
            matched_fields.add(canonical_field)

    # Tier 2/3: score every remaining (header, canonical_field) pair, then
    # greedily assign highest-scoring pairs first -- this is what correctly
    # separates "Amt" from "Discount Amt" when both are candidates for
    # gross_revenue and neither is an exact match: whichever genuinely scores
    # higher wins the field, the other falls through to its own next-best
    # candidate (or unmapped) instead of both vaguely competing per-field.
    candidates: list[tuple[float, str, str]] = []  # (score, header, canonical_field)
    for col, norm in normalized_columns.items():
        if col in matched_headers:
            continue
        for canonical_field in normalized_variants:
            if canonical_field in matched_fields:
                continue
            score = max((fuzz.token_sort_ratio(norm, v) / 100.0 for v in normalized_variants[canonical_field]), default=0.0)
            if score >= MIN_CANDIDATE_SCORE:
                candidates.append((score, col, canonical_field))
    candidates.sort(key=lambda item: item[0], reverse=True)

    needs_confirmation: list[NeedsConfirmation] = []
    # Second-best score per header, for the margin check -- computed before
    # greedy assignment consumes candidates.
    scores_by_header: dict[str, list[float]] = {}
    for score, col, _field in candidates:
        scores_by_header.setdefault(col, []).append(score)

    for score, col, canonical_field in candidates:
        if col in matched_headers or canonical_field in matched_fields:
            continue
        header_scores = scores_by_header.get(col, [score])
        runner_up = header_scores[1] if len(header_scores) > 1 else 0.0
        margin = score - runner_up
        is_money_field = canonical_field in money_fields

        if score >= FUZZY_THRESHOLD and margin >= FUZZY_MARGIN and not is_money_field:
            auto_mapped.append(FieldMatch(col, canonical_field, "fuzzy", round(score, 2)))
        else:
            needs_confirmation.append(
                NeedsConfirmation(
                    col,
                    canonical_field,
                    round(score, 2),
                    f"Is '{col}' your {canonical_field.replace('_', ' ')}?",
                )
            )
        matched_headers.add(col)
        matched_fields.add(canonical_field)

    unmapped = [Unmapped(col, "no confident match") for col in columns if col not in matched_headers]

    value_questions: list[ValueQuestion] = []
    revenue_field = _PRIMARY_REVENUE_FIELD.get(analyzer_type)
    if revenue_field and any(m.canonical == revenue_field for m in auto_mapped):
        value_questions.append(
            ValueQuestion(
                revenue_field,
                f"Is '{revenue_field.replace('_', ' ')}' the price for one unit or the whole line?",
            )
        )

    return MappingResult(auto_mapped, needs_confirmation, unmapped, value_questions)


def summarize_mapping_applied(mapping: Optional[dict], unmapped_headers: Optional[list], value_rules: Optional[dict]) -> dict:
    """The `mapping_applied` snapshot each ingestion task writes onto its own
    Upload.analyzer_metadata (see routes/uploads.py:_serialize) -- describes
    what this specific upload actually used, frozen at ingestion time.
    Deliberately simpler than the richer per-field tier/confidence data (that
    lives in the ColumnMapping row's confidence_summary, already returned to
    the frontend by the original detect/confirm call) -- this snapshot only
    reports what's genuinely knowable at the ingestion-task boundary, not a
    reconstructed tier breakdown."""
    return {
        "columns_mapped": len(mapping or {}),
        "unmapped_headers": unmapped_headers or [],
        "value_rules_applied": value_rules or {},
    }


def compute_source_signature(columns: list[str], analyzer_type: AnalyzerType) -> str:
    """Identifies a recurring header shape for a merchant so a future upload
    with the identical header set can reuse a previously-confirmed mapping
    zero-touch. Folds analyzer_type into the hash itself (not just the
    lookup scope) since a bank CSV and an ecommerce CSV can plausibly share
    a near-identical generic header set (date, amount, description).

    Deliberately exact-header-set only: adding/removing one column changes
    the signature and re-triggers confirmation even though most columns are
    unchanged -- a conservative, safe default, not a bug."""
    normalized = sorted(_normalize_header(c) for c in columns)
    payload = f"{analyzer_type.value}|{','.join(normalized)}"
    return hashlib.sha256(payload.encode()).hexdigest()
