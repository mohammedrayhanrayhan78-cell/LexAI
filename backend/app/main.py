from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.rag import router as rag_router
from app.api.v1.documents import router as documents_router
from app.api.v1.voice import router as voice_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_is_prod = settings.ENVIRONMENT.lower() == "production"

app = FastAPI(
    title="Legal AI Assistant API",
    version="1.0.0",
    docs_url=None if _is_prod else "/docs",
    redoc_url=None if _is_prod else "/redoc",
    openapi_url=None if _is_prod else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
app.include_router(rag_router, prefix="/api/v1", tags=["RAG Documents"])
app.include_router(documents_router, prefix="/api/v1", tags=["Documents"])
app.include_router(voice_router, prefix="/api/v1", tags=["Voice"])

@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Starting up Legal AI Assistant backend server...")

@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info("Shutting down Legal AI Assistant backend server...")