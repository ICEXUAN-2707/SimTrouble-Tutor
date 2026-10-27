# Product v0.5 M1 delivery note

Date: 2026-10-27
Branch: `task/product-v0.5-m1-launcher`
Base: Product v0.5 Phase commit `538c9ce` (M0 and M2 merged)

## Scope delivered

- Added root Windows double-click entry and a small Python launcher.
- Added local configuration example and setup/launch guidance.
- Preflight reuses the existing Tutor settings and provider registry, checks required local runtimes/dependencies and fixed ports, and reports provider state without secrets.
- Starts only local API/Vite services, waits for readiness, opens the local training workspace, and cleans up only launcher-owned processes.
- Kept real provider smoke explicit and credential-gated. SQLite scope remains user-owned completed training records only.

## Review and acceptance

- Code review checked config allowlisting, API-only provider secrets, safe port refusal, readiness handling, and launcher-owned process cleanup. Corrected the readiness callback type and import ordering.
- `--check-only` passed after reusing the main workspace's existing Python and Vite dependencies through temporary junctions in this isolated worktree.
- Launcher started API and Vite successfully and reported the local training page ready.
- User completed browser acceptance and reported that all flows except LLM smart Q&A were acceptable.
- Launcher startup reported `llm_disabled`; this run used deterministic rule fallback and did not exercise a real LLM provider. No API key was requested, printed, or persisted by the launcher.
- The full automated Playwright smoke produced no output while waiting and was interrupted; it is not counted as passed.

## Remaining ordered work

1. Configure a valid provider key locally and run the existing explicit DeepSeek smoke if real LLM behavior is needed.
2. Finish M1 merge review/CI on its task branch, then merge into the Product v0.5 Phase.
3. Preserve Product v0.4 Phase → `develop` before Product v0.5 Phase → `develop`.
4. Complete the already planned human UAT and deployment acceptance.
