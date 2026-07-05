"""
Iteradores streaming para el pipeline offline multimodal.

Proveen generadores que leen styles.csv e images.csv línea por línea
desde Backend/Multimodal/Data/, yields (doc_id, data) una tupla a la vez
sin cargar el dataset completo.
"""

import csv
import logging
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Iterator, List, Dict, Optional, Tuple, Union

from tqdm import tqdm

import cv2
import numpy as np
import requests

from . import CodeBook as _cb_module
from . import FeatureExtractor as _fe_module
from . import InverseIndex as _ii_module
from .SplitChunks import MultimodalSplitter
from .Persistence import PersistenceManager
from .FeatureExtractor import ImageFeatureExtractor, TextFeatureExtractor
from .CodeBook import VisualCodebookBuilder, TextCodebookBuilder
from .CodeBook_pt2 import TextCodebookTransform, VisualCodebookTransform
from .InverseIndex import InverseIndex

logger = logging.getLogger("StreamingIterators")

DATA_DIR = Path(__file__).resolve().parent.parent / "Data"

Data = Union[str, np.ndarray]
Chunk = Union[str, np.ndarray]
ChunkList = List[Tuple[int, Chunk]]

TEXT_COLUMNS = [
    "gender", "masterCategory", "subCategory", "articleType",
    "baseColour", "season", "year", "usage", "productDisplayName",
]


