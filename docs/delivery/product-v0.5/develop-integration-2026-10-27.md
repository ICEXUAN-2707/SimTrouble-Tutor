# Product v0.5 develop integration — 2026-10-27

## Baselines and ordering

- v0.4 final RC: `35cedbe43a3b95b360f75a9914c4f318e57fa8d5`.
- v0.5 Phase: `21ebf8d592a55bc14f7409fd895874512e272b2f`, including M0 #24, M2 #25 and M1 #26.
- Integration workspace: `.tmp/v05-develop-integration`; original workspace changes retained.
- v0.4-to-develop PR: https://github.com/ICEXUAN-2707/SimTrouble-Tutor/pull/28
- Product owner explicitly confirmed human RC acceptance PASS in the project conversation on 2026-10-27 ("可以，验收通过"). Browser version was not supplied.
- PR #28 merged v0.4 into develop as `24f3f892d0d97a19e96e619482345597c179d1f9` after current-head CI passed.
- Merged the resulting develop into this candidate as `29de344`; the merge introduced no additional file-content changes.

## Resolutions

- Keep the shared provider configuration example; resolve its comment-only add/add conflict.
- Keep both the v0.4 acceptance information and v0.5 authentication, completed-record storage and launcher documentation in README.
- Preserve v0.5 Phase push checks and v0.4 production Preview CI; remove the duplicate dependency-audit step introduced by automatic merge.
- Update the inherited acceptance launcher's health requirement to v0.5.0. It must reject an old v0.4 service rather than waiting for or accepting the wrong product version.
- Keep all public API contracts, ownership rules, scoring and minimal SQLite storage scope unchanged.

## Local candidate verification

- Full Python regression including the stale-v0.4-service regression: all 170 tests passed.
- Acceptance-launcher tests: all 7 passed.
- TypeScript and Vite production build passed; existing Three.js chunk-size warning remains.
- npm dependency audit: zero vulnerabilities.
- Real FastAPI + production Preview + Edge CI browser suite passed: authentication/restore/revocation, learning, precollected-evidence unlock, diagnosis/report errors and results, controlled Tutor delivery/fallback, desktop/tablet/mobile.
- Browser database isolated at the integration workspace's `var/integration-acceptance.db`; root account data untouched. Test services stopped after completion.
- No new live Provider call made for this candidate. The unchanged v0.4 final RC has an explicit real DeepSeek smoke PASS record.

## Pending gates

1. Complete current-head CI/review of alignment PR #29, then integrate into v0.5 Phase.
2. Current-head v0.5 Phase checks and PR review, then merge v0.5 into develop.
3. Verify final develop ancestry and post-merge checks.

Production hosting, HTTPS, backup/restore, release/main promotion and additional features are outside this integration task.
