# SimTrouble Training Web v0.4

CAD-style learner workspace for the v0.4 dual-core product baseline.

## Local development

From the repository root, start the scene API:

```powershell
.\.venv\Scripts\python.exe -B -m apps.training_api
```

Then start the web client in another terminal:

```powershell
Set-Location apps\training_web
npm.cmd run dev
```

Open `http://127.0.0.1:5174`. Vite proxies `/api` to the local service on port `8001`.

## Implemented scope

- T1: public-safe Case configuration, deterministic anomaly playback, and CAD-style scene controls.
- T2: Tutor requests with visible `LLM` / `SAFE FALLBACK` delivery mode.
- T4A: one page-lifetime Session, Evidence release, initial/revised Hypothesis flow, and `allowed_actions`-driven controls.
- T4B: create-once Diagnosis submission, released-Evidence citations, explicit API error recovery, and the authoritative five-dimension Training Report.
- Legacy `apps/demo` remains available during migration and is not imported by this application.

Evidence values are rendered only after the matching Evidence request succeeds. Failed learning and Diagnosis commands keep the current Session snapshot, released Evidence, Hypothesis history, and draft input intact.

The Report UI renders backend-owned assessment, scores, coverage, rationales, and Tutor mode without recalculation. A `not_assessed` dimension is shown as “未评价 / 无评价机会”, never as a zero score.

## Verification

With the API and Vite development servers running:

```powershell
Set-Location apps\training_web
npm.cmd run build
node e2e\smoke-ci.mjs
```

The browser suite covers animation continuity, T4A learning operations, create-once Diagnosis, Report retry, all four assessment outcomes, 409/422 recovery, Tutor delivery modes, and complete Diagnosis/Report flows at 1280 x 720, 768 x 1024, and 390 x 844.
