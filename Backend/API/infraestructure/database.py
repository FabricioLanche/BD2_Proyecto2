import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

class DatabaseRepository:
    def __init__(self):
        # falta conectar con el multimodal 
        pass

    def get_product_metadata(self, doc_id: str):
        # para testear
        mock_db = {
            "1": {
                "ProductDisplayName": "Ashwood Curved Dining Chair",
                "masterCategory": "Furniture",
                "image_url": "/link/silla.jpg",
                "gender": "Unisex",
                "subcategory": "Seating",
                "articletype": "Chairs",
                "baseColour": "Ash Brown",
                "season": "All Season",
                "year": "2024",
                "usage": "Casual"
            },
            "2": {
                "ProductDisplayName": "Ashwood Curved Dining Chair2",
                "masterCategory": "Furniture",
                "image_url": "/link/silla.jpg",
                "gender": "Unisex",
                "subcategory": "Seating",
                "articletype": "Chairs",
                "baseColour": "Ash Brown",
                "season": "All Season",
                "year": "2024",
                "usage": "Casual"
            }
            
        }
        return mock_db.get(str(doc_id), mock_db["1"])