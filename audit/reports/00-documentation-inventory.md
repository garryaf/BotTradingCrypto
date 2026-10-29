# 00 — Documentation Inventory

**Phase:** A (Discovery, READ-ONLY). Files listed exist on disk; "authoritative" = referenced as source-of-truth by code comments.

## `docs/` tree (15-domain set, Indonesian)
| Folder | Files present |
|---|---|
| 00-overview | ROADMAP.md, (code cites `OPEN_QUESTIONS.md` Q-04/Q-07/Q-08/Q-12 — **presence not yet confirmed**) |
| 01-requirements | BUSINESS_REQUIREMENTS.md, FUNCTIONAL_REQUIREMENTS.md, NON_FUNCTIONAL_REQUIREMENTS.md, ACCEPTANCE_CRITERIA.md, TESTING_PLAN.md, UI_UX_SPECIFICATION.md, USER_ROLES_AND_USE_CASES.md |
| 02-architecture | (expected: ARCHITECTURE_OVERVIEW, RUST_ENGINE_INTEGRATION_SPEC, FAILURE_MODES_AND_RECOVERY — cited by code; listing not expanded this phase) |
| 03-diagrams | (expected: ERD.mmd, DATA_FLOW.mmd, flowcharts — cited by code) |
| 04-data | DATA_DICTIONARY.md (cited as 1:1 source for models.py) |
| 05-security | (expected: SECURITY_CONTROLS, CIRCUIT_BREAKER_OPERATIONAL_SOP, TELEGRAM_BOT_SETUP_AND_RUNBOOK, LIVE_TRADING_SAFETY_GATE — cited by code) |
| audit | DOCUMENTATION_COMPLETION_REPORT.md, DOCUMENTATION_COVERAGE_MATRIX.md, DOCUMENTATION_DEPENDENCIES.md, DOCUMENTATION_TASK_BACKLOG.md, IMPLEMENTATION_GAP_PHASES.md, PONYTAIL_SKILLS_GAP_TASKS.md, REQUIREMENTS_TRACEABILITY_MATRIX.md, UNIMPLEMENTED_TASKS_BACKLOG.md |

> Folders 02/03/05 contents were not individually listed in this phase to conserve tokens; their files are referenced by code comments and README. Phase B will enumerate and open them for the traceability matrix.

## Authoritative documents (cited directly by code)
- `docs/04-data/DATA_DICTIONARY.md` — `models.py` header says tables are "one-to-one" with it.
- `docs/00-overview/ROADMAP.md` — task IDs (TASK-2.6, 3.1-3.4, 4.1-4.4, 5.5, 6.1-6.2) referenced throughout.
- `docs/02-architecture/RUST_ENGINE_INTEGRATION_SPEC.md` — IPC contract (§3-6) for engine_client.py and _signal_candidate payload.
- `docs/05-security/LIVE_TRADING_SAFETY_GATE.md` — hardcoded live lock in main.py + burner_guard.
- `docs/00-overview/OPEN_QUESTIONS.md` — Q-04/07/08/12 drive config fallbacks and gate design.
- `.agents/skills/*/SKILL.md` — LLM system prompts (single source of truth, loaded at runtime by skills.py).

## README.md (root)
Comprehensive bilingual-leaning (Indonesian) operations manual: roadmap (Fase 0-5 ✅, 6 🟡, 7 🔒), tech stack, port matrix, local + production VPS deployment, test commands, Telegram SOP, troubleshooting, 15-doc index. **Contains the clearest statement of intended behavior** and is the de-facto product spec alongside docs/01-requirements.

## Pre-existing audit artifacts (do NOT overwrite — Rule 1)
`docs/audit/REQUIREMENTS_TRACEABILITY_MATRIX.md` (v1.0.0, 2026-10-21) already maps BR/FR/AC → files with ✅/⚠️/❌ status. This is the project's OWN self-assessment. Our audit (`audit/reports/`) is kept separate and will note where the existing RTM's claims diverge from verified code (e.g. RTM marks everything ✅; we found orphaned `wallet_scorer`, Rust/Python gate divergence, and unauth endpoints).

## Documentation vs implementation — immediate mismatches spotted
1. RTM cites `wallet_scorer.calculate_wallet_score`; actual function is `calculate_wallet_metrics` + `update_wallet_scores` (wrong name in doc, and the docstring in the module also says `calculate_wallet_score`).
2. RTM marks FR-WLT-01/03 ✅ "Fulfilled" but `update_wallet_scores` is never called by any runtime loop.
3. README says "4 agents" narrative; code implements Hermes as 3 sequential LLM skill calls + 2 deterministic non-LLM modules. See report 00-application-discovery §AI.
