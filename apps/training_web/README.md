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
- Legacy `apps/demo` remains available during migration and is not imported by this application.

Evidence values are rendered only after the matching Evidence request succeeds. Failed learning commands keep the current Session snapshot, released Evidence, Hypothesis history, and draft input intact.

## Verification

With the API and Vite development servers running:

```powershell
Set-Location apps\training_web
npm.cmd run build
node e2e\smoke-ci.mjs
```

The browser suite covers animation continuity, the T4A learning flow, command-error recovery, Tutor delivery modes, and the 390 x 844 viewport.
