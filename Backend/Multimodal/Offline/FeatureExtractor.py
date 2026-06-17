import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set, Tuple, Union

import cv2
import numpy as np
import pandas as pd
import psycopg2
from nltk.stem.snowball import SnowballStemmer

ChunkInput = Union[str, np.ndarray, Tuple[str, np.ndarray]]


class BaseFeatureExtractor(ABC):
    @property
    @abstractmethod
    def modality(self) -> str:
        # identificador del formato: imagen o texto
        pass
    @abstractmethod
    def extract_features(self, data: Any) -> Any:
        pass


class ImageFeatureExtractor(BaseFeatureExtractor):
    def __init__(self) -> None:
        self._sift = cv2.SIFT_create(nfeatures=150)

    @property
    def modality(self) -> str:
        return "image"

    def extract_features(self, image_input: ChunkInput) -> np.ndarray:
        return self.extract_sift_features(image_input)

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
        # descriptores SIFT (N, 128)
        keypoints, descriptors = self._sift.detectAndCompute(gray, None)

        if descriptors is None: #no se encontro contraste en la imagen -> imagen lisa con color homogeneo
            return np.empty((0, 128), dtype=np.float32)

        return descriptors


class TextFeatureExtractor(BaseFeatureExtractor):
    """Extrae características Bag of Words (BoW) a partir de texto."""

    def __init__(self, connection_params: Dict[str, Any]) -> None:
        self._conn_params = connection_params
        self._stemmer = SnowballStemmer("spanish")
        self._stop_words: Set[str] = self._load_stopwords()

    @property
    def modality(self) -> str:
        return "text"

    def extract_features(self, dataframe: pd.DataFrame) -> Tuple[List[Tuple[Any, Dict[str, int]]], Set[str]]:
        """Implementación concreta: extrae BoW sobre todo un corpus."""
        return self.extract_features_corpus(dataframe)

    def _load_stopwords(self) -> Set[str]:
        """Carga las stopwords desde la tabla 'stopwords' en PostgreSQL."""
        try:
            conn = psycopg2.connect(**self._conn_params)
            query = "SELECT word FROM stopwords;"
            df = pd.read_sql(query, conn)
            conn.close()
            return set(df["word"].str.lower())
        except Exception as e:
            raise ConnectionError(f"Error al cargar stopwords desde PostgreSQL: {e}")

    def preprocess(self, text: str) -> List[str]:
        """Limpia, tokeniza, filtra stopwords y aplica stemming.

        Returns:
            Lista de lexemas (raíces) generados por el stemmer.
        """
        text = text.lower()
        tokens = re.findall(r"\b[a-záéíóúñ0-9]+\b", text)
        tokens = [t for t in tokens if t not in self._stop_words]
        tokens = [self._stemmer.stem(t) for t in tokens]
        return tokens

    def compute_bow(self, text: str) -> Dict[str, int]:
        """Construye el diccionario {lexema: frecuencia} para un texto dado."""
        tokens = self.preprocess(text)
        bow: Dict[str, int] = {}
        for token in tokens:
            bow[token] = bow.get(token, 0) + 1
        return bow

    def extract_features_corpus(
        self, dataframe: pd.DataFrame, id_col: str = "id", text_col: str = "contenido"
    ) -> Tuple[List[Tuple[Any, Dict[str, int]]], Set[str]]:
        """Procesa cada fila del DataFrame extrayendo BoW y el vocabulario global.

        Args:
            dataframe: DataFrame con columnas id_col (identificador) y text_col (texto a procesar).
            id_col: Nombre de la columna que contiene el identificador del chunk/documento.
            text_col: Nombre de la columna que contiene el texto a procesar.

        Returns:
            Tuple con:
                - Lista de tuplas [(chunk_id, {lexema: frecuencia}), ...]
                - Set con el vocabulario global (todos los lexemas únicos del corpus).
        """
        results: List[Tuple[Any, Dict[str, int]]] = []
        global_vocab: Set[str] = set()

        for _, row in dataframe.iterrows():
            chunk_id = row[id_col]
            text = row[text_col]
            bow = self.compute_bow(text)
            results.append((chunk_id, bow))
            global_vocab.update(bow.keys())

        return results, global_vocab
