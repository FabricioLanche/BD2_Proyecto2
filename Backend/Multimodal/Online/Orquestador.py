"""
Orquestador ONLINE del pipeline multimodal.

Recibe UNA consulta (texto, imagen o ambos), la transforma en histograma
reutilizando las mismas etapas del offline + los artefactos persistidos
(vocab.pkl, text_codebook.pkl, visual_codebook.pkl), delega el ranking a
Search y enriquece el resultado con metadata desde PostgreSQL.

No reconstruye nada: solo carga lo que dejó el orquestador offline.

Uso:
    python -m Backend.Multimodal.Online.Orquestador --text "blue shirt" --k 10
    python -m Backend.Multimodal.Online.Orquestador --image "C:/ruta/foto.jpg"
    python -m Backend.Multimodal.Online.Orquestador --text "shoes" --image "C:/ruta/foto.jpg" \
        --text-weight 0.5 --image-weight 0.5
"""

from __future__ import annotations

import argparse
import heapq
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
import psycopg2

from ..Offline.CodeBook_pt2 import generate_image_histograms
from ..Offline.FeatureExtractor import ImageFeatureExtractor, TextFeatureExtractor
from ..Offline.SplitChunks import MultimodalSplitter
from .Search import Search

DATA_DIR = Path(__file__).resolve().parent.parent / "Data"

DEFAULT_DB = {
    "host": "localhost", "port": "5432", "database": "multimodal",
    "user": "postgres", "password": "123456",
}

TEXT_FIELDS = [
    "gender", "master_category", "sub_category", "article_type",
    "base_colour", "season", "year", "usage", "product_name",
]


