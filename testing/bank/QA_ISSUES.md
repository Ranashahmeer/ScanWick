# Bank QA — Issue Tracker (Archived)

All Bank Analyzer QA issues discovered during Prompts 1–7 have been migrated to **GitHub Issues** as the single source of truth going forward.

- **Migrated:** every issue whose status was `Open` (18 of 21 tracked issues — B1-3, B2-1 through B2-4, B3-1 through B3-3, B4-1, B4-2, B5-1 through B5-4, B6-1 through B6-4). Each GitHub Issue preserves the original QA Issue ID in its title and body for full traceability.
- **Not migrated** (already resolved or superseded, not independently open): B1-1 (resolved/confirmed benign), B1-2 (superseded by B2-3), B3-4 (resolved via test-scaffolding workaround).
- The full original tracker, with complete evidence/root-cause/impact detail for every issue, is preserved for historical reference in [`QA_ISSUES_ARCHIVED.md`](QA_ISSUES_ARCHIVED.md) and in git history.
- The mapping from QA Issue ID → GitHub Issue number is also recorded in `testing/bank/07_result.json`'s `consolidated_issues[].github_issue` field.

See the repository's GitHub Issues tab (filtered by the `bank` label) for current status, discussion, and resolution of each issue.

_Migrated 2026-07-11._
