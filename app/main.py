from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, chat
from app.core.config import settings
from app.core.lifespan import lifespan

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="OpenAI-compatible LLM gateway with routing, rate limits, caching, and fallback",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, tags=["OpenAI Compatible"])
app.include_router(admin.router, tags=["Admin"])

try:
    app.mount("/dashboard", StaticFiles(directory="frontend", html=True), name="dashboard")
except RuntimeError:
    pass
