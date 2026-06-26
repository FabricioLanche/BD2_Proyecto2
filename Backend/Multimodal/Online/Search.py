import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

class SearchEngine:
    def __init__(self):
        pass

    def search_image(self, image_bytes: bytes, top_k: int):
        # Temporal para testear
        return [("1", 0.85), ("2", 0.74)]

    def search_multimodal(self, image_bytes: Optional[bytes], text_query: str, weight_visual: float, weight_text: float, top_k: int):
        # Temporal para testear
        return [("1", 0.92), ("2", 0.65)]