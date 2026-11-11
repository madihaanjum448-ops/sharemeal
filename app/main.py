
from fastapi import FastAPI, HTTPException
from app.claims.routes import router as claims_router
from app.core.supabase_client import get_supabase
from app.listings.routes import router as listings_router
from app.auth.routes import router as auth_router


app = FastAPI(
    title="ShareMeal API",
    description="Backend API for the ShareMeal food-sharing platform",
    version="1.0.0",
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
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "unavailable",
            },
        )
