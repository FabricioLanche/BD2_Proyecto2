import csv
import logging
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Iterator, List, Dict, Optional, Tuple, Union

from tqdm import tqdm

import cv2
import numpy as np

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


def get_text_data(
    dataset_size: Optional[int] = None,
) -> Iterator[Tuple[int, str]]:
    """
    Lee Data/styles.csv línea por línea usando csv.DictReader.
    El CSV debe tener columnas: id, texto (texto pre-concatenado con |).
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
            texto = row.get("texto", "")

            yield doc_id, texto
            count += 1

    logger.info("yield_text_data: %d documentos emitidos", count)


def get_image_data(
    dataset_size: Optional[int] = None,
) -> Iterator[Tuple[int, str, str]]:
    """
    Lee Data/images.csv línea por línea usando csv.DictReader.
    Yield (doc_id, link, path_string) — el worker carga la imagen.
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
            if not filename:
                continue

            doc_id = int(row.get("id", "0"))
            link = row.get("link", "")

            local_path = str(DATA_DIR / "images" / Path(filename).name)
            if not Path(local_path).is_file():
                logger.warning(
                    "Imagen local no encontrada doc_id=%d, path=%s",
                    doc_id, local_path,
                )
                continue

            yield doc_id, link, local_path
            count += 1

    logger.info("get_image_data: %d im\u00e1genes emitidas", count)

DATA_DIR_IMAGES = DATA_DIR / "images"

# ── Workers para procesos hijo (pasada 1) ──────────────────────

# get_image_data  → item = (doc_id, link, path_str)
# get_text_data   → item = (doc_id, text)

def _image_worker(
    item: Tuple[int, str, str],
) -> Optional[Tuple[int, list]]:
    """Corre en proceso hijo: carga imagen, split + SIFT."""
    doc_id, _, path = item
    try:
        img = cv2.imread(path)
        if img is None:
            logger.warning("No se pudo decodificar imagen doc_id=%d, path=%s", doc_id, path)
            return None
        splitter = MultimodalSplitter()
        chunks = splitter.split(doc_id, img)
        extractor = ImageFeatureExtractor()
        features = extractor.extract_features(chunks)
        return doc_id, features
    except Exception as e:
        logger.warning("Error imagen doc_id=%d: %s", doc_id, e)
        return None


def _text_worker(
    item: Tuple[int, str, int],
) -> Optional[Tuple[int, list]]:
    """Corre en proceso hijo: split texto + BOW."""
    doc_id, text, n_documents = item
    try:
        splitter = MultimodalSplitter()
        chunks = splitter.split(doc_id, text)
        extractor = TextFeatureExtractor(n_documents=n_documents)
        features = extractor.extract_features(chunks)
        return doc_id, features
    except Exception as e:
        logger.warning("Error texto doc_id=%d: %s", doc_id, e)
        return None


def parallel_feature_stage(
    items: List,
    worker_fn: Callable,
    codebook_builder: Union[VisualCodebookBuilder, TextCodebookBuilder],
    max_workers: int
) -> Iterator[Tuple[int, list]]:
    """
    Stage genérico de extracción en paralelo.

    Distribuye items entre procesos hijo via ProcessPoolExecutor.
    Cada worker ejecuta split + extracción de features.
    El proceso principal acumula en el codebook y hace yield.
    La persistencia debe hacerse antes de llamar a este stage.
    """
    if not items:
        return

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker_fn, it): it for it in items}
        for future in as_completed(futures):
            result = future.result()
            if result is None:
                continue
            doc_id, features = result
            codebook_builder.accumulate(features)
            yield doc_id, features


def split_stage(
    stream: Iterator,
    splitter: MultimodalSplitter,
) -> Iterator[Tuple[int, ChunkList]]:
    """Solo split, sin persistencia (texto se persiste por lotes antes)."""
    for item in stream:
        if len(item) == 3:
            doc_id, _, data = item
            if isinstance(data, str):
                data = cv2.imread(data)
        else:
            doc_id, data = item

        if data is None:
            continue
        chunks = splitter.split(doc_id, data)
        yield doc_id, chunks


def persist_and_split_stage(
    stream: Iterator,
    splitter: MultimodalSplitter,
    persister: PersistenceManager,
) -> Iterator[Tuple[int, ChunkList]]:
    """
    Stage combinado: persiste el documento (upsert) y luego aplica split.

    Para imagen espera tripletes (doc_id, url, path_str) → carga imagen.
    Para texto espera pares     (doc_id, text)          → upsert con texto.
    """
    for item in stream:
        if len(item) == 3:
            doc_id, url, data = item
            persister.insert_document(doc_id, url, "")
            if isinstance(data, str):
                data = cv2.imread(data)
        else:
            doc_id, data = item
            persister.insert_document(doc_id, "", data)

        if data is None:
            continue
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


def _transform_worker(args: Tuple) -> Tuple:
    """Corre en proceso hijo: transforma features a histograma.

    args = (doc_id, features_list, codebook, transform_class)
    transform_class puede ser VisualCodebookTransform o TextCodebookTransform.
    Returns (doc_id, histogram_array, [(doc_id, codeword_id), ...])
    """
    doc_id, features, codebook, transform_class = args
    transform = transform_class(codebook)
    histogram = transform.transform(features, doc_id)
    return doc_id, histogram, transform.tokens


