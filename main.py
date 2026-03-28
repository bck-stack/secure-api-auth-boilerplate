"""
FastAPI JWT Authentication Boilerplate
Full auth stack: register, login, refresh token, /me, role-based access.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.database import create_tables
from app.routers import auth, users


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_tables()
    yield


app = FastAPI(
    title="FastAPI JWT Auth",
    description="Production-ready JWT authentication boilerplate with role-based access control.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"status": "ok"}
