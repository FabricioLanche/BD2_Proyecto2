import math
import os
import pickle
import tempfile
import shutil
from sys import getsizeof

from tqdm import tqdm

from ..Utils.BPlusTree import BPlusTree
from ..Utils.BufferManager import BufferManager

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'Data')

EMPTY_DICT_SIZE = getsizeof({})
DICT_PAIR_OVERHEAD = 72
INT_SIZE = getsizeof(0)


class InverseIndex:
    def __init__(self, n_documents: int, buffer_size: int = 2_000_000_000):
        self.n_documents = n_documents
        self.buffer_manager = BufferManager(buffer_size)

    @staticmethod
    def _estimate_pair_mem(is_new_codeword: bool, is_new_doc: bool) -> int:
        mem = 0
        if is_new_codeword:
            mem += EMPTY_DICT_SIZE + DICT_PAIR_OVERHEAD + INT_SIZE
        if is_new_doc:
            mem += DICT_PAIR_OVERHEAD + INT_SIZE * 2
        return mem

    @staticmethod
    def _flush_buffer(
        buffer: dict[int, dict[int, int]],
        tmp_dir: str,
        block_id: int,
    ) -> tuple[str, str]:
        block_btree = os.path.join(tmp_dir, f"block_{block_id}.btree")
        block_heap = os.path.join(tmp_dir, f"block_{block_id}.heap")
        bm = BufferManager()
        btree = BPlusTree(block_btree, block_heap,
                          btree_file_id=0, heap_file_id=1,
                          buffer_manager=bm)
        for codeword_id, doc_freqs in buffer.items():
            tail: tuple[int, int] | None = None
            for doc_id, freq in doc_freqs.items():
                tail = btree.insert_posting(codeword_id, (doc_id, freq), tail)
        return (block_btree, block_heap)

    @staticmethod
    def _merge_blocks(
        blocks: list[tuple[str, str]],
        final_btree_path: str,
        final_heap_path: str,
        btree_file_id: int,
        heap_file_id: int,
        buffer_manager: BufferManager,
    ) -> BPlusTree:
        iterators = []
        current = []

        for btree_path, heap_path in blocks:
            block_bm = BufferManager()
            btree = BPlusTree(btree_path, heap_path,
                              btree_file_id=0, heap_file_id=1,
                              buffer_manager=block_bm)
            it = btree.scan()
            iterators.append(it)
            try:
                current.append(next(it))
            except StopIteration:
                current.append(None)

        final_btree = BPlusTree(final_btree_path, final_heap_path,
                                btree_file_id=btree_file_id,
                                heap_file_id=heap_file_id,
                                buffer_manager=buffer_manager)

        tails: dict[int, tuple[int, int]] = {}

        while any(e is not None for e in current):
            min_key = min(e[0] for e in current if e is not None)
            merged: dict[int, int] = {}

            for i, entry in enumerate(current):
                if entry is not None and entry[0] == min_key:
                    for posting in entry[1]:
                        merged[posting.DOC_ID] = merged.get(posting.DOC_ID, 0) + posting.TF
                    try:
                        current[i] = next(iterators[i])
                    except StopIteration:
                        current[i] = None

            tail = tails.get(min_key)
            for doc_id, tf in merged.items():
                tail = final_btree.insert_posting(min_key, (doc_id, tf), tail)
            tails[min_key] = tail

        return final_btree

    @staticmethod
    def _spimi_index_construction(
        token_stream: list[tuple[int, int]],
        btree_path: str,
        heap_path: str,
        buffer_size: int,
        btree_file_id: int,
        heap_file_id: int,
        buffer_manager: BufferManager,
    ) -> BPlusTree:
        buffer: dict[int, dict[int, int]] = {}
        buffer_mem = 0
        block_id = 0
        tmp_dir = tempfile.mkdtemp(prefix="spimi_blocks_")
        blocks: list[tuple[str, str]] = []

        try:
            for doc_id, codeword_id in tqdm(
                token_stream, desc="    SPIMI", unit="tok",
            ):
                if codeword_id not in buffer:
                    buffer[codeword_id] = {}
                    buffer_mem += InverseIndex._estimate_pair_mem(
                        is_new_codeword=True, is_new_doc=False
                    )

                freqs = buffer[codeword_id]
                if doc_id not in freqs:
                    buffer_mem += InverseIndex._estimate_pair_mem(
                        is_new_codeword=False, is_new_doc=True
                    )

                freqs[doc_id] = freqs.get(doc_id, 0) + 1

                if buffer_mem >= buffer_size:
                    block = InverseIndex._flush_buffer(buffer, tmp_dir, block_id)
                    blocks.append(block)
                    block_id += 1
                    buffer.clear()
                    buffer_mem = 0

            if buffer:
                block = InverseIndex._flush_buffer(buffer, tmp_dir, block_id)
                blocks.append(block)

            if blocks:
                return InverseIndex._merge_blocks(
                    blocks, btree_path, heap_path,
                    btree_file_id=btree_file_id,
                    heap_file_id=heap_file_id,
                    buffer_manager=buffer_manager,
                )
            else:
                return BPlusTree(btree_path, heap_path,
                                 btree_file_id=btree_file_id,
                                 heap_file_id=heap_file_id,
                                 buffer_manager=buffer_manager)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    @staticmethod
    def _compute_and_persist_tfidf(
        btree: BPlusTree, N: int, prefix: str,
        buffer_manager: BufferManager,
    ) -> None:
        idf_dict: dict[int, float] = {}

        total_postings = sum(len(pl) for _, pl in btree.scan())

        doc_norm_sq: dict[int, float] = {}

        pbar = tqdm(total=total_postings, desc=f"  TF-IDF {prefix}", unit="post")
        for word_id, posting_list in btree.scan():
            df = len(posting_list)
            idf = math.log(N / df) if df > 0 else 0.0
            idf_dict[word_id] = idf

            for posting in posting_list:
                doc_id = posting.DOC_ID
                tf = posting.TF
                weighted = tf * idf
                doc_norm_sq[doc_id] = doc_norm_sq.get(doc_id, 0.0) + weighted * weighted
                pbar.update(1)
        pbar.close()

        doc_norm_dict: dict[int, float] = {
            doc_id: math.sqrt(sq)
            for doc_id, sq in doc_norm_sq.items()
        }

        with open(os.path.join(DATA_DIR, f'{prefix}_word_idf_{N}.pkl'), 'wb') as f:
            pickle.dump(idf_dict, f)
        with open(os.path.join(DATA_DIR, f'{prefix}_doc_norm_{N}.pkl'), 'wb') as f:
            pickle.dump(doc_norm_dict, f)

    def build_text_index(
        self,
        token_stream: list[tuple[int, int]],
        buffer_size: int = 500_000_000,
    ) -> BPlusTree:
        btree_path = os.path.join(DATA_DIR, f'text_index_{self.n_documents}.btree')
        heap_path = os.path.join(DATA_DIR, f'text_index_{self.n_documents}.heap')
        btree = self._spimi_index_construction(
            token_stream, btree_path, heap_path, buffer_size,
            btree_file_id=0, heap_file_id=1,
            buffer_manager=self.buffer_manager,
        )
        self._compute_and_persist_tfidf(btree, self.n_documents, 'text', self.buffer_manager)
        return btree

    def build_image_index(
        self,
        token_stream: list[tuple[int, int]],
        buffer_size: int = 500_000_000,
    ) -> BPlusTree:
        btree_path = os.path.join(DATA_DIR, f'image_index_{self.n_documents}.btree')
        heap_path = os.path.join(DATA_DIR, f'image_index_{self.n_documents}.heap')
        btree = self._spimi_index_construction(
            token_stream, btree_path, heap_path, buffer_size,
            btree_file_id=2, heap_file_id=3,
            buffer_manager=self.buffer_manager,
        )
        self._compute_and_persist_tfidf(btree, self.n_documents, 'image', self.buffer_manager)
        return btree
