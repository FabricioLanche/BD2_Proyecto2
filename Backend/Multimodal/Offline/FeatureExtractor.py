import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set, Tuple, Union

import cv2
import numpy as np
from nltk.stem.snowball import SnowballStemmer

ChunkInput = Union[str, np.ndarray, Tuple[str, np.ndarray]]
ImageBatchOutput = List[Tuple[str, np.ndarray]]  # [(image_id, descriptores_Nx128), ...]
TextChunk = Tuple[str, str]                  
TextBatchOutput = List[Tuple[str, Dict[str, int]]]  # [(text_id, bow_dict), ...]


class BaseFeatureExtractor(ABC):
    @property
    @abstractmethod
    def format(self) -> str:
        # identificador del formato: imagen o texto
        pass
    @abstractmethod
    def extract_features(self, data: Any) -> Any:
        pass


class ImageFeatureExtractor(BaseFeatureExtractor):
    def __init__(self) -> None:
        self._sift = cv2.SIFT_create(nfeatures=150)

    @property
    def format(self) -> str:
        return "image"

    def extract_features(self, chunks: List[Tuple[str, np.ndarray]]) -> ImageBatchOutput:
        results: ImageBatchOutput = []
        for image_id, chunk_matriz in chunks:
            descriptors = self.extract_sift_features(chunk_matriz)
            results.append((image_id, descriptors))
        return results
    
    # image1, matriz

    def extract_sift_features(self, image_input: ChunkInput) -> np.ndarray:
        if isinstance(image_input, tuple):
            _, image_input = image_input

        if isinstance(image_input, str):
            img = cv2.imread(image_input, cv2.IMREAD_COLOR)
            if img is None:
                raise FileNotFoundError(f"No se pudo cargar la imagen: {image_input}")
        else:
            img = image_input

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        keypoints, descriptors = self._sift.detectAndCompute(gray, None)

        if descriptors is None:
            return np.empty((0, 128), dtype=np.float32)

        return descriptors

class TextFeatureExtractor(BaseFeatureExtractor):
    def __init__(self, stopwords_path: str = "") -> None:
        self._stemmer = SnowballStemmer("spanish")
        self._stop_words: Set[str] = self._load_stopwords(stopwords_path)

    @property
    def format(self) -> str:
        return "text"

    def extract_features(
        self, chunks: List[TextChunk]
    ) -> Tuple[TextBatchOutput, Set[str]]:

        results: TextBatchOutput = []
        global_vocab: Set[str] = set()

        for text_id, content in chunks:
            bow = self.compute_bow(content)
            results.append((text_id, bow))
            global_vocab.update(bow.keys())

        return results, global_vocab

    def _load_stopwords(self, stopwords_path: str = "") -> Set[str]:
        if not stopwords_path:
            stopwords_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "stopwords.txt"
            )
        try:
            with open(stopwords_path, "r", encoding="utf-8") as f:
                words = {line.strip().lower() for line in f if line.strip()}
            return words
        except FileNotFoundError:
            print(f"Advertencia: no se encontró {stopwords_path}. Usando stopwords vacías.")
            return set()

    def preprocess(self, text: str) -> List[str]:
        # Limpia, tokeniza, filtra stopwords y aplica stemming->lexemas.
        text = text.lower()
        tokens = re.findall(r"\b[a-záéíóúñ0-9]+\b", text)
        tokens = [t for t in tokens if t not in self._stop_words]
        tokens = [self._stemmer.stem(t) for t in tokens]
        return tokens

    def compute_bow(self, text: str) -> Dict[str, int]:
        # diccionario {lexema: frecuencia} para un texto

        tokens = self.preprocess(text)
        bow: Dict[str, int] = {}
        for token in tokens:
            bow[token] = bow.get(token, 0) + 1
        return bow



if __name__ == "__main__":
    print("=" * 70)
    print("EJEMPLO: ImageFeatureExtractor (formato batch)")
    print("=" * 70)

    dummy_img = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)

    chunks_mock: List[Tuple[str, np.ndarray]] = [
        ("product_001", dummy_img[:100, :100]),
        ("product_001", dummy_img[:100, 100:]),
        ("product_001", dummy_img[100:, :100]),
        ("product_001", dummy_img[100:, 100:]),
    ]

    img_ext = ImageFeatureExtractor()
    batch_result = img_ext.extract_features(chunks_mock)

    print(f"Total chunks procesados: {len(batch_result)}")
    for img_id, desc in batch_result:
        print(f"  {img_id} -> descriptores {desc.shape}")
    print(f"Modalidad: {img_ext.format}")
    print()

    print("=" * 70)
    print("EJEMPLO: TextFeatureExtractor")
    print("=" * 70)

    mock_chunks: List[TextChunk] = [
        (
            "text_001",
            "El comercio electrónico está transformando la economía digital. "
            "Las empresas deben arreglar sus estrategias de venta online.",
        ),
        (
            "text_001",
            "La inteligencia artificial y el aprendizaje automático están "
            "revolucionando la industria de la moda en todo el mundo.",
        ),
    ]

    txt_extractor = TextFeatureExtractor()

    results, vocab = txt_extractor.extract_features(mock_chunks)

    print("Chunks de entrada:")
    for cid, content in mock_chunks:
        print(f"  {cid}: {content[:60]}...")
    print()

    print("Resultados por chunk (BoW local):")
    for text_id, bow in results:
        print(f"  {text_id}: {bow}")

    print(f"\nVocabulario global ({len(vocab)} lexemas únicos):")
    print(f"  {sorted(vocab)}")
    print(f"Modalidad: {txt_extractor.format}")
