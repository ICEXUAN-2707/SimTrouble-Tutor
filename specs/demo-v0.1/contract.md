# Demo v0.1 Contract

> Status: APPROVED FOR IMPLEMENTATION
> Contract class: internal Demo adapter; does not modify the frozen public API Contract

## Module boundary

```text
apps/demo/
  __main__.py        composition and process entry
  server.py          HTTP transport only
  runtime.py         in-memory Demo orchestration/read model
  rule_tutor.py      deterministic Demo-only Tutor
  st001_judge.py     deterministic Demo-only diagnosis judge
  static/index.html  presentation
```

Rules:

- `apps/demo/` imports official `core/` and reads official `data/cases/ST-001.json`;
- no Core, Contract, Case or Spec file is copied into `apps/demo/`;
- HTTP code does not implement domain mutation directly;
- `runtime.py` calls existing `CaseSession` and `EvidenceManager` commands;
- Demo presentation state may contain messages, released Evidence projections and a diagnosis result, but authoritative stage/Evidence/Hypothesis/Action/Trace come from `CaseSession.session`;
- there is no parallel Demo `events` fact list; the UI timeline is projected from authoritative Core Trace.

## Phase 3 compatibility

- Demo commands never assign Session fields directly;
- Demo commands do not automatically call `transition_to`;
- the Demo does not claim a completed `START → FINISH` diagnostic workflow;
- ST-001 diagnosis completion is a Demo-wrapper state, not a new Core stage, score or frozen diagnosis contract;
- Session IDs are server-generated and cannot be supplied by the client.

## HTTP surface

Read:

- `GET /`: static Demo page;
- `GET /healthz`: `{"status":"ok","case":"ST-001","mode":"demo-v0.1"}`;
- `GET /api/state`: creates or resumes the cookie session and returns the public Demo projection.

Commands:

- `POST /api/reset`;
- `POST /api/evidence` with `{"id":"E01|E02|E03"}`;
- `POST /api/hypothesis` with `{"text":"..."}`;
- `POST /api/chat` with `{"text":"..."}`;
- `POST /api/diagnose` with `{"text":"..."}`.

The Demo-only state projection contains:

- `mode`;
- public `case`;
- released Evidence projections;
- authoritative `session` public snapshot fields required by the UI;
- Tutor `messages`;
- authoritative Core `trace`;
- Demo-only `diagnosis`.

It excludes Ground Truth, fault configuration, Optimal Path, unreleased Evidence content, Evidence metadata and scoring rules.

## Runtime and transport rules

- bind to `127.0.0.1` by default;
- default `PORT=8000`, overridable by environment;
- use a cryptographically random HttpOnly, SameSite=Lax cookie;
- protect the process-local session map with a re-entrant lock;
- reject request bodies over 8192 bytes;
- cap free-text fields at 500 characters;
- return UTF-8 JSON and `Cache-Control: no-store`;
- no CORS, remote hosting, authentication or user accounts.

## Tutor and diagnosis rules

- Tutor output is deterministic and reads only public Case state, released Evidence IDs and the learner Hypothesis;
- Tutor cannot read Ground Truth, hidden Evidence metadata or scoring rules;
- diagnosis judgment is explicitly limited to ST-001 and must be labeled Demo-only;
- neither component changes Core stage or Skill scores.

## Contract impact

No existing JSON Schema, API Contract, Tutor Contract or Simulation Adapter Contract changes. This Demo HTTP surface is private to the pre-release adapter and may later be replaced by the approved FastAPI/Application implementation.
