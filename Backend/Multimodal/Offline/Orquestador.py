"""
(Split -> FeatureExtractor -> CodeBook -> CodeBook_pt2 ->
InverseIndex)

lee el dataset, conecta las salidas de una etapa con las entradas de la
siguiente y llama a la persistencia.

artefactos que deja en Backend/Multimodal/Data/ (los reusa el orquestador online):
    - vocab.pkl, text_codebook.pkl, visual_codebook.pkl
    - text_index.btree/heap + image_index.btree/heap (indices invertidos)
    - text_word_idf.pkl, text_doc_norm.pkl, image_word_idf.pkl, image_doc_norm.pkl (TF-IDF)
    - Tabla `descriptors` poblada en PostgreSQL.
"""

from __future__ import annotations

import argparse
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
import pandas as pd

from .CodeBook import TextCodebookBuilder, VisualCodebookBuilder
from .CodeBook_pt2 import generate_image_histograms, generate_text_histograms
from .FeatureExtractor import ImageFeatureExtractor, TextFeatureExtractor
from .InverseIndex import InverseIndex
from .Persistence import PersistenceManager
from .SplitChunks import MultimodalSplitter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Orquestador")

MODULE_DIR = Path(__file__).resolve().parent
DATA_DIR = MODULE_DIR.parent / "Data"

#columnas textuales de styles.csv que se concatenan para formar `texto`.
TEXT_COLUMNS = [
    "gender", "masterCategory", "subCategory", "articleType",
    "baseColour", "season", "year", "usage", "productDisplayName",
]


#lectura dataset y registro de IDs
def load_dataset(dataset_dir: Path, limit: int | None = None
                 ) -> Tuple[pd.DataFrame, Dict[int, Path]]:
    #Devuelve (df[doc_id, url, texto], {doc_id: ruta_imagen_local})
    dataset_dir = Path(dataset_dir)
    images_csv = dataset_dir / "images.csv"
    styles_csv = dataset_dir / "styles.csv"
    if not styles_csv.exists():
        raise FileNotFoundError(f"No se encontro {styles_csv}")

    styles = pd.read_csv(styles_csv, on_bad_lines="skip")

    #texto = concatenacion de las columnas textuales disponibles en styles.csv
    present = [c for c in TEXT_COLUMNS if c in styles.columns]
    styles[present] = styles[present].fillna("").astype(str)
    styles["texto"] = (
        styles[present].agg(" ".join, axis=1).str.replace(r"\s+", " ", regex=True).str.strip()
    )
    styles = styles.rename(columns={"id": "doc_id"})

    if images_csv.exists():
        #version grande: images.csv trae filename (-> doc_id) y link (-> url)
        images = pd.read_csv(images_csv)
        images["doc_id"] = (
            images["filename"].astype(str).str.replace(".jpg", "", regex=False).astype(int)
        )
        images = images.rename(columns={"link": "url"})
        df = images.merge(styles[["doc_id", "texto"]], on="doc_id", how="inner")
        df = df[["doc_id", "url", "texto"]]
    else:
        #version small: no hay images.csv -> doc_id sale de styles.csv y url queda vacia
        logger.info("Sin images.csv; usando ids de styles.csv (url vacia)")
        df = styles[["doc_id", "texto"]].copy()
        df["url"] = ""
        df = df[["doc_id", "url", "texto"]]

    df = df.drop_duplicates(subset="doc_id").reset_index(drop=True)

    if limit:
        df = df.head(limit).reset_index(drop=True)

    image_paths = {
        int(doc_id): dataset_dir / "images" / f"{int(doc_id)}.jpg"
        for doc_id in df["doc_id"]
    }
    logger.info("Dataset cargado: %d productos", len(df))
    return df, image_paths


#imagen: split + SIFT
def extract_image_features(image_paths: Dict[int, Path],
                           splitter: MultimodalSplitter
                           ) -> List[Tuple[int, np.ndarray]]:
    #[(doc_id, descriptor_128d), ...] para todas las imagenes
    extractor = ImageFeatureExtractor()
    all_features: List[Tuple[int, np.ndarray]] = []

    for doc_id, path in image_paths.items():
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None:
            logger.warning("Imagen no encontrada/ilegible, se omite: %s", path)
            continue

        patches = splitter.split(doc_id, img)   # [(doc_id, patch), ...] ya etiquetado
        all_features.extend(extractor.extract_features(patches))

    logger.info("Descriptores SIFT extraidos: %d", len(all_features))
    return all_features


