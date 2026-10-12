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

## Scope

- T1: public-safe Case configuration, deterministic anomaly playback, CAD-style scene controls.
- T2: the visible Tutor area is an explicit placeholder; no LLM answer is simulated in T1.
- Legacy `apps/demo` remains available during migration and is not imported by this application.
