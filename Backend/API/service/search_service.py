import os
import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Multimodal.Online.Orquestador import OnlineOrchestrator

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "multimodal"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "123456"),
}


class SearchService:
    def __init__(self, db_config: Optional[dict] = None, n_documents: Optional[int] = None):
        self._orchestrator: Optional[OnlineOrchestrator] = None
        self._db_config = db_config or DB_CONFIG
        self._n_documents = n_documents if n_documents is not None else int(os.getenv("DATASET_SIZE", "1000"))

    @property
    def orchestrator(self) -> OnlineOrchestrator:
        """Singleton: se crea una sola vez al primer acceso."""
        if self._orchestrator is None:
            self._orchestrator = OnlineOrchestrator(self._db_config, n_documents=self._n_documents)
        return self._orchestrator

    def execute_visual_search(self, image_bytes: bytes, top_k: int) -> list[dict]:
        img = self._decode_image(image_bytes)
        raw_results = self.orchestrator.search_image(img, k=top_k)
        return self._format_search_results(raw_results)

    def execute_multimodal_search(
        self,
        image_bytes: Optional[bytes],
        text_query: str,
        weight_visual: float,
        weight_text: float,
        top_k: int,
    ) -> list[dict]:
        img = self._decode_image(image_bytes) if image_bytes else None
        if img is not None and text_query:
            raw_results = self.orchestrator.search_multimodal(
                text_query, img, text_weight=weight_text, image_weight=weight_visual, k=top_k
            )
        elif img is not None:
            raw_results = self.orchestrator.search_image(img, k=top_k)
        else:
            raw_results = self.orchestrator.search_text(text_query, k=top_k)
            
        return self._format_search_results(raw_results)

    def close(self) -> None:
        if self._orchestrator is not None:
            self._orchestrator.close()
            self._orchestrator = None

    def _format_search_results(self, raw_results: list[dict]) -> list[dict]:
        """Convierte el formato del orquestador al formato que espera el frontend en las búsquedas"""
        formatted = []
        for r in raw_results:
            formatted.append({
                "id": str(r["doc_id"]),
                "name": r.get("product_name") or "Unknown",
                "match_percentage": f"{int(r['score'] * 100)}%"
            })
        return formatted

    def get_product_details(self, doc_id: str) -> Optional[dict]:
        """Convierte el formato del orquestador al formato anidado que espera la vista de detalles"""
        meta = self.orchestrator.recover_by_ids([int(doc_id)])
        entry = meta.get(int(doc_id))
        if entry is None:
            return None
            
        url, texto = entry
        from Multimodal.Online.Orquestador import OnlineOrchestrator as _O
        fields = _O._parse_texto(texto)
        
        return {
            "id": doc_id,
            "name": fields.get("product_name", "Unknown"),
            "category": fields.get("master_category", ""),
            "image_url": url or "",
            "details": {
                "gender": fields.get("gender", ""),
                "subcategory": fields.get("sub_category", ""),
                "type": fields.get("article_type", ""),
                "colour": fields.get("base_colour", ""),
                "season": fields.get("season", ""),
                "year": fields.get("year", ""),
                "usage": fields.get("usage", "")
            }
        }

    @staticmethod
    def _decode_image(image_bytes: bytes) -> np.ndarray:
        img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("No se pudo decodificar la imagen recibida.")
        return img