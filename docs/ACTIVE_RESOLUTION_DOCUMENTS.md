# Active Resolution Documents

Use these documents together as the current implementation backlog. They are deliberately retained in their original locations so existing references continue to work.

| Order | Document | Use it for |
| --- | --- | --- |
| 1 | [Developer Scope — Verified Implementation Guide](../issues/DEVELOPER_SCOPE_VERIFIED_IMPLEMENTATION_GUIDE.md) | Product direction: what must remain, be corrected, deleted, mothballed, and built for the lender-facing Scanwick product. |
| 2 | [Full System Audit Issues](../AUDIT_ISSUES.md) | Cross-system security, authentication, upload, payment, backend, and frontend defects. |
| 3 | [Critical Fix Pack Issues](../FIX_PACK_ISSUES.md) | Bank/ecommerce product-critical fixes, with overlap notes that map issues to the full audit. |

## Recommended resolution workflow

1. Start with **critical security issues** in `AUDIT_ISSUES.md` and `FIX_PACK_ISSUES.md`. Do not implement product-scope deletion before account takeover, secrets, authorization, and upload safety are addressed.
2. For each issue, check whether `FIX_PACK_ISSUES.md` lists an overlap with an audit ID. Create one implementation task and one regression-test set for overlaps—do not resolve the same defect twice.
3. Resolve the verified financial correctness and lender-access items in the Developer Scope guide next: ABM, calendar windows, fixed weights, lender brief, fraud false positives, loan-officer scope, currency totals, deduplication, date parsing, mapping, warnings, and merchant context.
4. Only after the critical fixes pass tests, execute the Developer Scope cleanup: delete sales/non-core analytics and mothball payment/report scheduling features.
5. Track each completed item by adding its implementation PR/commit, affected tests, and verification date to the original issue entry or a separate change log. Preserve the issue IDs (`AUTH-*`, `FP-*`, etc.) so audits remain traceable.

## Working rule

The Developer Scope guide controls **what the product should become**. The Audit and Fix Pack documents control **what is unsafe or broken now**. When they overlap, solve the stricter security/correctness requirement first and keep the provenance, RBAC, and regression-test requirements from both documents.
