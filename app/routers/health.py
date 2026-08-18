from fastapi import APIRouter, status
from app.core.config import settings
from app.core.database import check_database_connection
from app.schemas.common import DatabaseHealth, HealthData, HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Check",
    description="Returns application health status, environment info, and database connectivity diagnostic.",
)
def get_health() -> HealthResponse:
    db_status = check_database_connection()
    is_healthy = db_status["connected"]

    health_data = HealthData(
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        status="healthy" if is_healthy else "degraded",
        database=DatabaseHealth(
            connected=db_status["connected"],
            message=db_status["message"],
        ),
    )

    return HealthResponse(
        success=True,
        message="System operational" if is_healthy else "System running with degraded database connectivity",
        data=health_data,
    )
