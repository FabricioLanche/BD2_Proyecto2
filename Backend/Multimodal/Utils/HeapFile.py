from dataclasses import dataclass
import struct
import os

@dataclass
class Page:
    PAGE_ID: int
    DATA: bytearray

@dataclass
class PageHeader:
    NEXT_PAGE: int = -1
    N_POSTINGS: int = 0
PAGE_HEADER_FORMAT = "<2i"
PAGE_HEADER_SIZE = struct.calcsize(PAGE_HEADER_FORMAT)

@dataclass
class PostingEntry:
    DOC_ID: int
    TF: int
POSTING_ENTRY_FORMAT = "<2i"
POSTING_ENTRY_SIZE = struct.calcsize(POSTING_ENTRY_FORMAT)

class PostingPage:
    def __init__(self, page_id: int, posting_list: list[PostingEntry], next_page: int = -1):
        self.PAGE_ID = page_id
        self.POSTING_LIST = posting_list
        self.NEXT_PAGE = next_page
        
    @staticmethod
    def from_page(page: Page) -> "PostingPage":
        data = page.DATA
        next_page, n_postings = struct.unpack(PAGE_HEADER_FORMAT, data[:PAGE_HEADER_SIZE])
        posting_list = []
        offset = PAGE_HEADER_SIZE
        for _ in range(n_postings):
            doc_id, tf = struct.unpack(POSTING_ENTRY_FORMAT, data[offset:offset+POSTING_ENTRY_SIZE])
            posting_list.append(PostingEntry(doc_id, tf))
            offset += POSTING_ENTRY_SIZE
        return PostingPage(page.PAGE_ID, posting_list, next_page)

    def to_page(self, page_size: int) -> Page:
        data = bytearray(page_size)
        struct.pack_into(PAGE_HEADER_FORMAT, data, 0, self.NEXT_PAGE, len(self.POSTING_LIST))
        offset = PAGE_HEADER_SIZE
        for entry in self.POSTING_LIST:
            struct.pack_into(POSTING_ENTRY_FORMAT, data, offset, entry.DOC_ID, entry.TF)
            offset += POSTING_ENTRY_SIZE
        return Page(self.PAGE_ID, data)
    
@dataclass
class FileHeader:
    PAGE_SIZE: int = 8192
    N_PAGES: int = 0
FILE_HEADER_FORMAT = "<2i"
FILE_HEADER_SIZE = struct.calcsize(FILE_HEADER_FORMAT)


class HeapFile:
    # FILE_HEADER = FileHeader
    # FILE_PATH = os.path.join(FILE_DIR, "HeapFile.bin")
    # MAX_ENTRIES = (PAGE_SIZE - PAGE_HEADER_SIZE) // POSTING_ENTRY_SIZE

    def __init__(self, filename="HeapFile.bin"):
        self.FILE_PATH = filename 
        try:
            self.read_file_header()
        except (FileNotFoundError, struct.error):
            self.FILE_HEADER = FileHeader()
            os.makedirs(os.path.dirname(self.FILE_PATH), exist_ok=True)
            open(self.FILE_PATH, "ab").close()
            self.write_file_header()
        finally:
            self.MAX_ENTRIES = (self.FILE_HEADER.PAGE_SIZE - PAGE_HEADER_SIZE) // POSTING_ENTRY_SIZE

    def read_file_header(self) -> None: 
        with open(self.FILE_PATH, "rb+") as file:
            file.seek(0)
            header_data = file.read(FILE_HEADER_SIZE)
            header_values = struct.unpack(FILE_HEADER_FORMAT, header_data)
            self.FILE_HEADER = FileHeader(*header_values)
        
    def write_file_header(self) -> None:
        with open(self.FILE_PATH, "rb+") as file:
            file.seek(0)
            file.write(struct.pack(
                FILE_HEADER_FORMAT,
                self.FILE_HEADER.PAGE_SIZE,
                self.FILE_HEADER.N_PAGES
            ))

    def read_page(self, page_id: int) -> Page:
        offset = FILE_HEADER_SIZE + page_id * self.FILE_HEADER.PAGE_SIZE
        with open(self.FILE_PATH, "rb") as file:
            file.seek(offset)
            data = file.read(self.FILE_HEADER.PAGE_SIZE)
            if len(data) != self.FILE_HEADER.PAGE_SIZE:
                raise ValueError("Página incompleta o inexistente")
        return Page(page_id, bytearray(data))
    
    def write_page(self, page: Page):
        if len(page.DATA) != self.FILE_HEADER.PAGE_SIZE:
            raise ValueError("Tamaño de página incorrecto")
        offset = FILE_HEADER_SIZE + page.PAGE_ID * self.FILE_HEADER.PAGE_SIZE
        with open(self.FILE_PATH, "rb+") as file:
            file.seek(offset)
            file.write(page.DATA)
        self.FILE_HEADER.N_PAGES = max(self.FILE_HEADER.N_PAGES, page.PAGE_ID + 1)

    def allocate_page(self) -> int:
        page_id = self.FILE_HEADER.N_PAGES
        self.FILE_HEADER.N_PAGES += 1
        self.write_file_header()
        return page_id

    def create_posting_page(self, posting: PostingEntry) -> int:
        page_id = self.allocate_page()
        posting_page = PostingPage(page_id, [posting], -1)
        page = posting_page.to_page(self.FILE_HEADER.PAGE_SIZE)
        self.write_page(page)
        return page_id

    def append_to_posting_list(self, start_page_id: int, posting: PostingEntry) -> None:
        page_id = start_page_id
        while True:
            page = self.read_page(page_id)
            posting_page = PostingPage.from_page(page)

            if len(posting_page.POSTING_LIST) < self.MAX_ENTRIES:
                posting_page.POSTING_LIST.append(posting)
                self.write_page(posting_page.to_page(self.FILE_HEADER.PAGE_SIZE))
                return

            if posting_page.NEXT_PAGE == -1:
                new_page_id = self.allocate_page()
                new_page = PostingPage(new_page_id, [posting], -1)
                self.write_page(new_page.to_page(self.FILE_HEADER.PAGE_SIZE))

                posting_page.NEXT_PAGE = new_page_id
                self.write_page(posting_page.to_page(self.FILE_HEADER.PAGE_SIZE))
                return

            page_id = posting_page.NEXT_PAGE

    def upsert_posting(self, start_page_id: int, posting: PostingEntry) -> None:
        page_id = start_page_id
        while True:
            page = self.read_page(page_id)
            posting_page = PostingPage.from_page(page)

            for i, entry in enumerate(posting_page.POSTING_LIST):
                if entry.DOC_ID == posting.DOC_ID:
                    posting_page.POSTING_LIST[i] = PostingEntry(
                        posting.DOC_ID, entry.TF + posting.TF
                    )
                    self.write_page(posting_page.to_page(self.FILE_HEADER.PAGE_SIZE))
                    return

            if posting_page.NEXT_PAGE == -1:
                break
            page_id = posting_page.NEXT_PAGE

        self.append_to_posting_list(start_page_id, posting)

    def read_posting_list(self, start_page_id: int) -> list[PostingEntry]:
        result = []
        page_id = start_page_id
        while page_id != -1:
            page = self.read_page(page_id)
            posting_page = PostingPage.from_page(page)
            result.extend(posting_page.POSTING_LIST)
            page_id = posting_page.NEXT_PAGE
        return result