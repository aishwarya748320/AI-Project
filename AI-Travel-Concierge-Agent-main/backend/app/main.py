from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db, SessionLocal
from app.models.flight import Flight
from app.seeds.run_seed import seed_database
from app.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    init_db()
    
    # Auto-seed if database is currently empty
    db = SessionLocal()
    try:
        flight_count = db.query(Flight).count()
        if flight_count == 0:
            print("Database empty. Auto-seeding initial flight and hotel inventory...")
            seed_database(clear_existing=False)
    except Exception as e:
        print(f"Startup database check note: {e}")
    finally:
        db.close()
        
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Goal-Based Intelligent Concierge Agent API for automated flight and hotel travel recommendations. "
        "Evaluates simulated travel packages, enforces hard constraints, minimizes total package cost in INR, "
        "and provides deterministic tie-breaking and explainability."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS for local frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centralized Error Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "ERROR",
            "message": exc.detail,
            "path": request.url.path,
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join([str(x) for x in err.get("loc", [])])
        msg = err.get("msg")
        errors.append(f"{loc}: {msg}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "status": "VALIDATION_ERROR",
            "message": "Input validation failed for travel requirements.",
            "details": errors,
            "path": request.url.path,
        },
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "INTERNAL_ERROR",
            "message": "An unexpected server error occurred.",
            "detail": str(exc) if settings.DEBUG else None,
            "path": request.url.path,
        },
    )

# Mount API routes (with /api prefix and root fallback)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(api_router)

@app.get("/")
def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
        "status": "active"
    }