def get_text_data(
    dataset_size: Optional[int] = None,
) -> Iterator[Tuple[int, str]]:
    """
    Lee Data/styles.csv línea por línea usando csv.DictReader.

    Por cada fila:
      - Concatena las columnas textuales disponibles con '|'
      - Yield (doc_id, texto_concatenado)
    """
    styles_path = DATA_DIR / "styles.csv"
    if not styles_path.exists():
        raise FileNotFoundError(f"No se encontr\u00f3 {styles_path}")

    with open(styles_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if dataset_size is not None and count >= dataset_size:
                break

            doc_id = int(row.get("id", count))

            parts: list[str] = []
            for col in TEXT_COLUMNS:
                val = row.get(col, "")
                parts.append(val if val else "")

            texto = "|".join(parts)

            yield doc_id, texto
            count += 1

    logger.info("yield_text_data: %d documentos emitidos", count)


def get_image_data(
    dataset_size: Optional[int] = None,
    timeout: int = 10,
) -> Iterator[Tuple[int, str, np.ndarray]]:
    """
    Lee Data/images.csv línea por línea usando csv.DictReader.

    Por cada fila:
      - Extrae doc_id del campo filename (ej. "123.jpg" -> 123)
      - Extrae url del campo link
      - Descarga la imagen desde la URL original con requests
      - Decodifica con OpenCV a np.ndarray (BGR)
      - Yield (doc_id, url, imagen_array)

    Si falla la descarga o decodificación, salta la imagen (loggea warning).
    """
    images_path = DATA_DIR / "images.csv"
    if not images_path.exists():
        raise FileNotFoundError(f"No se encontr\u00f3 {images_path}")

    with open(images_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if dataset_size is not None and count >= dataset_size:
                break

            filename: str = row.get("filename", "")
            url: str = row.get("link", "")

            if not filename or not url:
                logger.warning(
                    "Fila inv\u00e1lida en images.csv: filename=%s, link=%s",
                    filename, url,
                )
                continue

            doc_id = int(filename.replace(".jpg", "").replace(".png", ""))

            try:
                resp = requests.get(url, timeout=timeout)
                resp.raise_for_status()

                arr = np.frombuffer(resp.content, dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

                if img is None:
                    logger.warning(
                        "No se pudo decodificar imagen doc_id=%d, url=%s",
                        doc_id, url,
                    )
                    continue

                yield doc_id, url, img
                count += 1

            except requests.RequestException as e:
                logger.warning(
                    "Error descargando imagen doc_id=%d, url=%s: %s",
                    doc_id, url, e,
                )
                continue
            except Exception as e:
                logger.warning(
                    "Error procesando imagen doc_id=%d, url=%s: %s",
                    doc_id, url, e,
                )
                continue

    logger.info("get_image_data: %d im\u00e1genes emitidas", count)

def _image_worker(
    doc_id_url: Tuple[int, str],
) -> Optional[Tuple[int, str, List[np.ndarray]]]:
    """Corre en proceso hijo: descarga + decode + split + SIFT.

    Returns (doc_id, url, [(chunk_id, descriptor), ...]) o None si falla.
    """
    doc_id, url = doc_id_url
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        arr = np.frombuffer(resp.content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        splitter = MultimodalSplitter()
        chunks = splitter.split(doc_id, img)
        extractor = ImageFeatureExtractor()
        features = extractor.extract_features(chunks)
        return doc_id, url, features
    except Exception as e:
        logger.warning("Error imagen doc_id=%d: %s", doc_id, e)
        return None


def parallel_image_pipeline(
    dataset_size: int,
    codebook_builder: VisualCodebookBuilder,
    persister: PersistenceManager,
    max_workers: int,
) -> Iterator[Tuple[int, list]]:
    """Reemplaza get_image_data → persist_and_split → extract → codebook_build.

    Download + split + SIFT corren en procesos hijo (ProcessPoolExecutor).
    Persist + accumulate corren en el proceso principal.
    """
    images_path = DATA_DIR / "images.csv"
    if not images_path.exists():
        raise FileNotFoundError(f"No se encontr\u00f3 {images_path}")

    items: list[Tuple[int, str]] = []
    with open(images_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if dataset_size is not None and count >= dataset_size:
                break
            filename = row.get("filename", "")
            url = row.get("link", "")
            if not filename or not url:
                continue
            doc_id = int(filename.replace(".jpg", "").replace(".png", ""))
            items.append((doc_id, url))
            count += 1

    logger.info(
        "parallel_image_pipeline: %d imagenes con %d procesos",
        len(items), max_workers,
    )

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_image_worker, it): it for it in items}
        for future in as_completed(futures):
            result = future.result()
            if result is None:
                continue
            doc_id, url, features = result
            persister.insert_document(doc_id, url, "")
            codebook_builder.accumulate(features)
            yield doc_id, features


def persist_and_split_stage(
    stream: Iterator,
    splitter: MultimodalSplitter,
    persister: PersistenceManager,
) -> Iterator[Tuple[int, ChunkList]]:
    """
    Stage combinado: persiste el documento (upsert) y luego aplica split.

    Para imagen espera tripletes (doc_id, url, img) → upsert con url.
    Para texto espera pares    (doc_id, text)  → upsert con texto.
    """
    for item in stream:
        if len(item) == 3:
            doc_id, url, data = item
            persister.insert_document(doc_id, url, "")
        else:
            doc_id, data = item
            persister.insert_document(doc_id, "", data)

        chunks = splitter.split(doc_id, data)
        yield doc_id, chunks


def extract_feature_stage(
    stream: Iterator[Tuple[int, ChunkList]],
    extractor: Union[ImageFeatureExtractor, TextFeatureExtractor],
) -> Iterator[Tuple[int, List]]:
    """
    Generador de etapa feature extraction.

    Recibe (doc_id, chunks) del split_stage, extrae features de cada chunk
    y yield (doc_id, features_list).
    """
    for doc_id, chunks in stream:
        features = extractor.extract_features(chunks)
        yield doc_id, features


def codebook_build_stage(
    stream: Iterator[Tuple[int, List]],
    codebook_builder: Union[VisualCodebookBuilder, TextCodebookBuilder],
) -> Iterator[Tuple[int, List]]:
    """
    Stage comun para construir codebooks (texto e imagen).

    Delega en codebook_builder.accumulate(features) que se implementa
    distinto segun el tipo de builder:
      - VisualCodebookBuilder: extrae descriptores SIFT y llama partial_fit.
      - TextCodebookBuilder:    acumula frecuencias en un Counter.
    Hace pass-through de (doc_id, features).
    """
    for doc_id, features in stream:
        codebook_builder.accumulate(features)
        yield doc_id, features


def _image_transform_worker(args: Tuple) -> Tuple:
    """Corre en proceso hijo: transforma descriptores de un doc a histograma.

    args = (doc_id, descriptors_list, visual_codebook_array)
    Returns (doc_id, histogram_array, [(doc_id, codeword_id), ...])
    """
    doc_id, descriptors, codebook = args
    transform = VisualCodebookTransform(codebook)
    histogram = transform.transform(descriptors, doc_id)
    return doc_id, histogram, transform.tokens


def parallel_image_transform(
    features_iter: Iterator[Tuple[int, list]],
    codebook: np.ndarray,
    persister: PersistenceManager,
    max_workers: int,
) -> Tuple[List[Tuple[int, np.ndarray]], List[Tuple[int, int]]]:
    """Pasada 2 de imagen en paralelo.

    Transforma descriptores a histogramas con ProcessPoolExecutor.
    Retorna (list_histograms, all_tokens) para construir índices.
    """
    items = [(doc_id, descs, codebook)
             for doc_id, descs in features_iter]
    n = len(items)

    logger.info(
        "parallel_image_transform: %d docs con %d procesos",
        n, max_workers,
    )

    histograms: List[Tuple[int, np.ndarray]] = []
    all_tokens: List[Tuple[int, int]] = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_image_transform_worker, it): it[0]
                   for it in items}
        for future in tqdm(as_completed(futures), total=n,
                           desc="  Imagen", unit="doc"):
            doc_id, histogram, tokens = future.result()
            persister.insert_histogram(doc_id, histogram)
            histograms.append((doc_id, histogram))
            all_tokens.extend(tokens)

    return histograms, all_tokens


def codebook_transform_and_persist_stage(
    stream: Iterator[Tuple[int, list]],
    transform: Union[TextCodebookTransform, VisualCodebookTransform],
    persister: PersistenceManager,
) -> Iterator[Tuple[int, np.ndarray]]:
    """
    Transforma features a histogramas y persiste si el transform lo requiere.

    Solo VisualCodebookTransform tiene persist_histogram = True
    (persiste image_histogram vía persister.insert_histogram).
    """
    for doc_id, features_list in stream:
        histogram = transform.transform(features_list, doc_id)
        if getattr(transform, 'persist_histogram', False):
            persister.insert_histogram(doc_id, histogram)
        yield doc_id, histogram


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orquestador2 — Pipeline offline streaming (etapa split)"
    )
    parser.add_argument(
        "--dataset-size", type=int, default=40000,
        help="Procesar solo N productos (default: todos)",
    )
    parser.add_argument(
        "--processes", type=int, default=1,
        help="Procesos para imágenes (>1 activa parallel_image_pipeline con ProcessPoolExecutor)",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nivel de logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if args.dataset_size is not None:
        data_subdir = DATA_DIR / str(args.dataset_size)
        data_subdir.mkdir(parents=True, exist_ok=True)
        _cb_module.DATA_DIR = data_subdir
        _fe_module.DATA_DIR = str(data_subdir)
        _ii_module.DATA_DIR = str(data_subdir)

    splitter = MultimodalSplitter()
    persister = PersistenceManager(n_documents=args.dataset_size)
    text_extractor = TextFeatureExtractor(n_documents=args.dataset_size)
    image_extractor = ImageFeatureExtractor()
    text_codebook_builder = TextCodebookBuilder(n_documents=args.dataset_size)
    visual_codebook_builder = VisualCodebookBuilder(n_documents=args.dataset_size)

    persister.create_tables()

    logger.info("=== Fase 1: Texto ===")
    text_features: List[Tuple[int, List[Dict[int, int]]]] = []
    for doc_id, features in tqdm(
        codebook_build_stage(
            extract_feature_stage(
                persist_and_split_stage(
                    get_text_data(args.dataset_size), splitter, persister,
                ),
                text_extractor,
            ),
            text_codebook_builder,
        ),
        total=args.dataset_size,
        desc="  Texto",
        unit="doc",
    ):
        text_features.append((doc_id, [bow for _, bow in features]))
    text_extractor.persist_vocab()
    logger.info("Vocabulario persistido: %d terminos, %d documentos",
                len(text_extractor.vocab), len(text_features))

    logger.info("=== Fase 1: Imagen ===")
    image_features: List[Tuple[int, List[np.ndarray]]] = []
    image_stream = (
        parallel_image_pipeline(
            args.dataset_size, visual_codebook_builder, persister,
            max_workers=args.processes,
        )
        if args.processes > 1
        else codebook_build_stage(
            extract_feature_stage(
                persist_and_split_stage(
                    get_image_data(args.dataset_size), splitter, persister
                ),
                image_extractor,
            ),
            visual_codebook_builder,
        )
    )
    for doc_id, features in tqdm(
        image_stream,
        total=args.dataset_size,
        desc="  Imagen",
        unit="doc",
    ):
        image_features.append((doc_id, [desc for _, desc in features]))
    logger.info("Descriptores almacenados: %d documentos", len(image_features))

    logger.info("=== Finalizando codebooks ===")
    visual_codebook = visual_codebook_builder.finalize()
    text_codebook = text_codebook_builder.finalize()
    logger.info(
        "Codebooks listos: visual k=%d, texto k=%d",
        len(visual_codebook), len(text_codebook),
    )

    # --- Pasada 2: transformar features a histogramas (sin re-extraer) ---
    logger.info("=== Pasada 2: Texto ===")
    text_transform = TextCodebookTransform(text_codebook)
    for doc_id, histogram in tqdm(
        codebook_transform_and_persist_stage(
            iter(text_features), text_transform, persister,
        ),
        total=len(text_features),
        desc="  Texto",
        unit="doc",
    ): pass

    logger.info("=== Pasada 2: Imagen ===")
    if args.processes > 1:
        image_histograms, image_tokens = parallel_image_transform(
            iter(image_features), visual_codebook, persister,
            max_workers=args.processes,
        )
        class _DummyTransform:
            pass
        image_transform = _DummyTransform()
        image_transform.tokens = image_tokens
        image_transform.histograms = image_histograms
    else:
        image_transform = VisualCodebookTransform(visual_codebook)
        for doc_id, histogram in tqdm(
            codebook_transform_and_persist_stage(
                iter(image_features), image_transform, persister,
            ),
            total=len(image_features),
            desc="  Imagen",
            unit="doc",
        ): pass

    # --- Construcción de índices invertidos ---
    logger.info("=== Construyendo índices invertidos ===")
    inverse_index = InverseIndex(args.dataset_size)
    inverse_index.build_image_index(image_transform.tokens)
    inverse_index.build_text_index(text_transform.tokens)
    logger.info("Índices invertidos listos")

    persister.dump_csv()
    logger.info("Pipeline offline completado")


if __name__ == "__main__":
    main()