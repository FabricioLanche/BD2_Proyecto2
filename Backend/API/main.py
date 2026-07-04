import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from API.controller import search_controller
    from API.service.search_service import SearchService
except Exception:
    from controller import search_controller
    from service.search_service import SearchService


@asynccontextmanager
async def lifespan(app: FastAPI):
    svc = SearchService()
    _ = svc.orchestrator
    app.state.search_service = svc
    yield
    svc.close()


app = FastAPI(
    title="BD2 Proyecto 2 - Motor de Búsqueda Multimodal",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search_controller.router, prefix="/api", tags=["Search"])

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Backend Multimodal Activo"}