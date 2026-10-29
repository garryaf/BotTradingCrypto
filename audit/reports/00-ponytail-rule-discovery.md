# 00 — Ponytail & Project-Rule Discovery

**Phase:** A (READ-ONLY). Resolves Rule 3 of the audit charter.

## What "Ponytail" actually is (resolved, not invented)
Ponytail is **a coding-discipline rule, not a product feature or an AI agent.** It is defined identically in two places:
- `.kiro/steering/ponytail.md` — front-matter `title: "Ponytail, lazy senior dev mode"`, `inclusion: always` (applied to every Kiro interaction in this workspace).
- `.agents/rules/ponytail.md` — same text, with an extra closing line noting it also applies to agents working on the repo itself.

Source of each copy is the repo itself; both are byte-for-byte the same rule body. There is **no ambiguity** about the meaning, so no unresolved question here.

### The rule's requirements (summarized, not quoted >30 words)
1. Prefer the smallest complete change; do not write code nobody asked for.
2. Reuse existing codebase helpers/patterns, then stdlib/platform, then installed deps; never add a dependency for a few lines.
3. Finish every call site the change touches (callers, tests, fixtures, config, exports).
4. No gratuitous abstraction, wrappers, type conversions, options, or "for later" code; deletion beats addition.
5. Fix bugs at the shared root cause after grepping all callers.
6. New non-trivial logic must carry a small test or assert-based self-check.
7. Known shortcuts must be marked with a `shortcut: <limit>, <when to upgrade>` comment.
8. Never cut: trust-boundary validation, data-loss-preventing error handling, security, accessibility, hardware calibration, or anything the user asked for.

## Related repo rule/skill assets
- `.agents/skills/` holds six `SKILL.md` prompt files. Three are the LLM system prompts Hermes loads at runtime (regime, safety, signal). The other three (risk-gate-validation, position-sizing-compounding, token-and-contract-safety [dup], market-regime-detection) are domain knowledge prompts; only the runtime-loaded ones affect behavior.
- `.agents/skills/ponytail-audit`, `ponytail-review` — skill prompts describing how to audit/review under Ponytail (meta, not product code).
- `docs/audit/PONYTAIL_SKILLS_GAP_TASKS.md` — project's own backlog mapping Ponytail skills to gaps (not yet opened in detail).

## Compliance observations against the code read so far
These are preliminary; full scoring is Phase D (`06-ponytail-compliance.csv`).

| Rule | Where examined | Verdict | Evidence |
|---|---|---|---|
| Smallest change / no gratuitous abstraction | risk/gate.py, gateway/client.py, api/control.py | **Compliant** | Pure functions, no needless wrappers; values kept as Decimal/dicts |
| Reuse existing patterns | backtest/engine.py reuses risk gate+broker | **Compliant** | Explicit comment + shared imports |
| Self-check for non-trivial logic | risk/test_gate.py, engine test_valid_signal, test_copy_trade, etc. | **Compliant** | Plain-assert self-checks per module |
| Mark shortcuts | binance.ts ("ponytail: fixed backoff ceiling"), engine.py ("shortcut: Decimal->float") | **Compliant** | Comments present in required form |
| Never cut trust-boundary validation | api/routes.py /signals & /backtest/run | **Violated (partial)** | Missing auth at a trust boundary (F-03) |
| Finish every call site | wallet_scorer | **Violated** | Logic written but never wired to a runtime caller (F-07) |
| Keep docs/names honest (implied by "anything the user asked for") | RTM, README | **Drift** | Overstated completion + stale name (F-10, F-12) |

## Conclusion for Rule 3
Ponytail is fully determinable from the repo; definition recorded above. Compliance is mostly strong (the code is lean and self-checked), with concrete violations captured as F-03 (trust-boundary validation cut) and F-07 (unfinished call site), plus documentation-honesty drift (F-10/F-12). Full per-file compliance matrix deferred to Phase D.
