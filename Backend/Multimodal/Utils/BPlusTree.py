from .BufferManager import BufferManager
from .HeapFile import HeapFile, PostingEntry
from dataclasses import dataclass
import struct
import os

@dataclass
class Page:
    PAGE_ID: tuple[int, int] #(file_id, page_number)
    DATA: bytearray

@dataclass
class PageHeader:
    IS_LEAF: bool
    N_ENTRIES: int
    PARENT_ID: int = -1
    NEXT_LEAF: int = -1
    FIRST_PTR: int = -1
PAGE_HEADER_FORMAT = "<?4i"
PAGE_HEADER_SIZE = struct.calcsize(PAGE_HEADER_FORMAT)

@dataclass
class NodeEntry:
    KEY: int
    PTR: int
NODE_ENTRY_FORMAT = "<2i"
NODE_ENTRY_SIZE = struct.calcsize(NODE_ENTRY_FORMAT)

class NodePage:
    def __init__(self, page_id: tuple[int, int], entries: list[NodeEntry], page_header: PageHeader):
        self.PAGE_ID = page_id
        self.PAGE_HEADER = page_header
        self.ENTRIES = entries

    @property
    def FIRST_PTR(self):
        return self.PAGE_HEADER.FIRST_PTR

    @FIRST_PTR.setter
    def FIRST_PTR(self, value):
        self.PAGE_HEADER.FIRST_PTR = value

    @staticmethod
    def from_page(page: Page) -> "NodePage":
        data = page.DATA
        is_leaf, n_entries, parent_id, next_leaf, first_ptr = struct.unpack(
            PAGE_HEADER_FORMAT, data[:PAGE_HEADER_SIZE]
        )
        page_header = PageHeader(
            IS_LEAF=bool(is_leaf), N_ENTRIES=n_entries,
            PARENT_ID=parent_id, NEXT_LEAF=next_leaf,
            FIRST_PTR=first_ptr
        )
        entries = []
        offset = PAGE_HEADER_SIZE
        for _ in range(n_entries):
            key, ptr = struct.unpack(NODE_ENTRY_FORMAT, data[offset:offset+NODE_ENTRY_SIZE])
            entries.append(NodeEntry(key, ptr))
            offset += NODE_ENTRY_SIZE
        return NodePage(page.PAGE_ID, entries, page_header)

    def to_page(self, page_size: int) -> Page:
        data = bytearray(page_size)
        struct.pack_into(PAGE_HEADER_FORMAT, data, 0,
                         self.PAGE_HEADER.IS_LEAF,
                         self.PAGE_HEADER.N_ENTRIES,
                         self.PAGE_HEADER.PARENT_ID,
                         self.PAGE_HEADER.NEXT_LEAF,
                         self.PAGE_HEADER.FIRST_PTR)
        offset = PAGE_HEADER_SIZE
        for entry in self.ENTRIES:
            struct.pack_into(NODE_ENTRY_FORMAT, data, offset, entry.KEY, entry.PTR)
            offset += NODE_ENTRY_SIZE
        return Page(self.PAGE_ID, data)

@dataclass
class FileHeader:
    PAGE_SIZE: int = 8192
    ROOT_PAGE: int = -1
    N_PAGES: int = 0
FILE_HEADER_FORMAT = "<3i"
FILE_HEADER_SIZE = struct.calcsize(FILE_HEADER_FORMAT)

class BPlusTreeFile:
    # FILE_HEADER = FileHeader
    # FILE_PATH = os.path.join(FILE_DIR, "BPlusTree.bin")
    # MAX_ENTRIES = (PAGE_SIZE - PAGE_HEADER_SIZE) // NODE_ENTRY_SIZE

    def __init__(self, filename, file_id: int, buffer_manager: BufferManager):
        self.FILE_ID = file_id
        self.FILE_PATH = filename
        self.BUFFER_MANAGER = buffer_manager
        try:
            self.read_file_header()
        except (FileNotFoundError, struct.error):
            self.FILE_HEADER = FileHeader()
            os.makedirs(os.path.dirname(self.FILE_PATH), exist_ok=True)
            open(self.FILE_PATH, "ab").close()
            self.write_file_header()
        finally:
            self.MAX_ENTRIES = (self.FILE_HEADER.PAGE_SIZE - PAGE_HEADER_SIZE) // NODE_ENTRY_SIZE
            self.BUFFER_MANAGER.register_file(
                file_id, filename,
                self.FILE_HEADER.PAGE_SIZE,
                FILE_HEADER_SIZE,
            )

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
                self.FILE_HEADER.ROOT_PAGE,
                self.FILE_HEADER.N_PAGES
            ))

    def read_page(self, page_id: tuple[int, int]) -> Page:
        data = self.BUFFER_MANAGER.read_page(page_id)
        return Page(page_id, data)

    def write_page(self, page: Page):
        if len(page.DATA) != self.FILE_HEADER.PAGE_SIZE:
            raise ValueError("Tamaño de página incorrecto")
        self.BUFFER_MANAGER.write_page(page.PAGE_ID, page.DATA)
        _, page_number = page.PAGE_ID
        self.FILE_HEADER.N_PAGES = max(self.FILE_HEADER.N_PAGES, page_number + 1)

    def allocate_page(self) -> tuple[int, int]:
        page_number = self.FILE_HEADER.N_PAGES
        self.FILE_HEADER.N_PAGES += 1
        self.write_file_header()
        return (self.FILE_ID, page_number)