class OnlineOrchestrator:
    def __init__(self, db_config: Optional[dict] = None, buffer_size: int = 1_000_000_000):
        # etapas reutilizadas del offline
        self.splitter = MultimodalSplitter()
        self.text_extractor = TextFeatureExtractor()
        self.image_extractor = ImageFeatureExtractor()

        # artefactos persistidos por el offline
        self.vocab = self._load_pickle("vocab.pkl")                 # set[str]
        self.text_codebook = self._load_pickle("text_codebook.pkl")  # list[str]
        self.visual_codebook = self._load_pickle("visual_codebook.pkl")  # np.ndarray (k x 128)

        # motor de ranking (lazy-load de indices + TF-IDF)
        self.search = Search(buffer_size)

        # conexion a Postgres para el recovery por ids
        self.conn = psycopg2.connect(**(db_config or DEFAULT_DB))

    @staticmethod
    def _load_pickle(name: str):
        with open(DATA_DIR / name, "rb") as f:
            return pickle.load(f)
        

    @staticmethod
    def _parse_texto(texto: str | None) -> dict:
        """Desconcatena el campo texto (separado por |) en sus campos originales."""
        if not texto:
            return {f: "" for f in TEXT_FIELDS}
        parts = texto.split("|")
        parts += [""] * (len(TEXT_FIELDS) - len(parts))
        return dict(zip(TEXT_FIELDS, parts))

    # Consulta -> histograma (reusa las etapas del offline)
    def _text_histogram(self, text: str) -> np.ndarray:
        """Histograma de la consulta sobre el text_codebook (freq de cada codeword)."""
        chunks = self.splitter.split(0, text)                       # [(0, chunk), ...]
        bows = self.text_extractor.extract_features(chunks, self.vocab)  # modo online
        agg: Dict[str, int] = {}
        for _, bow in bows:
            for word, count in bow.items():
                agg[word] = agg.get(word, 0) + count
        return np.array([agg.get(w, 0) for w in self.text_codebook], dtype=np.float32)

    def _image_histogram(self, image: Union[str, np.ndarray]) -> np.ndarray:
        """Histograma de la consulta sobre el codebook visual (palabras visuales)."""
        if isinstance(image, str):
            img = cv2.imread(image, cv2.IMREAD_COLOR)
            if img is None:
                raise FileNotFoundError(f"No se pudo cargar la imagen: {image}")
        else:
            img = image

        patches = self.splitter.split(0, img)
        features = self.image_extractor.extract_features(patches)
        hists, _ = generate_image_histograms(features, self.visual_codebook)
        if hists:
            return np.asarray(hists[0][1], dtype=np.float32)
        return np.zeros(len(self.visual_codebook), dtype=np.float32)

    # Recovery por ids (desde PostgreSQL)
    def recover_by_ids(self, doc_ids: List[int]) -> Dict[int, Tuple[Optional[str], Optional[str]]]:
        """{doc_id: (url, texto)} para los ids dados."""
        if not doc_ids:
            return {}
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT doc_id, url, texto FROM descriptors WHERE doc_id = ANY(%s)",
                ([int(d) for d in doc_ids],),
            )
            return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    def _format(self, heap: List[Tuple[float, int]], k: int) -> List[dict]:
        """Top-k del heap (-score, doc_id) -> lista enriquecida ordenada por score desc."""
        top = heapq.nsmallest(k, heap)              # los k de mayor score
        meta = self.recover_by_ids([doc_id for _, doc_id in top])
        results = []
        for neg_score, doc_id in top:
            url, texto = meta.get(doc_id, (None, None))
            fields = self._parse_texto(texto)
            results.append({
                "doc_id":          doc_id,
                "score":           round(-neg_score, 6),
                "url":             url,
                "product_name":    fields["product_name"],
                "master_category": fields["master_category"],
                "sub_category":    fields["sub_category"],
                "article_type":    fields["article_type"],
                "base_colour":     fields["base_colour"],
                "season":          fields["season"],
                "year":            fields["year"],
                "usage":           fields["usage"],
                "gender":          fields["gender"],
            })
        return results

    # Busquedas
    def search_text(self, text: str, k: int = 10) -> List[dict]:
        histogram = self._text_histogram(text)
        heap = self.search.text_search(histogram, text_weight=1.0)
        return self._format(heap, k)

    def search_image(self, image: Union[str, np.ndarray], k: int = 10) -> List[dict]:
        # image_search resuelto con multimodal_search y peso de texto = 0
        image_histogram = self._image_histogram(image)
        zero_text = np.zeros(len(self.text_codebook), dtype=np.float32)
        heap = self.search.multimodal_search(
            zero_text, image_histogram, text_weight=0.0, image_weight=1.0
        )
        return self._format(heap, k)

    def search_multimodal(self, text: str, image: Union[str, np.ndarray],
                          text_weight: float = 0.5, image_weight: float = 0.5,
                          k: int = 10) -> List[dict]:
        text_histogram = self._text_histogram(text)
        image_histogram = self._image_histogram(image)
        heap = self.search.multimodal_search(
            text_histogram, image_histogram, text_weight, image_weight
        )
        return self._format(heap, k)

    def close(self) -> None:
        self.search.buffer_manager.close()
        if self.conn and not self.conn.closed:
            self.conn.close()

    
    


def main() -> None:
    parser = argparse.ArgumentParser(description="Orquestador online multimodal")
    parser.add_argument("--text", default=None, help="Consulta de texto")
    parser.add_argument("--image", default=None, help="Ruta a la imagen de consulta")
    parser.add_argument("--k", type=int, default=10, help="Top-k resultados")
    parser.add_argument("--text-weight", type=float, default=0.5)
    parser.add_argument("--image-weight", type=float, default=0.5)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default="5432")
    parser.add_argument("--database", default="multimodal")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="123456")
    args = parser.parse_args()

    if not args.text and not args.image:
        parser.error("Debes pasar --text y/o --image")

    db_config = {
        "host": args.host, "port": args.port, "database": args.database,
        "user": args.user, "password": args.password,
    }
    orch = OnlineOrchestrator(db_config)
    try:
        if args.text and args.image:
            results = orch.search_multimodal(
                args.text, args.image, args.text_weight, args.image_weight, k=args.k
            )
        elif args.image:
            results = orch.search_image(args.image, k=args.k)
        else:
            results = orch.search_text(args.text, k=args.k)

        for i, r in enumerate(results, 1):
            texto = (r["texto"] or "")[:60]
            print(f"{i:2d}. doc_id={r['doc_id']:<8} score={r['score']:.4f}  {texto}")
    finally:
        orch.close()


if __name__ == "__main__":
    main()
