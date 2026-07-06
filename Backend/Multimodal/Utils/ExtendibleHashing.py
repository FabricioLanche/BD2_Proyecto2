import os
import struct
from dataclasses import dataclass
from typing import Iterator, Optional

from .BufferManager import BufferManager
from .HeapFile import HeapFile

# ── Formatos de serialización ───────────────────────────────────────

FILE_HEADER_FORMAT = "<3i"     # global_depth, page_size, n_pages
FILE_HEADER_SIZE = struct.calcsize(FILE_HEADER_FORMAT)

BUCKET_HEADER_FORMAT = "<2i"   # local_depth, n_entries
BUCKET_HEADER_SIZE = struct.calcsize(BUCKET_HEADER_FORMAT)

HASH_ENTRY_FORMAT = "<2i"      # key, ptr (page_number en value file)
HASH_ENTRY_SIZE = struct.calcsize(HASH_ENTRY_FORMAT)

VALUE_FORMAT = "<f"            # float (4 bytes)
VALUE_SIZE = struct.calcsize(VALUE_FORMAT)

# ── Dataclasses de formato en disco ─────────────────────────────────

@dataclass
class FileHeader:
    """Cabecera del archivo de cubetas (bucket file) o de valores (value file)."""
    GLOBAL_DEPTH: int = 4
    PAGE_SIZE: int = 8192
    N_PAGES: int = 0


@dataclass
class BucketHeader:
    """Cabecera de cada página-cubeta dentro del bucket file."""
    LOCAL_DEPTH: int
    N_ENTRIES: int


@dataclass
class HashEntry:
    """Entrada individual dentro de una cubeta.
    PTR es el índice lineal del float en el value file (ptr // 2048 = página,
    ptr % 2048 = offset dentro de la página).
    """
    KEY: int
    PTR: int


@dataclass
class ValueRecord:
    """Float almacenado en el value file.
    Los floats se empaquetan secuencialmente, 2048 por página de 8KB.
    """
    VALUE: float


# ── Implementación ──────────────────────────────────────────────────

