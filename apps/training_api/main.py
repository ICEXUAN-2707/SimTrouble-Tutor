"""FastAPI boundary for the Product v0.4 training application."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import SceneConfiguration
from .scene_service import SceneNotFoundError, SceneRepository


def create_app(repository: SceneRepository | None = None) -> FastAPI:
    scenes = repository or SceneRepository()
    application = FastAPI(
        title="SimTrouble Tutor API",
        version="0.4.0",
        description="Case-driven CAD scene and learning orchestration boundary.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5174", "http://localhost:5174"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @application.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.4.0"}

    @application.get(
        "/api/v0.4/cases/{case_id}/scene",
        response_model=SceneConfiguration,
    )
    def get_scene(case_id: str) -> SceneConfiguration:
        try:
            return scenes.load(case_id)
        except SceneNotFoundError as exc:
            raise HTTPException(status_code=404, detail="scene_not_found") from exc

    return application


app = create_app()
