import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from backend.database import init_db
from backend.routers import admin, game, user


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("✅ FastAPI started, DB initialized")
    yield
    print("👋 FastAPI shutting down")


app = FastAPI(
    title="Casino Bot API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(admin.router)
app.include_router(game.router)
app.include_router(user.router)

# Serve static files
webapp_dir = os.path.join(os.path.dirname(__file__), "..", "webapp")
admin_dir = os.path.join(os.path.dirname(__file__), "..", "admin")

if os.path.exists(webapp_dir):
    app.mount("/webapp", StaticFiles(directory=webapp_dir, html=True), name="webapp")
if os.path.exists(admin_dir):
    app.mount("/admin", StaticFiles(directory=admin_dir, html=True), name="admin")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/")
async def root():
    return JSONResponse({
        "message": "🎰 Casino Bot API",
        "webapp": "/webapp/",
        "admin": "/admin/",
        "docs": "/docs"
    })
