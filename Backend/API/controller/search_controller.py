import sys
from pathlib import Path
from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Query 

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
    search_type: str = Query("spimi", description="Tipos: spimi, postgres")
):
    image_bytes = await image.read()
    response_data = _svc(request).execute_visual_search(image_bytes, top_k, search_type)
    return response_data


@router.post("/multimodal")
async def multimodal_search(
    request: Request,
    image: UploadFile = File(None),
    text_query: str = Form(""),
    weight_visual: float = Form(60),
    weight_text: float = Form(40),
    top_k: int = Form(10),
    search_type: str = Query("spimi", description="Tipos: spimi, postgres")
):
    image_bytes = await image.read() if image else None

    w_vis = weight_visual / 100.0 if weight_visual > 1.0 else weight_visual
    w_txt = weight_text / 100.0 if weight_text > 1.0 else weight_text

    response_data  = _svc(request).execute_multimodal_search(
        image_bytes, text_query, w_vis, w_txt, top_k, search_type
    )
    return response_data


@router.get("/details/{doc_id}")
async def get_details(request: Request, doc_id: str):
    details = _svc(request).get_product_details(doc_id)
    if not details:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"product": details}