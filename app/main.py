from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.auth.routes import router as auth_router
from app.claims.routes import router as claims_router
from app.core.config import settings
from app.core.supabase_client import get_supabase
from app.jobs.expiry_worker import run_expiry_and_timeout_sweep
from app.listings.routes import router as listings_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sharemeal.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Validate mandatory configuration
    try:
        settings.validate()
        logger.info("Configuration validated successfully.")
    except Exception as e:
        logger.error(f"Startup configuration error: {e}")
    
    yield
    # Shutdown logic if needed


app = FastAPI(
    title="ShareMeal API",
    description="Backend API for the ShareMeal location-aware food-sharing platform",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "status_code": exc.status_code,
                "message": detail,
            }
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "status_code": 500,
                "message": "An unexpected internal server error occurred. Please try again later.",
            }
        },
    )


# Register API routers
app.include_router(listings_router)
app.include_router(auth_router)
app.include_router(claims_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to ShareMeal API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
def health():
    try:
        client = get_supabase()
        client.table("food_listings").select("id").limit(1).execute()

        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )


@app.post("/jobs/trigger-sweep", tags=["Admin Jobs"])
def trigger_expiry_sweep():
    """Manual endpoint to invoke 15-minute claim expiry and safe_until food sweeps (FR-08, FR-09)."""
    result = run_expiry_and_timeout_sweep()
    return {"message": "Expiry sweep completed", "results": result}