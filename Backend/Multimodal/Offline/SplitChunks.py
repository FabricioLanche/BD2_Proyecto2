import numpy as np

class MultimodalSplitter:
    def __init__(self, 
                 chunk_size=100, overlap=20, 
                 image_patch_size=(64, 64), image_overlap=(0, 0)):
        """
        Splitter Multimodal con Chunking Recursivo por caracter para texto, overlap y chunk_size medido en caracteres.
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

        self.image_patch_size = image_patch_size
        self.image_overlap = image_overlap
        
        self.separators = ["\n\n", "\n", " ", ""]

    def split(self, data):
        if isinstance(data, str):
            return self._split_text(data)
        elif isinstance(data, np.ndarray):
            return self._split_image(data)
        else:
            raise TypeError("Formato no soportado. Debe ser 'str' o 'np.ndarray'.")


    def _split_text(self, text):
        if not text.strip(): return []
            
        atomic_units = self._recursive_split(text)

        return self._merge_splits(atomic_units)

    def _recursive_split(self, text, sep_index=0):
        """Función recursiva que divide el texto siguiendo los separadores proporcionados cuando uno excede el tamaño del chunk."""

        if len(text) <= self.chunk_size:
            return [text]
            
        if sep_index >= len(self.separators) or self.separators[sep_index] == "":
            return [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size)]
            
        separator = self.separators[sep_index]
        
        splits = text.split(separator)

        final_splits = []
        for s in splits:
            if s.strip() == "": continue
            
            if len(s) <= self.chunk_size:
                final_splits.append(s)
            else:
                final_splits.extend(self._recursive_split(s, sep_index + 1))
                
        return final_splits

    def _merge_splits(self, splits):
        """Ensambla los pedazos atómicos aplicando el algoritmo de ventana deslizante (Overlap)."""
        chunks = []
        current_chunk = []
        current_len = 0
        
        for split in splits:

            split_len = len(split) + (1 if current_chunk else 0) 
            
            if current_len + split_len > self.chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                
                while current_len > self.overlap and len(current_chunk) > 1:
                    removed = current_chunk.pop(0)
                    current_len -= (len(removed) + 1)
                    
            current_chunk.append(split)
            current_len += split_len
            
        if current_chunk:
             chunks.append(" ".join(current_chunk))
             
        return chunks

    def _split_image(self, image_matrix):

        return "split de imagen"

if __name__ == "__main__":
    splitter = MultimodalSplitter(
        chunk_size=100, 
        overlap=20, 
        image_patch_size=(100, 100), 
        image_overlap=(0, 0)
    )

    documento = (
        "Parrafo 1: Proyecto de BII :,).\n\n"
        "Parrafo 2: Splitchunk de prueba para texto e imagen agnostico a a a a a a a a a a a a a a a a a a a a a a a a a a a a aa a a aa a a a a a a a a a a a aa a a a a a a aa a a aa a aaaa a a a a a a a aa a a a  aaaa aa a a a a aa a a aa aaaaaa aa aaa aa a a a aa a aabbb bb b b b bbb bbbbbbbb bb b b a aa a aaaa  a aaaa a  aaaa a a aa aa aa  aaaa a aaa a aaaa  aa aa aaaaa aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.\n\n"
        "Parrafo 3: Generación de chunks segun parametros.\n\n"
        "Parrafo 4: ya no se que mas ponerrrrrr."
    )
    
    texto_chunks = splitter.split(documento)
    for i, c in enumerate(texto_chunks):
         print(f"[{i+1}] ({len(c)} chars)\n{c}\n")