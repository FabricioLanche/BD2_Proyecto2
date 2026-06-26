import sys
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from API.service.search_service import SearchService
except Exception:
    from service.search_service import SearchService

router = APIRouter()
search_service = SearchService()

@router.post("/visual")
async def visual_search(
    image: UploadFile = File(...),
    top_k: int = Form(10)
):
    image_bytes = await image.read()
    results = search_service.execute_visual_search(image_bytes, top_k)
    return {"results": results}

@router.post("/multimodal")
async def multimodal_search(
    image: UploadFile = File(None),
    text_query: str = Form(""),
    weight_visual: float = Form(0.6),
    weight_text: float = Form(0.4),
    top_k: int = Form(10)
):
    image_bytes = await image.read() if image else None
    results = search_service.execute_multimodal_search(
        image_bytes, text_query, weight_visual, weight_text, top_k
    )
    return {"results": results}