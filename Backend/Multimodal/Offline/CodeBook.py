from typing import (Iterator, Iterable, Tuple, List, Dict)
from sklearn.cluster import MiniBatchKMeans
from collections import Counter
import numpy as np


class VisualCodebookBuilder:

    def __init__(self, batch_size: int = 1024, k_candidates: Iterable[int] = range(10, 101, 10), random_state: int = 42):

        self.batch_size = batch_size
        self.k_candidates = list(k_candidates)
        self.random_state = random_state

    # Creación de batches
    def _batch_generator(self, data: Iterator[Tuple[int, np.ndarray]]) -> Iterator[np.ndarray]:
        batch = []
        for _, vector in data:                                                                                                            
            batch.append(vector)
            if len(batch) == self.batch_size:
                yield np.array(batch)
                batch=[]

        if batch:
            yield np.array(batch)
    
    # Experimento para encontrar el k ideal con incercia
    def _estimate_inertia(self, data_factory, k: int) -> float:
        model = MiniBatchKMeans(n_clusters=k, batch_size=self.batch_size, random_state=self.random_state)

        for batch in self._batch_generator(data_factory()):
            model.partial_fit(batch)

        return model.inertia_
    
    # Selector del k optimo basado en el metodo del codo
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
    
    # Modelo final
    def build(self, data_factory) -> np.ndarray:
        best_k = self._select_k(data_factory)
        print(f"K seleccionado: {best_k}")

        model = MiniBatchKMeans(n_clusters=best_k, batch_size=self.batch_size, random_state=self.random_state)

        for batch in self._batch_generator (data_factory()):
            model.partial_fit(batch)

        return model.cluster_centers_

class TextCodebookBuilder:

    def __init__(self, vocabulary: List[str], chunks: List[Tuple[int, Dict[str, int]]], k: int = 100) -> List[str]:

        self.vocabulary = vocabulary
        self.chunks = chunks
        self.k = k
        
    # Frecuencia global de las palabras basadas en el vocabulario
    def build(self) -> List[str]:
        global_frequency = Counter()

        for _, bow in self.chunks:
            global_frequency.update(bow)

        top_words = global_frequency.most_common(self.k)

        codebook = [word for word, freq in top_words]

        return codebook