class BPlusTree:
    def __init__(self, btree_filename, heap_filename,
                 btree_file_id: int, heap_file_id: int,
                 buffer_manager: BufferManager):
        self.BUFFER_MANAGER = buffer_manager
        self.HEAP_FILE = HeapFile(heap_filename, file_id=heap_file_id,
                                  buffer_manager=buffer_manager)
        self.BPLUS_TREE_FILE = BPlusTreeFile(btree_filename, file_id=btree_file_id,
                                             buffer_manager=buffer_manager)
        if self.BPLUS_TREE_FILE.FILE_HEADER.ROOT_PAGE == -1:
            root = self._create_node(is_leaf=True)
            self._save_node(root)
            self.BPLUS_TREE_FILE.FILE_HEADER.ROOT_PAGE = root.PAGE_ID[1]
            self.BPLUS_TREE_FILE.write_file_header()

    def _load_node(self, page_id: int | tuple[int, int]) -> NodePage:
        if isinstance(page_id, int):
            page_id = (self.BPLUS_TREE_FILE.FILE_ID, page_id)
        page = self.BPLUS_TREE_FILE.read_page(page_id)
        return NodePage.from_page(page)

    def _save_node(self, node: NodePage):
        page = node.to_page(self.BPLUS_TREE_FILE.FILE_HEADER.PAGE_SIZE)
        self.BPLUS_TREE_FILE.write_page(page)

    def _create_node(self, is_leaf: bool) -> NodePage:
        page_id = self.BPLUS_TREE_FILE.allocate_page()
        header = PageHeader(IS_LEAF=is_leaf, N_ENTRIES=0, PARENT_ID=-1, NEXT_LEAF=-1, FIRST_PTR=-1)
        return NodePage(page_id=page_id, entries=[], page_header=header)

    def _find_leaf(self, key: int) -> NodePage:
        leaf_id = self.BPLUS_TREE_FILE.FILE_HEADER.ROOT_PAGE
        node = self._load_node(leaf_id)
        while not node.PAGE_HEADER.IS_LEAF:
            if key < node.ENTRIES[0].KEY:
                leaf_id = node.FIRST_PTR
            elif key >= node.ENTRIES[-1].KEY:
                leaf_id = node.ENTRIES[-1].PTR
            else:
                for i in range(len(node.ENTRIES) - 1):
                    if node.ENTRIES[i].KEY <= key < node.ENTRIES[i + 1].KEY:
                        leaf_id = node.ENTRIES[i].PTR
                        break
            node = self._load_node(leaf_id)
        return node

    def _insert_into_leaf(self, leaf: NodePage, entry: NodeEntry):
        for i, e in enumerate(leaf.ENTRIES):
            if entry.KEY < e.KEY:
                leaf.ENTRIES.insert(i, entry)
                break
        else:
            leaf.ENTRIES.append(entry)
        leaf.PAGE_HEADER.N_ENTRIES = len(leaf.ENTRIES)
        if leaf.PAGE_HEADER.N_ENTRIES > self.BPLUS_TREE_FILE.MAX_ENTRIES:
            self._split_leaf(leaf)
        else:
            self._save_node(leaf)

    def _split_leaf(self, leaf: NodePage):
        new_leaf = self._create_node(is_leaf=True)
        mid = len(leaf.ENTRIES) // 2
        new_leaf.ENTRIES = leaf.ENTRIES[mid:]
        leaf.ENTRIES = leaf.ENTRIES[:mid]
        leaf.PAGE_HEADER.N_ENTRIES = len(leaf.ENTRIES)
        new_leaf.PAGE_HEADER.N_ENTRIES = len(new_leaf.ENTRIES)
        new_leaf.PAGE_HEADER.NEXT_LEAF = leaf.PAGE_HEADER.NEXT_LEAF
        leaf.PAGE_HEADER.NEXT_LEAF = new_leaf.PAGE_ID[1]
        self._save_node(leaf)
        self._save_node(new_leaf)
        split_key = new_leaf.ENTRIES[0].KEY
        self._insert_into_parent(leaf, split_key, new_leaf)

    def _split_internal(self, node: NodePage):
        mid = len(node.ENTRIES) // 2
        split_key = node.ENTRIES[mid].KEY
        new_node = self._create_node(is_leaf=False)
        new_node.ENTRIES = node.ENTRIES[mid + 1:]
        new_node.FIRST_PTR = node.ENTRIES[mid].PTR
        node.ENTRIES = node.ENTRIES[:mid]
        node.PAGE_HEADER.N_ENTRIES = len(node.ENTRIES)
        new_node.PAGE_HEADER.N_ENTRIES = len(new_node.ENTRIES)
        child = self._load_node(new_node.FIRST_PTR)
        child.PAGE_HEADER.PARENT_ID = new_node.PAGE_ID[1]
        self._save_node(child)
        for entry in new_node.ENTRIES:
            child = self._load_node(entry.PTR)
            child.PAGE_HEADER.PARENT_ID = new_node.PAGE_ID[1]
            self._save_node(child)
        self._save_node(node)
        self._save_node(new_node)
        self._insert_into_parent(node, split_key, new_node)

    def _insert_into_parent(self, left: NodePage, split_key: int, right: NodePage):
        if left.PAGE_HEADER.PARENT_ID == -1:
            new_root = self._create_node(is_leaf=False)
            new_root.FIRST_PTR = left.PAGE_ID[1]
            new_root.ENTRIES = [NodeEntry(split_key, right.PAGE_ID[1])]
            new_root.PAGE_HEADER.N_ENTRIES = 1
            left.PAGE_HEADER.PARENT_ID = new_root.PAGE_ID[1]
            right.PAGE_HEADER.PARENT_ID = new_root.PAGE_ID[1]
            self._save_node(left)
            self._save_node(right)
            self._save_node(new_root)
            self.BPLUS_TREE_FILE.FILE_HEADER.ROOT_PAGE = new_root.PAGE_ID[1]
            self.BPLUS_TREE_FILE.write_file_header()
            return
        parent = self._load_node(left.PAGE_HEADER.PARENT_ID)
        for i, entry in enumerate(parent.ENTRIES):
            if split_key < entry.KEY:
                parent.ENTRIES.insert(i, NodeEntry(split_key, right.PAGE_ID[1]))
                break
        else:
            parent.ENTRIES.append(NodeEntry(split_key, right.PAGE_ID[1]))
        parent.PAGE_HEADER.N_ENTRIES = len(parent.ENTRIES)
        right.PAGE_HEADER.PARENT_ID = parent.PAGE_ID[1]
        self._save_node(right)
        if parent.PAGE_HEADER.N_ENTRIES > self.BPLUS_TREE_FILE.MAX_ENTRIES:
            self._split_internal(parent)
        else:
            self._save_node(parent)

    def insert_posting(
        self,
        codeword_id: int,
        posting: tuple[int, int],
        tail: tuple[int, int] | None = None,
    ) -> tuple[int, int]:
        if tail is not None:
            return self.HEAP_FILE.append_to_posting_list(tail, PostingEntry(posting[0], posting[1]))
        leaf = self._find_leaf(codeword_id)
        for entry in leaf.ENTRIES:
            if entry.KEY == codeword_id:
                start = (self.HEAP_FILE.FILE_ID, entry.PTR)
                return self.HEAP_FILE.append_to_posting_list(start, PostingEntry(posting[0], posting[1]))
        heap_page_id = self.HEAP_FILE.create_posting_page(
            PostingEntry(posting[0], posting[1])
        )
        self._insert_into_leaf(leaf, NodeEntry(codeword_id, heap_page_id[1]))
        return heap_page_id

    def scan(self):
        leaf_id = self.BPLUS_TREE_FILE.FILE_HEADER.ROOT_PAGE
        node = self._load_node(leaf_id)
        while not node.PAGE_HEADER.IS_LEAF:
            leaf_id = node.FIRST_PTR
            node = self._load_node(leaf_id)
        while True:
            for entry in node.ENTRIES:
                posting_list = self.HEAP_FILE.read_posting_list(
                    (self.HEAP_FILE.FILE_ID, entry.PTR)
                )
                yield (entry.KEY, posting_list)
            if node.PAGE_HEADER.NEXT_LEAF == -1:
                break
            node = self._load_node(node.PAGE_HEADER.NEXT_LEAF)

    def get_posting_list(self, key: int) -> list[PostingEntry] | None:
        leaf = self._find_leaf(key)
        for entry in leaf.ENTRIES:
            if entry.KEY == key:
                return self.HEAP_FILE.read_posting_list(
                    (self.HEAP_FILE.FILE_ID, entry.PTR)
                )
        return None

    def upsert_posting(self, codeword_id: int, posting: tuple[int, int]) -> None:
        leaf = self._find_leaf(codeword_id)
        for entry in leaf.ENTRIES:
            if entry.KEY == codeword_id:
                self.HEAP_FILE.upsert_posting(
                    (self.HEAP_FILE.FILE_ID, entry.PTR), PostingEntry(posting[0], posting[1])
                )
                return
        heap_page_id = self.HEAP_FILE.create_posting_page(
            PostingEntry(posting[0], posting[1])
        )
        self._insert_into_leaf(leaf, NodeEntry(codeword_id, heap_page_id[1]))