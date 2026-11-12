import asyncio
import logging
import uuid
from app.admin.routes import router as admin_router
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.auth.routes import router as auth_router
from app.claims.routes import router as claims_router
from app.core.auth import get_current_admin
from app.core.config import settings
from app.core.supabase_client import get_supabase
from app.jobs.expiry_worker import run_expiry_and_timeout_sweep
from app.listings.routes import router as listings_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sharemeal.api")


async def _expiry_loop():
    while True:
        try:
            await asyncio.to_thread(run_expiry_and_timeout_sweep)
        except Exception:
            logger.exception("Scheduled expiry sweep failed")
        await asyncio.sleep(settings.EXPIRY_SWEEP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate()  # fail fast; do not serve traffic with invalid configuration
    task = asyncio.create_task(_expiry_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="ShareMeal API", description="Backend API for ShareMeal", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request could not be completed"
    return JSONResponse(status_code=exc.status_code,
                        content={"error": {"code": f"HTTP_{exc.status_code}", "message": message,
                                           "request_id": getattr(request.state, "request_id", None)}},
                        headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR",
                        "message": "Request validation failed", "fields": jsonable_encoder(exc.errors()),
                        "request_id": getattr(request.state, "request_id", None)}})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled request error request_id=%s", getattr(request.state, "request_id", "unknown"))
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected internal server error occurred",
                        "request_id": getattr(request.state, "request_id", None)}})


app.include_router(listings_router)
app.include_router(auth_router)
app.include_router(claims_router)
app.include_router(admin_router)

@app.get("/")
def root():
    return {"message": "Welcome to ShareMeal API", "status": "running", "version": "1.0.0"}


@app.get("/health")
def health():
    try:
        get_supabase().table("food_listings").select("id").limit(1).execute()
        return {"status": "healthy", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database service unavailable")


@app.post("/jobs/trigger-sweep", tags=["Admin Jobs"])
def trigger_expiry_sweep(_admin=Depends(get_current_admin)):
    return {"message": "Expiry sweep completed", "results": run_expiry_and_timeout_sweep()}
