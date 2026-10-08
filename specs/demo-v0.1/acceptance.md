# Demo v0.1 Acceptance

## Repository and architecture

- [ ] only one authoritative `core/`, `contracts/`, `data/` and `specs/` tree exists;
- [ ] local delivery packages and personal files are ignored and absent from commits;
- [ ] Demo code is isolated under `apps/demo/`;
- [ ] HTTP, runtime, rule Tutor, diagnosis judge and static UI responsibilities are separated;
- [ ] current and target architecture documents match the repository.

## Functional Demo

- [ ] `python -m apps.demo` starts the Demo;
- [ ] root page and `/healthz` respond successfully;
- [ ] cookie sessions are server-created and isolated;
- [ ] ST-001 public state excludes hidden fields;
- [ ] E01/E02/E03 can be released through the official EvidenceManager;
- [ ] Hypothesis add/update uses the official CaseSession;
- [ ] rule Tutor works without network or LLM;
- [ ] diagnosis result is labeled ST-001 Demo-only;
- [ ] reset creates a fresh session;
- [ ] timeline is derived from authoritative Core Trace, with no duplicate Demo event store.

## Automated gates

- [ ] HTTP E2E covers state, Evidence, Hypothesis, Tutor, diagnosis and reset;
- [ ] startup smoke launches a real subprocess, polls `/healthz` and exits cleanly;
- [ ] hidden Case fields never appear in learner HTTP responses;
- [ ] Demo tests are deterministic and require no internet;
- [ ] existing Phase 1–3 tests remain green;
- [ ] dependency and forbidden-import scans pass;
- [ ] CI runs the complete test suite on every PR.
