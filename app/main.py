import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router

app = FastAPI(title="NanoGPT", version="1.0.0")

frontend_dist = Path(os.getenv("FRONTEND_DIST_DIR", "frontend/dist"))
static_assets = frontend_dist / "assets"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://gentle-ocean-01208a90f.7.azurestaticapps.net",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

if static_assets.exists():
    app.mount("/assets", StaticFiles(directory=static_assets), name="assets")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "status": "ok",
        "message": "Frontend build not found. Run the Vite dev server or build frontend/dist.",
    }
