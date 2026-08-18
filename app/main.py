import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.routers import health
from app.routers.api_v1 import api_v1_router
from app.utils.logging import setup_logging

# Configure logging
setup_logging(debug=settings.DEBUG)
logger = logging.getLogger(__name__)

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOADS_DIR = PROJECT_ROOT / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
(UPLOADS_DIR / "products").mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for startup and shutdown procedures.
    """
    logger.info("Starting %s v%s in [%s] mode...", settings.PROJECT_NAME, settings.VERSION, settings.ENVIRONMENT)
    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)


# Initialize FastAPI Application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-grade SaaS Multi-Vendor E-Commerce Platform API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS Middleware Configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register Global Exception Handlers
register_exception_handlers(app)

# Mount Static Files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount Uploads
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Configure Jinja2 Templates Engine
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Mount API Routers
app.include_router(api_v1_router, prefix=settings.API_V1_STR)
app.include_router(health.router)  # Direct /health root alias


@app.get("/", response_class=HTMLResponse, tags=["Web UI"], include_in_schema=False)
async def root_view(request: Request):
    """Landing and foundation status view rendered via Jinja2."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request, "project_name": settings.PROJECT_NAME},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
