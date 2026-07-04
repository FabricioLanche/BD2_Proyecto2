import sys
from pathlib import Path
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

router = APIRouter()


def _svc(request: Request):
    """Obtiene el SearchService singleton del lifespan."""
    return request.app.state.search_service


@router.post("/visual")
async def visual_search(
    request: Request,
    image: UploadFile = File(...),
    top_k: int = Form(10),
):
    image_bytes = await image.read()
    results = _svc(request).execute_visual_search(image_bytes, top_k)
    return {"results": results}


@router.post("/multimodal")
async def multimodal_search(
    request: Request,
    image: UploadFile = File(None),
    text_query: str = Form(""),
    weight_visual: float = Form(0.6),
    weight_text: float = Form(0.4),
    top_k: int = Form(10),
):
    image_bytes = await image.read() if image else None
    results = _svc(request).execute_multimodal_search(
        image_bytes, text_query, weight_visual / 100.0, weight_text / 100.0, top_k
    )
    return {"results": results}


@router.get("/details/{doc_id}")
async def get_details(request: Request, doc_id: str):
    details = _svc(request).get_product_details(doc_id)
    if not details:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"product": details}