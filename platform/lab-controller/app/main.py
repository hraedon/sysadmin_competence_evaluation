import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .database import init_db, get_db, LabHeartbeat
from .schemas import settings
from .middleware.rate_limit import limiter
from .services.lab_service import (
    load_environments,
    reap_expired_sessions_wrapper,
    reconcile_environments_wrapper
)
from .routers import lab, admin, evaluate_v2, auth, profile

# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    await load_environments()
    
    # Start background jobs
    scheduler = BackgroundScheduler()
    scheduler.add_job(reap_expired_sessions_wrapper, 'interval', minutes=1)
    scheduler.add_job(reconcile_environments_wrapper, 'interval', minutes=settings.reconcile_interval_minutes)
    scheduler.start()
    app.state.scheduler = scheduler
    
    yield
    
    # Shutdown
    scheduler.shutdown()

app = FastAPI(title="Sysadmin Competency Lab Controller", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS: allow frontend dev server (localhost:5173) and production origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "https://learning.hraedon.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(lab.router)
app.include_router(admin.router)
app.include_router(evaluate_v2.router)
app.include_router(auth.router)
app.include_router(profile.router)

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    heartbeats = db.query(LabHeartbeat).all()
    return {
        "status": "healthy",
        "jobs": {hb.job_name: {"last_run": hb.last_run_at, "status": hb.last_status, "error": hb.last_error} for hb in heartbeats}
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
