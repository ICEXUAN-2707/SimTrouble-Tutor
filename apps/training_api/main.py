"""FastAPI boundary for the Product v0.4 training application."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from core.errors import EvidenceNotFoundError

from .models import SceneConfiguration
from .scene_service import SceneNotFoundError, SceneRepository
from .session_models import (
    CreateSessionRequest,
    EvidenceRequest,
    EvidenceResponse,
    HypothesisRequest,
    SessionView,
)
from .session_repository import SessionNotFoundError
from .session_service import (
    CaseNotFoundError,
    SessionService,
    SessionStageConflictError,
)


def create_app(
    repository: SceneRepository | None = None,
    session_service: SessionService | None = None,
) -> FastAPI:
    scenes = repository or SceneRepository()
    sessions = session_service or SessionService()
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

    @application.post(
        "/api/v0.4/sessions",
        response_model=SessionView,
        status_code=status.HTTP_201_CREATED,
    )
    def create_session(request: CreateSessionRequest) -> SessionView:
        try:
            return sessions.create(request.case_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=404, detail="case_not_found") from exc

    @application.get(
        "/api/v0.4/sessions/{session_id}",
        response_model=SessionView,
    )
    def get_session(session_id: str) -> SessionView:
        try:
            return sessions.get(session_id)
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail="session_not_found") from exc

    @application.post(
        "/api/v0.4/sessions/{session_id}/evidence",
        response_model=EvidenceResponse,
    )
    def request_evidence(
        session_id: str,
        request: EvidenceRequest,
    ) -> EvidenceResponse:
        try:
            return sessions.request_evidence(session_id, request.evidence_id)
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail="session_not_found") from exc
        except EvidenceNotFoundError as exc:
            raise HTTPException(status_code=404, detail="evidence_not_found") from exc
        except SessionStageConflictError as exc:
            raise HTTPException(status_code=409, detail="invalid_session_stage") from exc

    @application.post(
        "/api/v0.4/sessions/{session_id}/hypotheses",
        response_model=SessionView,
    )
    def submit_hypothesis(
        session_id: str,
        request: HypothesisRequest,
    ) -> SessionView:
        try:
            return sessions.submit_hypothesis(session_id, request.hypothesis)
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail="session_not_found") from exc
        except SessionStageConflictError as exc:
            raise HTTPException(status_code=409, detail="invalid_session_stage") from exc

    return application


app = create_app()
