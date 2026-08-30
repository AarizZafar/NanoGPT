from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(title="NanoGPT", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://cae-nanogpt-prod.happyisland-c2178764.eastus.azurecontainerapps.io",
    ],
    allow_origin_regex=r"https://.*\.azurestaticapps\.net",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
'''
    This one line registers ALL routes defined in routes.py onto the app — with /api prepended.
    /api/upload
    /api/train
    /api/generate
    /api/status
    /api/ws/loss

    Why we need it - Nginx routing.
    location /api/ {
        proxy_pass http://app;   ← goes to FastAPI
    }

    location / {
        proxy_pass http://app;   ← also goes to FastAPI (serves index.html)
    }

    The /api/ prefix lets Nginx clearly distinguish — "this is an API call" vs "this is a page request."
'''

app.mount("/static", StaticFiles(directory="frontend"), name="static") # Tells FastAPI anything under /static/... serve directly from the frontend/ folder on disk. No Python code runs, just raw file serving.
@app.get("/")                                                          # The one route defined directly on main.py serves frontend/index.html when the browser hits the root URL.
async def root():
    '''
        When browser hits http://localhost/ — this function runs and sends back the frontend/index.html
        With this:
        GET /  →  returns index.html  →  browser renders the UI
    '''
    return FileResponse("frontend/index.html")


'''
request hits Uvicorn
  → FastAPI checks URL
      /          → returns index.html
      /api/...   → router handles it (routes.py)
      /static/.. → serves file from frontend/ folder
'''
