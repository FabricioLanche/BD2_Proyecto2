"""
Orquestador ONLINE del pipeline multimodal (streaming).

Recibe UNA consulta (texto, imagen o ambos), la transforma en histograma
reutilizando las mismas etapas del offline (split → extract → transform)
y delega el ranking a Search.

No persiste nada, no construye codebooks. Carga los artefactos que dejó
el orquestador offline desde Data/{n_documents}/.

Uso:
    python -m Backend.Multimodal.Online.Orquestador --dataset-size 5 \\
        --text "blue shirt" --k 10
    python -m Backend.Multimodal.Online.Orquestador --dataset-size 5 \\
        --image "C:/ruta/foto.jpg"
    python -m Backend.Multimodal.Online.Orquestador --dataset-size 5 \\
        --text "shoes" --image "C:/ruta/foto.jpg" \\
        --text-weight 0.5 --image-weight 0.5
"""

from __future__ import annotations

import argparse
import heapq
import pickle
import logging
from pathlib import Path
from typing import Iterator, List, Optional, Tuple, Union

import cv2
import numpy as np
import psycopg2

from ..Offline.Orquestador import extract_feature_stage
from ..Offline.SplitChunks import MultimodalSplitter
from ..Offline.FeatureExtractor import ImageFeatureExtractor, TextFeatureExtractor
from ..Offline.CodeBook_pt2 import TextCodebookTransform, VisualCodebookTransform
from .Search import Search

logger = logging.getLogger("OnlineOrchestrator")

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
    def __init__(self, db_config: Optional[dict] = None,
                 n_documents: int = 0,
                 buffer_size: int = 1_000_000_000):
        self.n_documents = n_documents
        data_subdir = DATA_DIR / str(n_documents)
        self._data_dir = data_subdir

        # Splitter
        self.splitter = MultimodalSplitter()

        # Text extractor con vocabulario precargado (read-only)
        self.text_extractor = TextFeatureExtractor(n_documents=n_documents)
        self.vocab = self._load_pickle(f"vocab_{n_documents}.pkl")
        self.text_extractor.load_vocab(self.vocab)

        # Image extractor
        self.image_extractor = ImageFeatureExtractor()

        # Codebooks persistidos por el offline
        self.text_codebook = self._load_pickle(f"text_codebook_{n_documents}.pkl")
        self.visual_codebook = self._load_pickle(f"visual_codebook_{n_documents}.pkl")

        # Motor de ranking
        self.search = Search(n_documents=n_documents, buffer_size=buffer_size)

        # Conexión a Postgres para recovery por ids
        self.conn = psycopg2.connect(**(db_config or DEFAULT_DB))

    def _load_pickle(self, name: str):
        path = self._data_dir / name
        with open(path, "rb") as f:
            return pickle.load(f)

    # ── Generadores streaming para una consulta ──────────────────

    @staticmethod
    def _single_text_stream(text: str) -> Iterator[Tuple[int, str]]:
        yield (0, text)

    @staticmethod
    def _single_image_stream(image: np.ndarray) -> Iterator[Tuple[int, str, np.ndarray]]:
        yield (0, "", image)

    @staticmethod
    def _split_without_persist(
        stream: Iterator,
        splitter: MultimodalSplitter,
    ) -> Iterator[Tuple[int, list]]:
        """Similar a persist_and_split_stage pero sin persistir."""
        for item in stream:
            if len(item) == 3:
                doc_id, _url, data = item
            else:
                doc_id, data = item
            chunks = splitter.split(doc_id, data)
            yield doc_id, chunks

    # ── Transformación a histogramas ─────────────────────────────

    def _text_histogram(self, text: str) -> np.ndarray:
        bows: list = []
        for _doc_id, features in extract_feature_stage(
            self._split_without_persist(
                self._single_text_stream(text), self.splitter,
            ),
            self.text_extractor,
        ):
            bows.extend(bow for _, bow in features)

        transform = TextCodebookTransform(self.text_codebook)
        return transform.transform(bows, doc_id=0)

    def _image_histogram(self, image: Union[str, np.ndarray]) -> np.ndarray:
        if isinstance(image, str):
            img = cv2.imread(image, cv2.IMREAD_COLOR)
            if img is None:
                raise FileNotFoundError(f"No se pudo cargar la imagen: {image}")
        else:
            img = image

        descriptors: list = []
        for _doc_id, features in extract_feature_stage(
            self._split_without_persist(
                self._single_image_stream(img), self.splitter,
            ),
            self.image_extractor,
        ):
            descriptors.extend(desc for _, desc in features)

        transform = VisualCodebookTransform(self.visual_codebook)
        return transform.transform(descriptors, doc_id=0)

    # ── Recovery por ids (desde PostgreSQL) ──────────────────────

    @staticmethod
    def _parse_texto(texto: str | None) -> dict:
        if not texto:
            return {f: "" for f in TEXT_FIELDS}
        parts = texto.split("|")
        parts += [""] * (len(TEXT_FIELDS) - len(parts))
        return dict(zip(TEXT_FIELDS, parts))

    def recover_by_ids(self, doc_ids: List[int]) -> dict:
        if not doc_ids:
            return {}
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT doc_id, url, texto FROM descriptors WHERE doc_id = ANY(%s)",
                ([int(d) for d in doc_ids],),
            )
            return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    # ── Formateo de resultados ───────────────────────────────────

    def _format(self, heap: List[Tuple[float, int]], k: int) -> List[dict]:
        top = heapq.nsmallest(k, heap)
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

    # ── Búsquedas públicas ───────────────────────────────────────

    def search_text(self, text: str, k: int = 10) -> List[dict]:
        histogram = self._text_histogram(text)
        heap = self.search.text_search(histogram)
        return self._format(heap, k)

    def search_image(self, image: Union[str, np.ndarray], k: int = 10) -> List[dict]:
        image_histogram = self._image_histogram(image)
        zero_text = np.zeros(len(self.text_codebook), dtype=np.float32)
        heap = self.search.multimodal_search(
            zero_text, image_histogram, text_weight=0.0, image_weight=1.0,
        )
        return self._format(heap, k)

    def search_multimodal(self, text: str, image: Union[str, np.ndarray],
                          text_weight: float = 0.5, image_weight: float = 0.5,
                          k: int = 10) -> List[dict]:
        text_histogram = self._text_histogram(text)
        image_histogram = self._image_histogram(image)
        heap = self.search.multimodal_search(
            text_histogram, image_histogram, text_weight, image_weight,
        )
        return self._format(heap, k)

    def close(self) -> None:
        self.search.buffer_manager.close()
        if self.conn and not self.conn.closed:
            self.conn.close()

    # ── Métricas I/O (delegadas) ─────────────────────────────────

    def reset_io_counters(self) -> None:
        self.search.reset_io_counters()

    def io_metrics(self) -> dict:
        return self.search.io_metrics()


