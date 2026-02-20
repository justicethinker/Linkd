import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .routers import onboarding, interactions, feedback, jobs, async_interactions
from . import db

# basic logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    try:
        db.init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    yield
    # Shutdown logic here if needed


app = FastAPI(title="Linkd Backend", lifespan=lifespan)


# middleware to attach a correlation_id to each request
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    logger.info(f"[correlation={correlation_id}] {request.method} {request.url.path}")
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# include routers
app.include_router(onboarding.router)
app.include_router(interactions.router)
app.include_router(feedback.router)
app.include_router(jobs.router)
app.include_router(async_interactions.router)  # Phase 2: Async workflow endpoints


@app.get("/")
def root():
    return {"message": "Linkd backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
