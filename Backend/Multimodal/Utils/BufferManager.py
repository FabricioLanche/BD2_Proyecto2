import os
from collections import OrderedDict

PageID = tuple[int, int]


class BufferManager:
    def __init__(self, buffer_size: int = 1_000_000_000):
        self.buffer_size = buffer_size
        self.current_size = 0
        self._cache: OrderedDict[PageID, bytearray] = OrderedDict()
        self._files: dict[int, tuple[str, int, int]] = {}
        self._handles: dict[int, object] = {}

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

    def read_page(self, page_id: PageID) -> bytearray:
        file_id, page_number = page_id

        if page_id in self._cache:
            self._cache.move_to_end(page_id)
            return self._cache[page_id]

        _, page_size, header_size = self._files[file_id]
        offset = header_size + page_number * page_size
        handle = self._get_handle(file_id)
        handle.seek(offset)
        data = handle.read(page_size)

        cached = bytearray(data)
        self._cache[page_id] = cached
        self.current_size += page_size
        self._evict()

        return cached

    def write_page(self, page_id: PageID, data: bytearray) -> None:
        file_id, page_number = page_id
        _, page_size, header_size = self._files[file_id]
        offset = header_size + page_number * page_size
        handle = self._get_handle(file_id)
        handle.seek(offset)
        handle.write(data)

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
