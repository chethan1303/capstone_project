"""
PI-EWS — FastAPI Application Entry Point.

Mounts all routers, configures CORS, and initializes the database on startup.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.conversations import router as conversations_router
from routes.admin import router as admin_router
from routes.roles import router as roles_router
from routes.analyst import router as analyst_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    await init_db()
    print("MongoDB connected and Beanie initialized")
    yield


app = FastAPI(
    title="PI-EWS API",
    description="Prompt Injection Early Warning System — LLM Honeypot Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(admin_router)
app.include_router(roles_router)
app.include_router(analyst_router)


@app.get("/")
def root():
    return {
        "name": "PI-EWS API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}
