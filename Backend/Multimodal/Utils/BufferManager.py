import os
from collections import OrderedDict

PageID = tuple[int, int]

class BufferManager:
    def __init__(self, buffer_size: int = 1_000_000_000):
        self.buffer_size = buffer_size
        self.current_size = 0
        self._cache: OrderedDict[PageID, bytearray] = OrderedDict()
        self._files: dict[int, tuple[str, int, int]] = {}
        self._handles: dict[int, int] = {}

    def register_file(
        self,
        file_id: int,
        filepath: str,
        page_size: int,
        header_size: int,
    ) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self._files[file_id] = (filepath, page_size, header_size)

    def read_page(self, page_id: PageID) -> bytearray:
        file_id, page_number = page_id

        if page_id in self._cache:
            self._cache.move_to_end(page_id)
            return self._cache[page_id]

        filepath, page_size, header_size = self._files[file_id]
        offset = header_size + page_number * page_size

        with open(filepath, "rb") as f:
            f.seek(offset)
            data = f.read(page_size)

        cached = bytearray(data)
        self._cache[page_id] = cached
        self.current_size += page_size
        self._evict()

        return cached

    def write_page(self, page_id: PageID, data: bytearray) -> None:
        file_id, page_number = page_id
        filepath, page_size, header_size = self._files[file_id]
        offset = header_size + page_number * page_size

        with open(filepath, "rb+") as f:
            f.seek(offset)
            f.write(data)

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
        self._cache.clear()
        self.current_size = 0

    @property
    def size(self) -> int:
        return self.current_size
