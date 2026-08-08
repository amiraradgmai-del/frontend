
import logging

from fastapi import APIRouter, Request, Response, status
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.system import HealthResponse, ReadinessResponse, StatusResponse

router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
def readiness(request: Request, response: Response) -> ReadinessResponse:
    try:
        request.app.state.database.ping()
    except SQLAlchemyError:
        logger.warning("database_readiness_failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="not_ready", database="down")
    return ReadinessResponse(status="ready", database="up")


@router.get("/api/v1/status", response_model=StatusResponse)
def service_status(request: Request) -> StatusResponse:
    settings = request.app.state.settings
    return StatusResponse(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        status="operational",
    )
