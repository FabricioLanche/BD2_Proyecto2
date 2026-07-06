from typing import (Iterator, Iterable, Optional, Tuple, List, Dict)
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
        n_documents: int,
        k: int = 512,
        batch_size: int = 1024,
        random_state: int = 42
    ):
        self.k = k
        self.n_documents = n_documents
        self.batch_size = batch_size
        self.random_state = random_state
        self._model: MiniBatchKMeans | None = None
        self._buffer: List[np.ndarray] = []

    def _init_model(self) -> None:
        if self._model is None:
            self._model = MiniBatchKMeans(
                n_clusters=self.k,
                batch_size=self.batch_size,
                random_state=self.random_state
            )

    def _flush(self) -> None:
        if not self._buffer:
            return
        batch = np.array(self._buffer)
        self._buffer = []
        self._init_model()
        self._model.partial_fit(batch)

    def accumulate(self, features) -> None:
        for _, d in features:
            self._buffer.append(d)
            if len(self._buffer) >= self.batch_size:
                self._flush()

    def finalize(self) -> np.ndarray:
        self._flush()
        self._init_model()
        codebook = self._model.cluster_centers_
        filename = f"visual_codebook_{self.n_documents}.pkl"
        with open(DATA_DIR / filename, "wb") as f:
            pickle.dump(codebook, f)
        return codebook

class TextCodebookBuilder:

    def __init__(
        self, 
        n_documents: int,
        k: int = 1000
    ):
        self.n_documents = n_documents
        self.k = k
        self.counter = Counter()

    def accumulate(self, features) -> None:
        for _, bow in features:
            self.counter.update(bow)

    def finalize(self) -> List[int]:
        top_words = self.counter.most_common(self.k)
        codebook: List[int] = [word_id for word_id, _ in top_words]
        filename = f"text_codebook_{self.n_documents}.pkl"
        with open(DATA_DIR / filename, "wb") as f:
            pickle.dump(codebook, f)
        return codebook