class ExtendibleHashing:
    """Índice hash extensible para pares (int → float).

    Archivos:
      - bucket file  (.hash):         FileHeader + cubetas con HashEntry(key, ptr)
      - value heap   (.hash.val):      HeapFile con FloatPage (floats empaquetados)
      - directorio   (.hash.dir):      arreglo de page_number (I/O directo)
    """

    def __init__(
        self,
        filename: str,
        bucket_file_id: int,
        value_file_id: int,
        buffer_manager: BufferManager,
    ):
        self.BUCKET_FID = bucket_file_id
        self.BUCKET_PATH = filename
        self.DIR_PATH = filename + ".dir"
        self.HEAP_FILE = HeapFile(
            filename + ".val", value_file_id, buffer_manager,
        )
        self.BUFFER_MANAGER = buffer_manager
        self._directory: list[int] = []

        # Leer o crear cabeceras
        fresh = False
        try:
            self._read_bucket_header()
            self._read_directory()
        except (FileNotFoundError, struct.error):
            self.FILE_HEADER = FileHeader()
            os.makedirs(os.path.dirname(self.BUCKET_PATH), exist_ok=True)
            open(self.BUCKET_PATH, "ab").close()
            open(self.DIR_PATH, "ab").close()
            fresh = True
        else:
            if not self._directory:
                fresh = True

        self.MAX_ENTRIES = (
            self.FILE_HEADER.PAGE_SIZE - BUCKET_HEADER_SIZE
        ) // HASH_ENTRY_SIZE
        self.FLOATS_PER_PAGE = self.HEAP_FILE.MAX_FLOATS

        # Registrar bucket file en BufferManager
        self.BUFFER_MANAGER.register_file(
            bucket_file_id, self.BUCKET_PATH,
            self.FILE_HEADER.PAGE_SIZE,
            FILE_HEADER_SIZE,
        )

        if fresh:
            self._init_structure()

    # ── Bucket file I/O ─────────────────────────────────────────────

    def _read_bucket_header(self) -> None:
        with open(self.BUCKET_PATH, "rb+") as f:
            f.seek(0)
            gd, ps, np_ = struct.unpack(
                FILE_HEADER_FORMAT, f.read(FILE_HEADER_SIZE)
            )
            self.FILE_HEADER = FileHeader(
                GLOBAL_DEPTH=gd, PAGE_SIZE=ps, N_PAGES=np_
            )

    def _write_bucket_header(self) -> None:
        with open(self.BUCKET_PATH, "rb+") as f:
            f.seek(0)
            f.write(struct.pack(
                FILE_HEADER_FORMAT,
                self.FILE_HEADER.GLOBAL_DEPTH,
                self.FILE_HEADER.PAGE_SIZE,
                self.FILE_HEADER.N_PAGES,
            ))

    # ── Value heap I/O ──────────────────────────────────────────────
    #
    # Usa un HeapFile con FloatPage (hasta FLOATS_PER_PAGE floats por página).
    # ptr = índice lineal del float (0, 1, 2, …).
    #   página = ptr // FLOATS_PER_PAGE
    #   offset = ptr % FLOATS_PER_PAGE
    #
    # _val_count se persiste al inicio del archivo .dir (antes del directorio).

    def _ensure_value_ptr(self, ptr: int) -> None:
        needed = (ptr // self.FLOATS_PER_PAGE) + 1
        while self.HEAP_FILE.FILE_HEADER.N_PAGES < needed:
            self.HEAP_FILE.create_float_page(self.FLOATS_PER_PAGE)

    def _alloc_value_ptr(self) -> int:
        ptr = self._val_count
        self._val_count += 1
        self._ensure_value_ptr(ptr)
        return ptr

    def _read_value(self, ptr: int) -> float:
        pn = ptr // self.FLOATS_PER_PAGE
        off = ptr % self.FLOATS_PER_PAGE
        values = self.HEAP_FILE.read_float_values(
            (self.HEAP_FILE.FILE_ID, pn)
        )
        return values[off]

    def _write_value(self, ptr: int, value: float) -> None:
        pn = ptr // self.FLOATS_PER_PAGE
        off = ptr % self.FLOATS_PER_PAGE
        page_id = (self.HEAP_FILE.FILE_ID, pn)
        data = bytearray(self.BUFFER_MANAGER.read_page(page_id))
        # FloatPage: PAGE_HEADER_SIZE(8) + off * FLOAT_ENTRY_SIZE(4)
        struct.pack_into("<f", data, 8 + off * 4, value)
        self.BUFFER_MANAGER.write_page(page_id, data)

    # ── Directory I/O ───────────────────────────────────────────────

    def _read_directory(self) -> None:
        ds = 1 << self.FILE_HEADER.GLOBAL_DEPTH
        if not os.path.exists(self.DIR_PATH):
            self._directory = []
            self._val_count = 0
            return
        fsize = os.path.getsize(self.DIR_PATH)
        if fsize < 4 + ds * 4:
            self._directory = []
            self._val_count = 0
            return
        with open(self.DIR_PATH, "rb") as f:
            self._val_count = struct.unpack("<i", f.read(4))[0]
            self._directory = list(struct.unpack(f"<{ds}i", f.read(ds * 4)))

    def _write_directory(self) -> None:
        with open(self.DIR_PATH, "wb") as f:
            f.write(struct.pack("<i", self._val_count))
            f.write(struct.pack(
                f"<{len(self._directory)}i", *self._directory
            ))

    # ── Bucket helpers ──────────────────────────────────────────────

    def _init_structure(self) -> None:
        self._val_count = 0
        self._directory.clear()
        for _ in range(1 << self.FILE_HEADER.GLOBAL_DEPTH):
            pn = self._alloc_bucket(self.FILE_HEADER.GLOBAL_DEPTH)
            self._directory.append(pn)
        self._write_bucket_header()
        self._write_directory()

    def _alloc_bucket(self, init_depth: int) -> int:
        pn = self.FILE_HEADER.N_PAGES
        self.FILE_HEADER.N_PAGES += 1
        data = bytearray(self.FILE_HEADER.PAGE_SIZE)
        struct.pack_into(BUCKET_HEADER_FORMAT, data, 0, init_depth, 0)
        self.BUFFER_MANAGER.write_page((self.BUCKET_FID, pn), data)
        return pn

    def _read_bucket(
        self, page_number: int
    ) -> tuple[int, list[tuple[int, int]]]:
        data = self.BUFFER_MANAGER.read_page((self.BUCKET_FID, page_number))
        local_depth, n = struct.unpack_from(BUCKET_HEADER_FORMAT, data, 0)
        entries: list[tuple[int, int]] = []
        off = BUCKET_HEADER_SIZE
        for _ in range(n):
            k, ptr = struct.unpack_from(HASH_ENTRY_FORMAT, data, off)
            entries.append((k, ptr))
            off += HASH_ENTRY_SIZE
        return local_depth, entries

    def _write_bucket(
        self, page_number: int, local_depth: int,
        entries: list[tuple[int, int]],
    ) -> None:
        data = bytearray(self.FILE_HEADER.PAGE_SIZE)
        struct.pack_into(BUCKET_HEADER_FORMAT, data, 0, local_depth, len(entries))
        off = BUCKET_HEADER_SIZE
        for k, ptr in entries:
            struct.pack_into(HASH_ENTRY_FORMAT, data, off, k, ptr)
            off += HASH_ENTRY_SIZE
        self.BUFFER_MANAGER.write_page((self.BUCKET_FID, page_number), data)

    # ── Hashing (Knuth multiplicativo, ~10× más rápido que SHA-256) ──

    @staticmethod
    def _hash_key(key: int) -> int:
        key = int(key)
        return (key * 0x9E3779B97F4A7C15) & 0xFFFFFFFF

    def _hash_idx(self, key: int) -> int:
        return self._hash_key(key) >> (32 - self.FILE_HEADER.GLOBAL_DEPTH)

    # ── Public API ──────────────────────────────────────────────────

    def put(self, key: int, value: float) -> None:
        while True:
            bidx = self._hash_idx(key)
            pn = self._directory[bidx]
            local_depth, entries = self._read_bucket(pn)

            for i, (k, ptr) in enumerate(entries):
                if k == key:
                    self._write_value(ptr, value)
                    return

            if len(entries) < self.MAX_ENTRIES:
                ptr = self._alloc_value_ptr()
                self._write_value(ptr, value)
                entries.append((key, ptr))
                self._write_bucket(pn, local_depth, entries)
                return

            if local_depth == self.FILE_HEADER.GLOBAL_DEPTH:
                self._double_directory()
                continue

            self._split_bucket(pn, local_depth, entries)

    def get(self, key: int) -> Optional[float]:
        bidx = self._hash_idx(key)
        if bidx >= len(self._directory):
            return None
        _, entries = self._read_bucket(self._directory[bidx])
        for k, ptr in entries:
            if k == key:
                return self._read_value(ptr)
        return None

    def items(self) -> Iterator[tuple[int, float]]:
        seen: set[int] = set()
        for pn in self._directory:
            if pn in seen:
                continue
            seen.add(pn)
            _, entries = self._read_bucket(pn)
            for k, ptr in entries:
                yield (k, self._read_value(ptr))

    def close(self) -> None:
        self._write_bucket_header()
        self._write_directory()
        self.HEAP_FILE.write_file_header()

    # ── Split / double ──────────────────────────────────────────────

    def _double_directory(self) -> None:
        old = self._directory
        self._directory = [0] * (len(old) * 2)
        for i, p in enumerate(old):
            self._directory[2 * i] = p
            self._directory[2 * i + 1] = p
        self.FILE_HEADER.GLOBAL_DEPTH += 1
        self._write_bucket_header()
        self._write_directory()

    def _split_bucket(
        self, page_number: int, local_depth: int,
        entries: list[tuple[int, int]],
    ) -> None:
        mask = 1 << local_depth
        g0: list[tuple[int, int]] = []
        g1: list[tuple[int, int]] = []
        for k, ptr in entries:
            if self._hash_key(k) & mask:
                g1.append((k, ptr))
            else:
                g0.append((k, ptr))

        new_depth = local_depth + 1
        new_pn = self._alloc_bucket(new_depth)
        self._write_bucket(page_number, new_depth, g0)
        self._write_bucket(new_pn, new_depth, g1)

        for i in range(len(self._directory)):
            if self._directory[i] == page_number and (i & mask):
                self._directory[i] = new_pn
        self._write_directory()


# ── Clases tipadas para cada uso ────────────────────────────────────

class IDFHash(ExtendibleHashing):
    """Índice hash extensible para word_id → idf."""
    pass


class DocNormHash(ExtendibleHashing):
    """Índice hash extensible para doc_id → norma_tf_idf."""
    pass
