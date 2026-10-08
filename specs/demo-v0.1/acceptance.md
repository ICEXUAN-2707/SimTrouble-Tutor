# Demo v0.1 Acceptance

## Repository and architecture

- [x] only one authoritative `core/`, `contracts/`, `data/` and `specs/` tree exists;
- [x] local delivery packages and personal files are ignored and absent from commits;
- [x] Demo code is isolated under `apps/demo/`;
- [x] HTTP, runtime, rule Tutor, diagnosis judge and static UI responsibilities are separated;
- [x] current and target architecture documents match the repository.

## Functional Demo

- [x] `python -m apps.demo` starts the Demo;
- [x] root page and `/healthz` respond successfully;
- [x] cookie sessions are server-created and isolated;
- [x] ST-001 public state excludes hidden fields;
- [x] E01/E02/E03 can be released through the official EvidenceManager;
- [x] Hypothesis add/update uses the official CaseSession;
- [x] rule Tutor works without network or LLM;
- [x] diagnosis result is labeled ST-001 Demo-only;
- [x] reset creates a fresh session;
- [x] timeline is derived from authoritative Core Trace, with no duplicate Demo event store.

## Automated gates

- [x] HTTP E2E covers state, Evidence, Hypothesis, Tutor, diagnosis and reset;
- [x] startup smoke launches a real subprocess, polls `/healthz` and exits cleanly;
- [x] hidden Case fields never appear in learner HTTP responses;
- [x] Demo tests are deterministic and require no internet;
- [x] existing Phase 1–3 tests remain green;
- [x] dependency and forbidden-import scans pass;
- [x] CI runs the complete test suite on every PR.
