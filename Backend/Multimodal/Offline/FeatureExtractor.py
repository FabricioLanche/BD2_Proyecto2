import os
import pickle
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set, Tuple, Union

import cv2
import numpy as np
from nltk.stem.snowball import SnowballStemmer

ChunkInput = Union[str, np.ndarray, Tuple[int, np.ndarray]]
ImageBatchOutput = List[Tuple[int, np.ndarray]]
TextChunk = Tuple[int, str]
TextBatchOutput = List[Tuple[int, Dict[int, int]]]

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Data")


class BaseFeatureExtractor(ABC):
    @property
    @abstractmethod
    def format(self) -> str:
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


class TextFeatureExtractor(BaseFeatureExtractor):
    def __init__(self, n_documents: int) -> None:
        self.n_documents = n_documents
        self._stemmer = SnowballStemmer("english")
        self._stop_words: Set[str] = self._load_stopwords()
        self._dist_dir = DATA_DIR
        self.vocab: Dict[str, int] = {}
        self._next_id: int = 0
        self._vocab_readonly: bool = False

    def load_vocab(self, vocab: Dict[str, int]) -> None:
        self.vocab = vocab
        self._next_id = max(vocab.values()) + 1 if vocab else 0
        self._vocab_readonly = True

    @property
    def format(self) -> str:
        return "text"

    def extract_features(self, chunks: List[TextChunk]) -> TextBatchOutput:
        results: TextBatchOutput = []
        for text_id, content in chunks:
            bow = self.compute_bow(content)
            results.append((text_id, bow))
        return results

    def compute_bow(self, text: str) -> Dict[int, int]:
        tokens = self.preprocess(text)
        bow: Dict[int, int] = {}
        for token in tokens:
            if token not in self.vocab:
                if self._vocab_readonly:
                    continue
                self.vocab[token] = self._next_id
                self._next_id += 1
            word_id = self.vocab[token]
            bow[word_id] = bow.get(word_id, 0) + 1
        return bow

    def persist_vocab(self) -> None:
        os.makedirs(self._dist_dir, exist_ok=True)
        filename = f"vocab_{self.n_documents}.pkl"
        path = os.path.join(self._dist_dir, filename)
        with open(path, "wb") as f:
            pickle.dump(self.vocab, f)

    def _load_stopwords(self) -> Set[str]:
        _global_data = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Data")
        stopwords_path = os.path.join(_global_data, "stopwords.txt")
        try:
            with open(stopwords_path, "r", encoding="utf-8") as f:
                words = {line.strip().lower() for line in f if line.strip()}
            return words
        except FileNotFoundError:
            print(f"Advertencia: no se encontr\u00f3 {stopwords_path}. Usando stopwords vac\u00edas.")
            return set()

    def preprocess(self, text: str) -> List[str]:
        text = text.lower()
        tokens = re.findall(r"\b[a-z0-9]+\b", text)
        tokens = [t for t in tokens if t not in self._stop_words]
        tokens = [self._stemmer.stem(t) for t in tokens]
        return tokens