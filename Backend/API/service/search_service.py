import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from API.infraestructure.database import DatabaseRepository

class MockSearchEngine:
    def search_image(self, image_bytes: bytes, top_k: int):
        return [("1", 0.99), ("2", 0.85), ("999", 0.45)]

    def search_multimodal(self, image_bytes: Optional[bytes], text_query: str, weight_visual: float, weight_text: float, top_k: int):
        return [("1", 0.95), ("2", 0.70)]


class SearchService:
    def __init__(self):
        # 2. INSTANCIAMOS EL MOCK, NO EL REAL
        self.search_engine = MockSearchEngine()
        self.db = DatabaseRepository()

    def execute_visual_search(self, image_bytes: bytes, top_k: int):
        ranking = self.search_engine.search_image(image_bytes, top_k)
        return self._enrich_results(ranking)

    def execute_multimodal_search(self, image_bytes: Optional[bytes], text_query: str, weight_visual: float, weight_text: float, top_k: int):
        ranking = self.search_engine.search_multimodal(
            image_bytes, text_query, weight_visual, weight_text, top_k
        )
        return self._enrich_results(ranking)

    def _enrich_results(self, ranking_tuples):
        results = []
        for doc_id, score in ranking_tuples:
            meta = self.db.get_product_metadata(doc_id)
            if not meta:
                continue
                
            match_pct = f"{int(score * 100)}%"
            
            results.append({
                "id": doc_id,
                "name": meta.get("ProductDisplayName", "Unknown"), 
                "image_url": meta.get("image_url", ""),
                "match_percentage": match_pct
            })
        return results

    def get_product_details(self, doc_id: str):
        meta = self.db.get_product_metadata(doc_id)
        if not meta:
            return None
            
        return {
            "id": doc_id,
            "name": meta.get("ProductDisplayName", "Unknown"), 
            "category": meta.get("masterCategory", ""), 
            "image_url": meta.get("image_url", ""),
            "details": {
                "gender": meta.get("gender", ""),
                "subcategory": meta.get("subcategory", ""),
                "type": meta.get("articletype", ""), 
                "colour": meta.get("baseColour", ""), 
                "season": meta.get("season", ""),
                "year": meta.get("year", ""),
                "usage": meta.get("usage", "")
            }
        }