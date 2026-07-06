from typing import List, Tuple

import numpy as np


class TextCodebookTransform:

    persist_histogram = True

    def __init__(self, codebook: List[int]):
        self.codebook = codebook
        self.tokens: List[Tuple[int, int]] = []

    def transform(self, features_list, doc_id: int) -> np.ndarray:
        k = len(self.codebook)
        histogram = np.zeros(k, dtype=np.float32)
        for bow in features_list:
            for i, word_id in enumerate(self.codebook):
                freq = bow.get(word_id, 0)
                histogram[i] += freq
                if freq > 0:
                    self.tokens.append((doc_id, i))
        return histogram


class VisualCodebookTransform:

    persist_histogram = True

    def __init__(self, codebook: np.ndarray):
        self.codebook_np = np.asarray(codebook, dtype=np.float32)
        self.tokens: List[Tuple[int, int]] = []

    def transform(self, features_list, doc_id: int) -> np.ndarray:
        k = len(self.codebook_np)
        histogram = np.zeros(k, dtype=np.float32)
        for descriptor in features_list:
            descriptor = np.asarray(descriptor, dtype=np.float32)
            dists = np.linalg.norm(
                self.codebook_np - descriptor, axis=1,
            )
            codeword_id = int(np.argmin(dists))
            histogram[codeword_id] += 1
            self.tokens.append((doc_id, codeword_id))
        return histogram