#texto: split + bag-of-words por documento
def extract_text_features(df: pd.DataFrame, splitter: MultimodalSplitter
                          ) -> Tuple[List[Tuple[int, Dict[str, int]]], List[str]]:
    #devuelve (bows agregados por doc, vocabulario_ordenado)
    extractor = TextFeatureExtractor()

    #split de texto -> [(doc_id, chunk)] (ya viene etiquetado con el doc_id)
    text_chunks: List[Tuple[int, str]] = []
    for row in df.itertuples(index=False):
        text_chunks.extend(splitter.split(int(row.doc_id), row.texto))

    per_chunk_bows, global_vocab = extractor.extract_features(text_chunks)  # persiste vocab.pkl

    #agregar los bows de todos los trozos de un mismo documento -> un bow por doc
    agg: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for doc_id, bow in per_chunk_bows:
        for word, count in bow.items():
            agg[doc_id][word] += count
    doc_bows = [(doc_id, dict(bow)) for doc_id, bow in agg.items()]

    #orden del vocabulario (online debe usar el mismo: sorted())
    vocabulary = sorted(global_vocab)
    logger.info("Vocabulario: %d terminos | documentos con texto: %d",
                len(vocabulary), len(doc_bows))
    return doc_bows, vocabulary


def to_dense_bows(doc_bows: List[Tuple[int, Dict[str, int]]], vocabulary: List[str]
                  ) -> List[Tuple[int, np.ndarray]]:
    #bow dict -> vector denso alineado al vocabulario (lo pide generate_text_histograms)
    index = {word: i for i, word in enumerate(vocabulary)}
    dense: List[Tuple[int, np.ndarray]] = []
    for doc_id, bow in doc_bows:
        vec = np.zeros(len(vocabulary), dtype=np.float32)
        for word, count in bow.items():
            vec[index[word]] = count
        dense.append((doc_id, vec))
    return dense



def run_offline(dataset_dir: str, db_config: dict, limit: int | None = None,
                text_k: int = 100) -> None:
    splitter = MultimodalSplitter()

    #1. dataset + registro de ids
    df, image_paths = load_dataset(Path(dataset_dir), limit)

    # 2. imagen: features + codebook visual (necesitamos k antes de crear la tabla)
    image_features = extract_image_features(image_paths, splitter)
    if not image_features:
        raise RuntimeError("No se extrajeron descriptores de imagen; revisa el dataset.")

    n_desc = len(image_features)
    k_candidates = [k for k in range(10, 101, 10) if k <= n_desc] or [min(n_desc, 10)]
    visual_codebook = VisualCodebookBuilder(k_candidates=k_candidates).build(
        lambda: iter(image_features)            #reentrega los descriptores
    )
    k = len(visual_codebook)
    logger.info("Codebook visual construido con k=%d palabras visuales", k)

    #3. postgreSQL: tabla (con dimension = k) + documentos base
    pm = PersistenceManager(**db_config)
    inverse_index = InverseIndex()
    n_docs = len(df)
    try:
        pm.create_tables(histogram_dim=k)
        pm.insert_document(df[["doc_id", "url", "texto"]])

        #4. imagen: histogramas + indice invertido
        image_histograms, image_spimi = generate_image_histograms(image_features, visual_codebook)
        pm.update_histograms(image_histograms)
        inverse_index.build_image_index(image_spimi, n_documents=n_docs)
        logger.info("Indice invertido de imagen construido")

        #5. texto: features -> codebook -> histogramas -> indice invertido
        doc_bows, vocabulary = extract_text_features(df, splitter)
        text_codebook = TextCodebookBuilder(vocabulary, doc_bows, k=text_k).build()
        dense_features = to_dense_bows(doc_bows, vocabulary)
        _, text_spimi = generate_text_histograms(
            dense_features, text_codebook, np.array(vocabulary)
        )
        inverse_index.build_text_index(text_spimi, n_documents=n_docs)
        logger.info("Indice invertido de texto construido")
    finally:
        inverse_index.buffer_manager.close()
        pm.close()

    logger.info("Pipeline offline completado.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Orquestador offline multimodal")
    parser.add_argument("--dataset", required=True, help="Ruta a la carpeta del dataset")
    parser.add_argument("--limit", type=int, default=None, help="Procesar solo N productos")
    parser.add_argument("--text-k", type=int, default=100, help="Top-k del codebook de texto")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default="5432")
    parser.add_argument("--database", default="multimodal")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="123456")
    args = parser.parse_args()

    db_config = {
        "host": args.host, "port": args.port, "database": args.database,
        "user": args.user, "password": args.password,
    }
    run_offline(args.dataset, db_config, limit=args.limit, text_k=args.text_k)


if __name__ == "__main__":
    main()
