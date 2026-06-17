from typing import (Iterator, Iterable, Tuple, List)

from collections import Counter

import numpy as np

from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import normalize

class VisualCodebookBuilder:

    def __init__(self, batch_size: int = 1024, k_candidates: Iterable[int] = range(10, 101, 10), random_state: int = 42):

        self.batch_size = batch_size
        self.k_candidates = list(k_candidates)
        self.random_state = random_state

    # batchs de vectores, normalizados
    def _batch_generator(self, data: Iterator[Tuple[str, np.ndarray]]) -> Iterator[np.ndarray]:
        batch = []

        for _, vector in data:                                                                                                            
            batch.append(vector)
            if len(batch) == self.batch_size:
                yield self._normalize(batch)
                batch = []

        if batch:
            yield self._normalize(batch)

    # normalizacion l2 por el feature SIFT
    def _normalize(self, vectors: List[np.ndarray]) -> np.ndarray:
        matrix = np.asarray(vectors)
        return normalize(matrix, norm="l2")
    
    # experimento para encontrar el k ideal
    def _estimate_inertia(self, data_factory, k: int) -> float:
        model = MiniBatchKMeans(n_clusters=k, batch_size=self.batch_size, random_state=self.random_state)

        for batch in self._batch_generator(data_factory()):
            model.partial_fit(batch)

        return model.inertia_

    def _select_k(self, data_factory) -> int:
        inertias = {}

        for k in self.k_candidates:
            inertia = self._estimate_inertia(data_factory, k)
            inertias[k] = inertia


        ks = list(inertias.keys())
        improvements = []


        for i in range(1, len(ks)):
            prev = inertias[ks[i-1]]
            curr = inertias[ks[i]]

            improvement = (prev - curr) / prev

            improvements.append(improvement)

        if not improvements:
            return ks[0]

        elbow_index = np.argmin(improvements)

        return ks[elbow_index + 1]
    
    # modelo final
    def build(self, data_factory) -> np.ndarray:
        
        best_k = self._select_k(data_factory)
        print(f"K seleccionado: {best_k}")

        model = MiniBatchKMeans(n_clusters=best_k, batch_size=self.batch_size, random_state=self.random_state)

        for batch in self._batch_generator (data_factory()):
            model.partial_fit(batch)

        return model.cluster_centers_


class TextCodebookBuilder:

    def __init__(self):
        pass

    # cuenta las palabras y devuelve las mas comunes
    def build(self, documents: Iterator[Tuple[str, list[str]]], top_k: int = 100) -> List[str]:
        counter = Counter()

        for _, tokens in documents:

            counter.update(tokens)

        return [word for word, _ in counter.most_common(top_k)] #sorted