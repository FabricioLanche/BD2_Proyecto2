from typing import (Iterator, Iterable, Tuple, List, Dict)
from sklearn.cluster import MiniBatchKMeans
from collections import Counter
from pathlib import Path
import numpy as np
import pickle

DATA_DIR = Path(__file__).resolve().parent.parent / "Data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

class VisualCodebookBuilder:

    def __init__(
        self,
        k: int = 100,
        batch_size: int = 1024,
        random_state: int = 42
    ):
        self.k = k
        self.batch_size = batch_size
        self.random_state = random_state

    # Creación de batches
    def _batch_generator(
        self,
        data: Iterator[Tuple[int, np.ndarray]]
    ) -> Iterator[np.ndarray]:

        batch = []

        for _, vector in data:
            batch.append(vector)

            if len(batch) == self.batch_size:
                yield np.array(batch)
                batch = []

        if batch:
            yield np.array(batch)

    # Modelo final con K fijo
    def build(
        self,
        data_factory,
        filename: str = "visual_codebook.pkl"
    ) -> np.ndarray:

        print(f"K fijo utilizado: {self.k}")

        model = MiniBatchKMeans(
            n_clusters=self.k,
            batch_size=self.batch_size,
            random_state=self.random_state
        )

        for batch in self._batch_generator(data_factory()):
            model.partial_fit(batch)

        codebook = model.cluster_centers_

        with open(DATA_DIR / filename, "wb") as f:
            pickle.dump(codebook, f)

        return codebook

class TextCodebookBuilder:

    def __init__(self, vocabulary: List[str], chunks: List[Tuple[int, Dict[str, int]]], k: int = 100) -> List[str]:

        self.vocabulary = vocabulary
        self.chunks = chunks
        self.k = k
        
    # Frecuencia global de las palabras basadas en el vocabulario
    def build(self, filename: str = "text_codebook.pkl") -> List[str]:
        global_frequency = Counter()

        for _, bow in self.chunks:
            global_frequency.update(bow)

        top_words = global_frequency.most_common(self.k)
        codebook = [word for word, freq in top_words]

        with open(DATA_DIR / filename, "wb") as f:
            pickle.dump(codebook, f)

        return codebook