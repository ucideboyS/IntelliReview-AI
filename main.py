import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.database import init_db
from app.routes.review import router as review_router
from app.middleware.rate_limiter import RateLimiterMiddleware

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── ENV CONFIG ─────────────────────────────────────────────────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    if _raw_origins != "*" else ["*"]
)
PRODUCTION = os.getenv("PRODUCTION", "false").lower() == "true"

# ── STARTUP TOKEN CHECK ────────────────────────────────────────────────────
if not os.getenv("GITHUB_TOKEN"):
    logger.warning("GITHUB_TOKEN is not set — AI analysis will fail on all requests.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    try:
        init_db()
        logger.info("Database initialized successfully")
        logger.info(f"CORS origins: {ALLOWED_ORIGINS}")
        logger.info(f"Production mode: {PRODUCTION}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    yield


app = FastAPI(
    title="IntelliReview AI",
    description="AI-powered code review and analysis service",
    version="2.0.0",
    lifespan=lifespan,
    docs_url=None if PRODUCTION else "/docs",
    redoc_url=None if PRODUCTION else "/redoc",
)

# ── MIDDLEWARE (rate limiter must be before CORS) ──────────────────────────
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─�� STATIC + TEMPLATES ─────────────────────────────────────────────────────
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ── ROUTERS ────────────────────────────────────────────────────────────────
app.include_router(review_router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main UI."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Hides stack traces in production."""
    logger.error(
        f"Unhandled exception on {request.url.path}: "
        f"{type(exc).__name__}: {exc}"
    )
    if PRODUCTION:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error."}
        )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error.", "detail": str(exc)}
    )

    if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)