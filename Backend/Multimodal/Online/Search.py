import heapq
import math
import os
import pickle
import time

import numpy as np

from ..Offline.InverseIndex import DATA_DIR
from ..Utils.BPlusTree import BPlusTree
from ..Utils.BufferManager import BufferManager


class Search:
    def __init__(self, n_documents: int, buffer_size: int = 1_000_000_000):
        self.n_documents = n_documents
        self.buffer_manager = BufferManager(buffer_size)
        self._data_dir = os.path.join(DATA_DIR, str(n_documents))
        self._text_btree: BPlusTree | None = None
        self._image_btree: BPlusTree | None = None
        self._text_word_idf: dict[int, float] | None = None
        self._image_word_idf: dict[int, float] | None = None
        self._text_doc_norm: dict[int, float] | None = None
        self._image_doc_norm: dict[int, float] | None = None
        self._query_time: float = 0.0

    # ── I/O metrics (delega al BufferManager) ──────────────────

    def reset_io_counters(self) -> None:
        self.buffer_manager.reset_io_counters()
        self._query_time = 0.0

    def io_metrics(self) -> dict:
        m = self.buffer_manager.io_metrics()
        m["query_ms"] = round(self._query_time * 1000, 3)
        return m

    # ── Lazy load ──────────────────────────────────────────────

    def _lazy_load(self, prefix: str) -> tuple[BPlusTree, dict[int, float], dict[int, float]]:
        btree_attr = f'_{prefix}_btree'
        word_idf_attr = f'_{prefix}_word_idf'
        doc_norm_attr = f'_{prefix}_doc_norm'

        if getattr(self, btree_attr) is None:
            fids = {
                'text':  (0, 1),
                'image': (2, 3),
            }
            bf, hf = fids[prefix]

            btree = BPlusTree(
                os.path.join(self._data_dir, f'{prefix}_index_{self.n_documents}.btree'),
                os.path.join(self._data_dir, f'{prefix}_index_{self.n_documents}.heap'),
                btree_file_id=bf,
                heap_file_id=hf,
                buffer_manager=self.buffer_manager,
            )
            with open(os.path.join(self._data_dir, f'{prefix}_word_idf_{self.n_documents}.pkl'), 'rb') as f:
                word_idf = pickle.load(f)
            with open(os.path.join(self._data_dir, f'{prefix}_doc_norm_{self.n_documents}.pkl'), 'rb') as f:
                doc_norm = pickle.load(f)

            setattr(self, btree_attr, btree)
            setattr(self, word_idf_attr, word_idf)
            setattr(self, doc_norm_attr, doc_norm)

        return (
            getattr(self, btree_attr),
            getattr(self, word_idf_attr),
            getattr(self, doc_norm_attr),
        )

    # ── Scoring ───────────────────────────────────────────────

    @staticmethod
    def _score(
        histogram: np.ndarray,
        btree: BPlusTree,
        word_idf: dict[int, float],
        doc_norm: dict[int, float],
    ) -> dict[int, float]:
        query_weights: dict[int, float] = {}
        query_norm_sq = 0.0

        for codeword_id in np.nonzero(histogram)[0]:
            tf = float(histogram[codeword_id])
            idf = word_idf.get(codeword_id)
            if idf is None or idf == 0.0:
                continue
            w = tf * idf
            query_weights[codeword_id] = w
            query_norm_sq += w * w

        query_norm = math.sqrt(query_norm_sq) if query_norm_sq > 0 else 1.0

        scores: dict[int, float] = {}
        for codeword_id, qw in query_weights.items():
            posting_list = btree.get_posting_list(codeword_id)
            if posting_list is None:
                continue
            idf = word_idf.get(codeword_id) or 0.0
            for posting in posting_list:
                dw = posting.TF * idf
                scores[posting.DOC_ID] = scores.get(posting.DOC_ID, 0.0) + qw * dw

        for doc_id in scores:
            d_norm = doc_norm.get(doc_id)
            if d_norm is not None and d_norm > 0:
                scores[doc_id] /= d_norm * query_norm

        return scores

    # ── Search methods ────────────────────────────────────────

    def text_search(
        self,
        text_histogram: np.ndarray,
        text_weight: float = 1.0,
    ) -> list[tuple[float, int]]:
        t0 = time.perf_counter()
        btree, word_idf, doc_norm = self._lazy_load('text')
        scores = self._score(text_histogram, btree, word_idf, doc_norm)
        heap = [(-s * text_weight, doc_id) for doc_id, s in scores.items()]
        heapq.heapify(heap)
        self._query_time = time.perf_counter() - t0
        return heap

    def multimodal_search(
        self,
        text_histogram: np.ndarray,
        image_histogram: np.ndarray,
        text_weight: float,
        image_weight: float,
    ) -> list[tuple[float, int]]:
        t0 = time.perf_counter()
        t_btree, t_widf, t_norm = self._lazy_load('text')
        i_btree, i_widf, i_norm = self._lazy_load('image')
        text_scores = self._score(text_histogram, t_btree, t_widf, t_norm)
        image_scores = self._score(image_histogram, i_btree, i_widf, i_norm)

        combined: dict[int, float] = {}
        for doc_id, s in text_scores.items():
            combined[doc_id] = combined.get(doc_id, 0.0) + s * text_weight
        for doc_id, s in image_scores.items():
            combined[doc_id] = combined.get(doc_id, 0.0) + s * image_weight

        heap = [(-s, doc_id) for doc_id, s in combined.items()]
        heapq.heapify(heap)
        self._query_time = time.perf_counter() - t0
        return heap
