from typing import Optional

from app.models.bank_transactions import TransactionMode

# Heuristic keyword classification from free-text `description` — there is
# no ingestion path anywhere (CSV/PDF/Mono) that populates
# BankTransaction.mode or .category, confirmed by grepping the codebase
# before building this. Real bank statement descriptions vary wildly and
# are often cryptic codes, so these are necessarily best-effort, not a
# robust classifier — documented as approximate rather than hidden behind
# a confident-looking result.

_MODE_KEYWORDS: list[tuple[TransactionMode, tuple[str, ...]]] = [
    (TransactionMode.pos, ("pos ", "pos/", "card purchase", "card payment", "point of sale")),
    (TransactionMode.cash_withdrawal, ("atm", "cash withdrawal", "withdrawal")),
    (TransactionMode.mobile_money, ("mobile money", "momo", "ussd")),
    (TransactionMode.direct_debit, ("direct debit",)),
    (TransactionMode.standing_order, ("standing order",)),
    (TransactionMode.bank_charge, ("charge", "fee", "commission", "maintenance fee")),
    (TransactionMode.bank_transfer, ("transfer", "nip", "rtgs", "neft")),
]


def classify_mode(description: Optional[str]) -> Optional[TransactionMode]:
    """None when no keyword matches — not a guessed default."""
    if not description:
        return None
    text = description.lower()
    for mode, keywords in _MODE_KEYWORDS:
        if any(kw in text for kw in keywords):
            return mode
    return None


_BUSINESS_KEYWORDS = (
    "invoice",
    "supplier",
    "vendor",
    "payroll",
    "office rent",
    "utility bill",
    "subscription fee",
    "withholding tax",
    "wht",
    "vat payment",
    "business loan",
)
_PERSONAL_KEYWORDS = (
    "netflix",
    "spotify",
    "uber",
    "bolt",
    "jumia",
    "restaurant",
    "supermarket",
    "grocery",
    "fuel station",
    "fast food",
    "cinema",
    "shopping",
)


def classify_business_or_personal(description: Optional[str]) -> str:
    """Returns "business" / "personal" / "unclassified". "unclassified"
    will often be the largest bucket against real bank statement text —
    an honest reflection of this heuristic's real limits, not hidden."""
    if not description:
        return "unclassified"
    text = description.lower()
    if any(kw in text for kw in _BUSINESS_KEYWORDS):
        return "business"
    if any(kw in text for kw in _PERSONAL_KEYWORDS):
        return "personal"
    return "unclassified"
