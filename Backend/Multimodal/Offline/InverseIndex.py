from sys import getsizeof
import os
import tempfile
import shutil
from ..Utils.BPlusTree import BPlusTree

EMPTY_DICT_SIZE = getsizeof({})
DICT_PAIR_OVERHEAD = 72
INT_SIZE = getsizeof(0)

def _estimate_pair_mem(is_new_codeword: bool, is_new_doc: bool) -> int:
    mem = 0
    if is_new_codeword:
        mem += EMPTY_DICT_SIZE + DICT_PAIR_OVERHEAD + INT_SIZE
    if is_new_doc:
        mem += DICT_PAIR_OVERHEAD + INT_SIZE * 2
    return mem

def SPIMIndexConstruction(
    token_stream: list[tuple[int, int]],
    btree_path: str,
    heap_path: str,
    buffer_size: int = 50_000_000,
) -> BPlusTree:
    buffer: dict[int, dict[int, int]] = {}
    buffer_mem = 0
    block_id = 0
    tmp_dir = tempfile.mkdtemp(prefix="spimi_blocks_")
    blocks: list[tuple[str, str]] = []

    try:
        for doc_id, codeword_id in token_stream:
            if codeword_id not in buffer:
                buffer[codeword_id] = {}
                buffer_mem += _estimate_pair_mem(is_new_codeword=True, is_new_doc=False)

            freqs = buffer[codeword_id]
            if doc_id not in freqs:
                buffer_mem += _estimate_pair_mem(is_new_codeword=False, is_new_doc=True)

            freqs[doc_id] = freqs.get(doc_id, 0) + 1

            if buffer_mem >= buffer_size:
                block = _flush_buffer(buffer, tmp_dir, block_id)
                blocks.append(block)
                block_id += 1
                buffer.clear()
                buffer_mem = 0

        if buffer:
            block = _flush_buffer(buffer, tmp_dir, block_id)
            blocks.append(block)

        if blocks:
            return merge_blocks(blocks, btree_path, heap_path)
        else:
            return BPlusTree(btree_path, heap_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _flush_buffer(
    buffer: dict[int, dict[int, int]],
    tmp_dir: str,
    block_id: int,
) -> tuple[str, str]:
    block_btree = os.path.join(tmp_dir, f"block_{block_id}.btree")
    block_heap = os.path.join(tmp_dir, f"block_{block_id}.heap")
    btree = BPlusTree(block_btree, block_heap)
    for codeword_id, doc_freqs in buffer.items():
        for doc_id, freq in doc_freqs.items():
            btree.insert_posting(codeword_id, (doc_id, freq))
    return (block_btree, block_heap)


def merge_blocks(
    blocks: list[tuple[str, str]],
    final_btree_path: str,
    final_heap_path: str,
) -> BPlusTree:
    iterators = []
    current = []

    for btree_path, heap_path in blocks:
        btree = BPlusTree(btree_path, heap_path)
        it = btree.scan()
        iterators.append(it)
        try:
            current.append(next(it))
        except StopIteration:
            current.append(None)

    final_btree = BPlusTree(final_btree_path, final_heap_path)

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

        for doc_id, tf in merged.items():
            final_btree.insert_posting(min_key, (doc_id, tf))

    return final_btree
