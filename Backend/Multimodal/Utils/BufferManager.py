import os
import time
from collections import OrderedDict

PageID = tuple[int, int]


class BufferManager:
    def __init__(self, buffer_size: int = 1_000_000_000):
        self.buffer_size = buffer_size
        self.current_size = 0
        self._cache: OrderedDict[PageID, bytearray] = OrderedDict()
        self._files: dict[int, tuple[str, int, int]] = {}
        self._handles: dict[int, object] = {}
        self.reset_io_counters()

    # ── I/O metrics ────────────────────────────────────────────

    def reset_io_counters(self) -> None:
        self._page_requests = 0
        self._cache_hits = 0
        self._disk_reads = 0
        self._disk_writes = 0
        self._disk_read_time = 0.0
        self._disk_write_time = 0.0

    def io_metrics(self) -> dict:
        return {
            "page_requests": self._page_requests,
            "cache_hits": self._cache_hits,
            "disk_reads": self._disk_reads,
            "disk_writes": self._disk_writes,
            "disk_read_ms": round(self._disk_read_time * 1000, 3),
            "disk_write_ms": round(self._disk_write_time * 1000, 3),
        }

    # ── File registration ──────────────────────────────────────

    def register_file(
        self,
        file_id: int,
        filepath: str,
        page_size: int,
        header_size: int,
    ) -> None:
        self._files[file_id] = (filepath, page_size, header_size)

    def _get_handle(self, file_id: int):
        if file_id not in self._handles:
            filepath, _, _ = self._files[file_id]
            handle = open(filepath, "rb+")
            self._handles[file_id] = handle
        return self._handles[file_id]

    # ── Page I/O ───────────────────────────────────────────────

    def read_page(self, page_id: PageID) -> bytearray:
        self._page_requests += 1

        if page_id in self._cache:
            self._cache_hits += 1
            self._cache.move_to_end(page_id)
            return self._cache[page_id]

        self._disk_reads += 1
        _, page_size, header_size = self._files[page_id[0]]
        offset = header_size + page_id[1] * page_size
        handle = self._get_handle(page_id[0])

        t0 = time.perf_counter()
        handle.seek(offset)
        data = handle.read(page_size)
        self._disk_read_time += time.perf_counter() - t0

        cached = bytearray(data)
        self._cache[page_id] = cached
        self.current_size += page_size
        self._evict()

        return cached

    def write_page(self, page_id: PageID, data: bytearray) -> None:
        self._disk_writes += 1
        file_id, page_number = page_id
        _, page_size, header_size = self._files[file_id]
        offset = header_size + page_number * page_size
        handle = self._get_handle(file_id)

        t0 = time.perf_counter()
        handle.seek(offset)
        handle.write(data)
        self._disk_write_time += time.perf_counter() - t0

        if page_id in self._cache:
            old = self._cache[page_id]
            self.current_size -= len(old)
        self._cache[page_id] = data
        self.current_size += len(data)
        self._evict()

    def _evict(self) -> None:
        while self.current_size > self.buffer_size and self._cache:
            page_id, data = self._cache.popitem(last=False)
            self.current_size -= len(data)

    def close(self) -> None:
        for handle in self._handles.values():
            handle.close()
        self._handles.clear()
        self._cache.clear()
        self.current_size = 0

    @property
    def size(self) -> int:
        return self.current_size
