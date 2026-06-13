# STATUS: COMPLETE
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import CORS_ORIGINS
from scheduler import start_scheduler
from api import niches, keywords, opportunities, competitors, community, reports, scheduler_status

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield

app = FastAPI(title="AOIP — App Opportunity Intelligence Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(niches.router, prefix="/api/niches", tags=["niches"])
app.include_router(keywords.router, prefix="/api/keywords", tags=["keywords"])
app.include_router(opportunities.router, prefix="/api/opportunities", tags=["opportunities"])
app.include_router(competitors.router, prefix="/api/competitors", tags=["competitors"])
app.include_router(community.router, prefix="/api/community", tags=["community"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(scheduler_status.router, prefix="/api/scheduler", tags=["scheduler"])