def main() -> None:
    parser = argparse.ArgumentParser(description="Orquestador online multimodal")
    parser.add_argument("--text", default=None, help="Consulta de texto")
    parser.add_argument("--image", default=None, help="Ruta a la imagen de consulta")
    parser.add_argument("--k", type=int, default=10, help="Top-k resultados")
    parser.add_argument("--text-weight", type=float, default=0.5)
    parser.add_argument("--image-weight", type=float, default=0.5)
    parser.add_argument("--dataset-size", type=int, required=True,
                        help="Cantidad de documentos usada en el offline")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default="5432")
    parser.add_argument("--database", default="multimodal")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="123456")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    if not args.text and not args.image:
        parser.error("Debes pasar --text y/o --image")

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    db_config = {
        "host": args.host, "port": args.port, "database": args.database,
        "user": args.user, "password": args.password,
    }
    orch = OnlineOrchestrator(db_config, n_documents=args.dataset_size)
    try:
        if args.text and args.image:
            results = orch.search_multimodal(
                args.text, args.image, args.text_weight, args.image_weight, k=args.k,
            )
        elif args.image:
            results = orch.search_image(args.image, k=args.k)
        else:
            results = orch.search_text(args.text, k=args.k)

        for i, r in enumerate(results, 1):
            texto = (r.get("product_name") or "")[:60]
            print(f"{i:2d}. doc_id={r['doc_id']:<8} score={r['score']:.4f}  {texto}")
    finally:
        orch.close()

if __name__ == "__main__":
    main()