def parallel_transform_stage(
    stream: Iterator[Tuple[int, list]],
    codebook: Union[np.ndarray, List],
    transform_class: Union[type],
    persister: PersistenceManager,
    max_workers: int,
    label: str = "",
    persist: bool = True,
) -> Tuple[List[Tuple[int, np.ndarray]], List[Tuple[int, int]]]:
    items = [(doc_id, features, codebook, transform_class)
             for doc_id, features in stream]
    n = len(items)
    if n == 0:
        return [], []

    is_text = transform_class == TextCodebookTransform
    histograms: List[Tuple[int, np.ndarray]] = []
    all_tokens: List[Tuple[int, int]] = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_transform_worker, it): it[0]
                   for it in items}
        for future in tqdm(as_completed(futures), total=n,
                           desc=label, unit="doc"):
            doc_id, histogram, tokens = future.result()
            if persist:
                if is_text:
                    persister.insert_text_histogram(doc_id, histogram)
                else:
                    persister.insert_image_histogram(doc_id, histogram)
            histograms.append((doc_id, histogram))
            all_tokens.extend(tokens)

    return histograms, all_tokens


def codebook_transform_and_persist_stage(
    stream: Iterator[Tuple[int, list]],
    transform: Union[TextCodebookTransform, VisualCodebookTransform],
    persister: PersistenceManager,
) -> Iterator[Tuple[int, np.ndarray]]:
    for doc_id, features_list in stream:
        histogram = transform.transform(features_list, doc_id)
        if getattr(transform, 'persist_histogram', False):
            if isinstance(transform, TextCodebookTransform):
                persister.insert_text_histogram(doc_id, histogram)
            else:
                persister.insert_image_histogram(doc_id, histogram)
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
        help="Procesos en paralelo para texto e imagen (>1 activa ProcessPoolExecutor)",
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

    parallel = args.processes > 1

    # ── Pasada 1: Texto (siempre secuencial — vocabulario global compartido) ──
    logger.info("=== Fase 1: Texto ===")
    text_features: List[Tuple[int, List[Dict[int, int]]]] = []

    text_data = list(get_text_data(args.dataset_size))
    persister.batch_insert_documents(
        [(doc_id, "", text) for doc_id, text in text_data]
    )
    text_stream = codebook_build_stage(
        extract_feature_stage(
            split_stage(iter(text_data), splitter),
            text_extractor,
        ),
        text_codebook_builder,
    )

    for doc_id, features in tqdm(
        text_stream,
        total=args.dataset_size,
        desc="  Texto",
        unit="doc",
    ):
        text_features.append((doc_id, [bow for _, bow in features]))
    text_extractor.persist_vocab()
    logger.info("Vocabulario persistido: %d terminos, %d documentos",
                len(text_extractor.vocab), len(text_features))

    # ── Pasada 1: Imagen ─────────────────────────────────────
    logger.info("=== Fase 1: Imagen ===")
    image_features: List[Tuple[int, List[np.ndarray]]] = []

    if parallel:
        image_items = list(get_image_data(args.dataset_size))
        persister.batch_insert_documents(
            [(doc_id, url, "") for doc_id, url, _ in image_items]
        )

        image_stream = parallel_feature_stage(
            image_items, _image_worker, visual_codebook_builder,
            max_workers=args.processes, label="  Imagen",
        )
    else:
        image_stream = codebook_build_stage(
            extract_feature_stage(
                persist_and_split_stage(
                    get_image_data(args.dataset_size), splitter, persister,
                ),
                image_extractor,
            ),
            visual_codebook_builder,
        )

    for doc_id, features in tqdm(
        image_stream,
        total=args.dataset_size,
        desc="  Imagen",
        unit="doc",
    ):
        image_features.append((doc_id, [desc for _, desc in features]))
    logger.info("Descriptores almacenados: %d documentos", len(image_features))

    # ── Finalizar codebooks ──────────────────────────────────
    logger.info("=== Finalizando codebooks ===")
    visual_codebook = visual_codebook_builder.finalize()
    text_codebook = text_codebook_builder.finalize()
    logger.info(
        "Codebooks listos: visual k=%d, texto k=%d",
        len(visual_codebook), len(text_codebook),
    )

    persister.add_text_histogram_column(len(text_codebook))

    # ── Pasada 2: Texto ──────────────────────────────────────
    logger.info("=== Pasada 2: Texto ===")
    if parallel:
        _, text_tokens = parallel_transform_stage(
            iter(text_features), text_codebook, TextCodebookTransform,
            persister, max_workers=args.processes,
            label="  Texto",
        )
    else:
        text_transform = TextCodebookTransform(text_codebook)
        for _ in tqdm(
            codebook_transform_and_persist_stage(
                iter(text_features), text_transform, persister,
            ),
            total=len(text_features),
            desc="  Texto",
            unit="doc",
        ): pass
        text_tokens = text_transform.tokens

    # ── Pasada 2: Imagen ─────────────────────────────────────
    logger.info("=== Pasada 2: Imagen ===")
    if parallel:
        _, image_tokens = parallel_transform_stage(
            iter(image_features), visual_codebook, VisualCodebookTransform,
            persister, max_workers=args.processes, label="  Imagen",
        )
    else:
        image_transform = VisualCodebookTransform(visual_codebook)
        for _ in tqdm(
            codebook_transform_and_persist_stage(
                iter(image_features), image_transform, persister,
            ),
            total=len(image_features),
            desc="  Imagen",
            unit="doc",
        ): pass
        image_tokens = image_transform.tokens

    # ── Construcción de índices invertidos ───────────────────
    logger.info("=== Construyendo índices invertidos ===")
    inverse_index = InverseIndex(args.dataset_size)
    inverse_index.build_image_index(image_tokens)
    inverse_index.build_text_index(text_tokens)
    logger.info("Índices invertidos listos")

    persister.dump_csv()
    logger.info("Pipeline offline completado")


if __name__ == "__main__":
    main()