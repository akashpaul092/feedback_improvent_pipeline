"""FastAPI application - AI Agent Evaluation Pipeline."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import conversations, evaluations, feedback, queue
from app.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize on startup - run migrations to create/update tables."""
    init_db()
    yield


app = FastAPI(
    title="AI Agent Evaluation Pipeline",
    description="Automated evaluation pipeline for AI agents in production",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversations.router)
app.include_router(evaluations.router)
app.include_router(feedback.router)
app.include_router(queue.router)


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "AI Agent Evaluation Pipeline"}


@app.get("/health")
def health():
    """Health check for load balancers."""
    return {"status": "healthy"}
