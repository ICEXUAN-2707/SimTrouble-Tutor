"""FastAPI boundary for the Product v0.4 training application."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.errors import EvidenceNotFoundError

from .auth import (
    AuthSessionV05,
    AuthenticationContext,
    AuthenticationStore,
    LoginRequest,
    RegisterRequest,
    UsernameUnavailableError,
)
from .auth.repository import IssuedAuthentication, SESSION_TTL_SECONDS
from .evaluation import DiagnosisService, build_diagnosis_service
from .evaluation.repository import (
    DiagnosisAlreadySubmittedError,
    ReportNotReadyError,
)
from .learning_models import DiagnosisSubmission, TrainingReportV04
from .models import SceneConfiguration
from .scene_service import SceneNotFoundError, SceneRepository
from .session_models import (
    CreateSessionRequest,
    EvidenceRequest,
    EvidenceResponse,
    HypothesisRequest,
    SessionView,
    TutorTurnRequest,
    TutorTurnResponse,
)
from .session_repository import SessionNotFoundError
from .session_service import (
    CaseNotFoundError,
    DiagnosisEvidenceError,
    SessionService,
    SessionStageConflictError,
)
from .tutor import TutorService, build_tutor_service
from .training_records import TrainingRecordStore


AUTH_COOKIE_NAME = "simtrouble_auth"
CSRF_COOKIE_NAME = "simtrouble_csrf"
_BOOLEAN_ENVIRONMENT_VALUES = {
    "0": False,
    "1": True,
    "false": False,
    "no": False,
    "true": True,
    "yes": True,
}


def _read_boolean_environment(name: str, *, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return _BOOLEAN_ENVIRONMENT_VALUES[raw.lower()]
    except KeyError as exc:
        allowed = ", ".join(_BOOLEAN_ENVIRONMENT_VALUES)
        raise ValueError(f"{name} must be one of: {allowed}") from exc


def create_app(
    repository: SceneRepository | None = None,
    session_service: SessionService | None = None,
    tutor_service: TutorService | None = None,
    diagnosis_service: DiagnosisService | None = None,
    authentication_store: AuthenticationStore | None = None,
) -> FastAPI:
    secure_cookies = _read_boolean_environment(
        "SIMTROUBLE_COOKIE_SECURE", default=False
    )
    scenes = repository or SceneRepository()
    sessions = session_service or SessionService()
    tutor = tutor_service or build_tutor_service(sessions)
    authentication = authentication_store or AuthenticationStore()
    authentication.initialize()
    diagnosis = diagnosis_service or build_diagnosis_service(
        sessions, records=TrainingRecordStore(authentication.database_path)
    )
    application = FastAPI(
        title="SimTrouble Tutor API",
        version="0.5.0",
        description="Case-driven learning orchestration with local identity.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5174", "http://localhost:5174"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        if request.url.path == "/api/v0.5/auth/register":
            return JSONResponse(status_code=400, content={"detail": "invalid_registration"})
        if request.url.path == "/api/v0.5/auth/login":
            return JSONResponse(status_code=401, content={"detail": "invalid_credentials"})
        return await request_validation_exception_handler(request, exc)

    def require_auth(request: Request) -> AuthenticationContext:
        token = request.cookies.get(AUTH_COOKIE_NAME)
        context = authentication.resolve(token) if token else None
        if context is None:
            raise HTTPException(status_code=401, detail="authentication_required")
        return context

    def require_csrf(request: Request, context: AuthenticationContext) -> str:
        header = request.headers.get("X-CSRF-Token")
        cookie = request.cookies.get(CSRF_COOKIE_NAME)
        if (
            not header
            or not cookie
            or header != cookie
            or not authentication.csrf_matches(context, header)
        ):
            raise HTTPException(status_code=403, detail="csrf_validation_failed")
        return header

    def set_auth_cookies(response: Response, issued: IssuedAuthentication) -> None:
        response.set_cookie(
            AUTH_COOKIE_NAME,
            issued.token,
            max_age=SESSION_TTL_SECONDS,
            httponly=True,
            secure=secure_cookies,
            samesite="lax",
            path="/",
        )
        response.set_cookie(
            CSRF_COOKIE_NAME,
            issued.csrf_token,
            max_age=SESSION_TTL_SECONDS,
            httponly=False,
            secure=secure_cookies,
            samesite="lax",
            path="/",
        )

    def auth_response(issued: IssuedAuthentication) -> AuthSessionV05:
        return AuthSessionV05(
            user=issued.user,
            expires_at=issued.expires_at,
            csrf_token=issued.csrf_token,
        )

    @application.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.5.0"}

    @application.post(
        "/api/v0.5/auth/register",
        response_model=AuthSessionV05,
        status_code=status.HTTP_201_CREATED,
    )
    def register(request: RegisterRequest, response: Response) -> AuthSessionV05:
        try:
            user = authentication.create_user(
                username=request.username,
                password=request.password,
                display_name=request.display_name,
            )
        except UsernameUnavailableError as exc:
            raise HTTPException(status_code=409, detail="username_unavailable") from exc
        issued = authentication.issue_session(user)
        set_auth_cookies(response, issued)
        return auth_response(issued)

    @application.post("/api/v0.5/auth/login", response_model=AuthSessionV05)
    def login(request: LoginRequest, response: Response) -> AuthSessionV05:
        user = authentication.authenticate(request.username, request.password)
        if user is None:
            raise HTTPException(status_code=401, detail="invalid_credentials")
        issued = authentication.issue_session(user)
        set_auth_cookies(response, issued)
        return auth_response(issued)

    @application.get("/api/v0.5/auth/me", response_model=AuthSessionV05)
    def current_identity(request: Request) -> AuthSessionV05:
        context = require_auth(request)
        csrf_token = request.cookies.get(CSRF_COOKIE_NAME)
        if not csrf_token or not authentication.csrf_matches(context, csrf_token):
            raise HTTPException(status_code=401, detail="authentication_required")
        return AuthSessionV05(
            user=context.user,
            expires_at=context.expires_at,
            csrf_token=csrf_token,
        )

    @application.post("/api/v0.5/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(request: Request, response: Response) -> None:
        context = require_auth(request)
        require_csrf(request, context)
        token = request.cookies.get(AUTH_COOKIE_NAME)
        assert token is not None
        authentication.revoke_session(token)
        response.delete_cookie(
            AUTH_COOKIE_NAME, path="/", secure=secure_cookies, samesite="lax"
        )
        response.delete_cookie(
            CSRF_COOKIE_NAME, path="/", secure=secure_cookies, samesite="lax"
        )

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

    @application.post(
        "/api/v0.4/sessions/{session_id}/tutor",
        response_model=TutorTurnResponse,
    )
    async def ask_tutor(
        session_id: str,
        request: TutorTurnRequest,
    ) -> TutorTurnResponse:
        try:
            return await tutor.ask(session_id, request.message)
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail="session_not_found") from exc

    @application.post(
        "/api/v0.4/sessions/{session_id}/diagnosis",
        response_model=SessionView,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def submit_diagnosis(
        session_id: str,
        request: DiagnosisSubmission,
    ) -> SessionView:
        try:
            return diagnosis.submit(session_id, request)
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail="session_not_found") from exc
        except SessionStageConflictError as exc:
            raise HTTPException(status_code=409, detail="invalid_session_stage") from exc
        except DiagnosisAlreadySubmittedError as exc:
            raise HTTPException(
                status_code=409,
                detail="diagnosis_already_submitted",
            ) from exc
        except DiagnosisEvidenceError as exc:
            raise HTTPException(
                status_code=422,
                detail="invalid_evidence_reference",
            ) from exc

    @application.get(
        "/api/v0.4/sessions/{session_id}/report",
        response_model=TrainingReportV04,
    )
    def get_report(session_id: str) -> TrainingReportV04:
        try:
            return diagnosis.report(session_id)
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail="session_not_found") from exc
        except ReportNotReadyError as exc:
            raise HTTPException(status_code=409, detail="report_not_ready") from exc

    @application.post(
        "/api/v0.5/sessions",
        response_model=SessionView,
        status_code=status.HTTP_201_CREATED,
    )
    def create_owned_session(request: Request, body: CreateSessionRequest) -> SessionView:
        context = require_auth(request)
        require_csrf(request, context)
        try:
            return sessions.create(body.case_id, user_id=context.user.user_id)
        except CaseNotFoundError as exc:
            raise HTTPException(status_code=404, detail="case_not_found") from exc

    @application.get(
        "/api/v0.5/sessions/{session_id}", response_model=SessionView
    )
    def get_owned_session(request: Request, session_id: str) -> SessionView:
        context = require_auth(request)
        try:
            return diagnosis.get_session(session_id, user_id=context.user.user_id)
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail="session_not_found") from exc

    @application.post(
        "/api/v0.5/sessions/{session_id}/evidence",
        response_model=EvidenceResponse,
    )
    def request_owned_evidence(
        request: Request, session_id: str, body: EvidenceRequest
    ) -> EvidenceResponse:
        context = require_auth(request)
        require_csrf(request, context)
        try:
            return sessions.request_evidence(
                session_id, body.evidence_id, user_id=context.user.user_id
            )
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail="session_not_found") from exc
        except EvidenceNotFoundError as exc:
            raise HTTPException(status_code=404, detail="evidence_not_found") from exc
        except SessionStageConflictError as exc:
            raise HTTPException(status_code=409, detail="invalid_session_stage") from exc

    @application.post(
        "/api/v0.5/sessions/{session_id}/hypotheses",
        response_model=SessionView,
    )
    def submit_owned_hypothesis(
        request: Request, session_id: str, body: HypothesisRequest
    ) -> SessionView:
        context = require_auth(request)
        require_csrf(request, context)
        try:
            return sessions.submit_hypothesis(
                session_id, body.hypothesis, user_id=context.user.user_id
            )
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail="session_not_found") from exc
        except SessionStageConflictError as exc:
            raise HTTPException(status_code=409, detail="invalid_session_stage") from exc

    @application.post(
        "/api/v0.5/sessions/{session_id}/tutor",
        response_model=TutorTurnResponse,
    )
    async def ask_owned_tutor(
        request: Request, session_id: str, body: TutorTurnRequest
    ) -> TutorTurnResponse:
        context = require_auth(request)
        require_csrf(request, context)
        try:
            return await tutor.ask(
                session_id, body.message, user_id=context.user.user_id
            )
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail="session_not_found") from exc

    @application.post(
        "/api/v0.5/sessions/{session_id}/diagnosis",
        response_model=SessionView,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def submit_owned_diagnosis(
        request: Request, session_id: str, body: DiagnosisSubmission
    ) -> SessionView:
        context = require_auth(request)
        require_csrf(request, context)
        try:
            return diagnosis.submit(
                session_id, body, user_id=context.user.user_id
            )
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail="session_not_found") from exc
        except SessionStageConflictError as exc:
            raise HTTPException(status_code=409, detail="invalid_session_stage") from exc
        except DiagnosisAlreadySubmittedError as exc:
            raise HTTPException(
                status_code=409, detail="diagnosis_already_submitted"
            ) from exc
        except DiagnosisEvidenceError as exc:
            raise HTTPException(
                status_code=422, detail="invalid_evidence_reference"
            ) from exc

    @application.get(
        "/api/v0.5/sessions/{session_id}/report",
        response_model=TrainingReportV04,
    )
    def get_owned_report(request: Request, session_id: str) -> TrainingReportV04:
        context = require_auth(request)
        try:
            return diagnosis.report(session_id, user_id=context.user.user_id)
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail="session_not_found") from exc
        except ReportNotReadyError as exc:
            raise HTTPException(status_code=409, detail="report_not_ready") from exc

    return application


app = create_app()
