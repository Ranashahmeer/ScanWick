import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from app.models.orders import OrderDataSource
from app.services.ai_client import GeminiAPIError, generate_text
from app.services.bank_ingestion import score_bank_columns
from app.services.ecommerce_ingestion import score_ecommerce_columns

logger = logging.getLogger(__name__)

# Below this, no candidate matched confidently enough to trust — the caller
# should tell the user detection wasn't confident rather than silently
# guessing (and possibly ingesting a file through the wrong pipeline
# entirely, which would parse "successfully" but produce nonsense: e.g. a
# bank statement squeezed through the ecommerce column map would resolve
# zero canonical fields and just reject every row).
MIN_CONFIDENCE = 0.4

# A heuristic score at or above this is treated as unambiguous (e.g. a real
# bank statement hitting all 4 of date/amount/balance/narration) and skips
# the LLM entirely. Below it — including scores that still clear
# MIN_CONFIDENCE, like a bare 2-of-4 bank-signal match from a column that
# merely contains the substring "price" — the heuristic could be
# confidently wrong from a shallow keyword coincidence, so it's worth a
# second, LLM-based opinion before committing to it.
LLM_FALLBACK_MAX_SCORE = 0.75

_VALID_LLM_TYPES = {"bank", "ecommerce", "other"}

_LLM_PROMPT_TEMPLATE = """You are classifying a business CSV export by its column headers and a
few sample rows, to route it to the right analytics pipeline.

Classify this file as exactly one of: "bank" (a bank/transaction statement
with debits/credits/balances), "ecommerce" (a store/order export with
per-order or per-line-item sales), or "other" (none of the above, or you're
not reasonably confident).

Columns: {columns}
Sample rows: {sample_rows}

Return ONLY a JSON object (no markdown, no explanation) with exactly these
fields:
- analyzer_type: one of "bank", "ecommerce", "other"
- confidence: a number between 0.0 and 1.0
- reasoning: one short sentence"""


def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    return match.group(1) if match else stripped


@dataclass
class DatasetDetectionResult:
    analyzer_type: Optional[str]  # "bank" | "ecommerce" | None (not confident enough)
    source: Optional[str]  # OrderDataSource value; None for bank or "not confident"
    confidence: float
    scores: dict = field(default_factory=dict)  # every candidate vertical's own best score, for transparency
    via_llm: bool = False  # whether the column-header heuristic was overridden by the LLM fallback


def detect_dataset_type(df: pd.DataFrame) -> DatasetDetectionResult:
    """Classifies an uploaded CSV's likely vertical (bank statement vs.
    e-commerce order export) from its column headers alone — reuses each
    vertical's own real column-detection logic (the same keyword lists/
    literal-header maps used during actual ingestion), so detection can
    never disagree with what ingestion itself would find.
    """
    bank_score = score_bank_columns(df)
    ecommerce_score, ecommerce_source = score_ecommerce_columns(df)

    scores = {"bank": bank_score, "ecommerce": ecommerce_score}
    best_analyzer_type = max(scores, key=lambda key: scores[key])
    best_score = scores[best_analyzer_type]

    if best_score < MIN_CONFIDENCE:
        return DatasetDetectionResult(analyzer_type=None, source=None, confidence=best_score, scores=scores)

    source = ecommerce_source.value if best_analyzer_type == "ecommerce" else None

    return DatasetDetectionResult(analyzer_type=best_analyzer_type, source=source, confidence=best_score, scores=scores)


async def _classify_with_llm(df: pd.DataFrame) -> Optional[tuple[str, float]]:
    """Second opinion for the case the header-keyword heuristic can't call
    confidently — headers that don't literally contain any known
    bank/e-commerce keyword (e.g. "unit selling price" reads as a bank
    "amount" signal to the heuristic purely because it contains "price").
    An LLM reading the actual column names and a few real rows can resolve
    that ambiguity the keyword-substring approach can't.

    Never raises: a failed call, a timeout, or an unparseable/low-confidence
    response all just return None, so the caller falls back to the
    existing "not confident enough" behavior rather than blocking the
    upload-detection endpoint on a flaky external API.
    """
    sample_rows = df.head(3).to_dict(orient="records")
    prompt = _LLM_PROMPT_TEMPLATE.format(
        columns=list(df.columns), sample_rows=json.dumps(sample_rows, default=str)
    )

    try:
        raw_text = await generate_text(prompt, timeout=10.0, max_retries=1)
    except GeminiAPIError as exc:
        logger.warning("LLM dataset-type fallback failed: %s", exc)
        return None

    try:
        parsed = json.loads(_strip_markdown_fences(raw_text))
    except (json.JSONDecodeError, TypeError):
        logger.warning("LLM dataset-type fallback returned non-JSON output: %s", raw_text[:200])
        return None

    if not isinstance(parsed, dict):
        return None
    analyzer_type = parsed.get("analyzer_type")
    confidence = parsed.get("confidence")
    if analyzer_type not in _VALID_LLM_TYPES or not isinstance(confidence, (int, float)):
        return None
    if analyzer_type == "other" or confidence < MIN_CONFIDENCE:
        return None
    return analyzer_type, float(confidence)


async def detect_dataset_type_async(df: pd.DataFrame) -> DatasetDetectionResult:
    """Same as detect_dataset_type, plus an LLM-based second opinion (see
    _classify_with_llm) whenever the header heuristic's own winning score
    is below LLM_FALLBACK_MAX_SCORE — which includes both "not confident
    enough to decide" (analyzer_type is None) and "confident enough to
    pass MIN_CONFIDENCE, but only on a couple of weak signals." The fast,
    deterministic heuristic stays authoritative for the clear-cut case
    (score >= LLM_FALLBACK_MAX_SCORE) and the LLM is never called there."""
    result = detect_dataset_type(df)
    if result.confidence >= LLM_FALLBACK_MAX_SCORE:
        return result

    llm_result = await _classify_with_llm(df)
    if llm_result is None:
        return result

    analyzer_type, confidence = llm_result
    source = OrderDataSource.generic_csv.value if analyzer_type == "ecommerce" else None

    return DatasetDetectionResult(
        analyzer_type=analyzer_type, source=source, confidence=confidence, scores=result.scores, via_llm=True
    )
