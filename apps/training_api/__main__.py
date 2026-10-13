"""Run the local Product v0.4 API."""

from __future__ import annotations

import uvicorn


if __name__ == "__main__":
    uvicorn.run("apps.training_api.main:app", host="127.0.0.1", port=8001, reload=False)
