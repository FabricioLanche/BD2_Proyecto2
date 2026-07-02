import os
import pickle
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple, Union, overload

import cv2
import numpy as np
from nltk.stem.snowball import SnowballStemmer

ChunkInput = Union[str, np.ndarray, Tuple[int, np.ndarray]]
ImageBatchOutput = List[Tuple[int, np.ndarray]]  # [(image_id, vector_128d), ...] — un tuple por descriptor
TextChunk = Tuple[int, str]                  
TextBatchOutput = List[Tuple[int, Dict[str, int]]]  # [(text_id, bow_dict), ...]


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

    def extract_features(self, chunks: List[Tuple[int, np.ndarray]]) -> ImageBatchOutput:
        results: ImageBatchOutput = []
        for image_id, chunk_matriz in chunks:
            descriptors = self.extract_sift_features(chunk_matriz)
            for i in range(descriptors.shape[0]):
                results.append((image_id, descriptors[i]))
        return results

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

VOCAB_FILENAME = "vocab.pkl"

class TextFeatureExtractor(BaseFeatureExtractor):
    def __init__(self, stopwords_path: str = "", dist_dir: str = "") -> None:
        self._stemmer = SnowballStemmer("english")
        self._stop_words: Set[str] = self._load_stopwords(stopwords_path)
        self._dist_dir = dist_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Data"
        )

    @property
    def format(self) -> str:
        return "text"

    @overload #offline
    def extract_features(
        self, chunks: List[TextChunk], vocab: None = None
    ) -> Tuple[TextBatchOutput, Set[str]]: ...

    @overload #online
    def extract_features(
        self, chunks: List[TextChunk], vocab: Set[str]
    ) -> TextBatchOutput: ...

    def extract_features(
        self, chunks: List[TextChunk], vocab: Optional[Set[str]] = None
    ) -> Union[TextBatchOutput, Tuple[TextBatchOutput, Set[str]]]:

        results: TextBatchOutput = []
        global_vocab: Set[str] = set()

        for text_id, content in chunks:
            bow = self.compute_bow(content, vocab)
            results.append((text_id, bow))
            if vocab is None:
                global_vocab.update(bow.keys())

        if vocab is None:
            self._persist_vocab(global_vocab)
            return results, global_vocab
        return results

    def _persist_vocab(self, vocab: Set[str]) -> None:
        os.makedirs(self._dist_dir, exist_ok=True)
        path = os.path.join(self._dist_dir, VOCAB_FILENAME)
        with open(path, "wb") as f:
            pickle.dump(vocab, f)
        print(f"Vocabulario guardado ({len(vocab)} terminos) en {path}")

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
        tokens = re.findall(r"\b[a-z0-9]+\b", text)
        tokens = [t for t in tokens if t not in self._stop_words]
        tokens = [self._stemmer.stem(t) for t in tokens]
        return tokens

    def compute_bow(self, text: str, vocab: Optional[Set[str]] = None) -> Dict[str, int]:
        tokens = self.preprocess(text)
        if vocab is not None:
            tokens = [t for t in tokens if t in vocab]
        bow: Dict[str, int] = {}
        for token in tokens:
            bow[token] = bow.get(token, 0) + 1
        return bow