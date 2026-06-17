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
        #extraer dimensiones (RGB 3 canales o Escala de grises 2 canales)
        if len(image_matrix.shape) == 3:
            h, w, channels = image_matrix.shape
        else:
            h, w = image_matrix.shape
            channels = None

        patch_h, patch_w = self.image_patch_size
        overlap_h, overlap_w = self.image_overlap

        #calcular stride para sliding window
        stride_y = patch_h - overlap_h
        stride_x = patch_w - overlap_w

        if stride_y <= 0 or stride_x <= 0:
            raise ValueError("El overlap debe ser estrictamente menor que el tamaño del parche.")

        #si la imagen es más pequeña que el patch, rellenamos hasta el tamaño del patch
        #si sobra espacio despues de stride, calcula espacio sobrante y rellena
        pad_h = 0
        if h < patch_h:
            pad_h = patch_h - h
        elif (h - patch_h) % stride_y != 0:
            pad_h = stride_y - ((h - patch_h) % stride_y)

        pad_w = 0
        if w < patch_w:
            pad_w = patch_w - w
        elif (w - patch_w) % stride_x != 0:
            pad_w = stride_x - ((w - patch_w) % stride_x)

        #relleno con ceros/negro
        #((top, bottom), (left, right), (canales_antes, canales_despues))
        if channels is not None:
            padded_img = np.pad(image_matrix, ((0, pad_h), (0, pad_w), (0, 0)), mode='constant')
        else:
            padded_img = np.pad(image_matrix, ((0, pad_h), (0, pad_w)), mode='constant')

        #sliding window
        patches_with_coords = []
        new_h, new_w = padded_img.shape[:2]

        for y in range(0, new_h - patch_h + 1, stride_y):
            for x in range(0, new_w - patch_w + 1, stride_x):
                #recortar el patch
                patch = padded_img[y:y+patch_h, x:x+patch_w]
                #guardar el parche y su coordenada de origen relativa a la imagen con padding
                patches_with_coords.append((patch, y, x))

        return patches_with_coords


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


    imagen_simulada = np.ones((250, 250, 3))
    print("Dimensiones de la imagen original:", imagen_simulada.shape)
    imagen_chunks = splitter.split(imagen_simulada)
    
    print(f"Se generaron {len(imagen_chunks)} parches visuales.")
    primer_parche, py1, px1 = imagen_chunks[0]
    ultimo_parche, py_last, px_last = imagen_chunks[-1]
    
    print(f"Primer parche:  Coordenada (Y:{py1}, X:{px1}) | Dimensiones: {primer_parche.shape}")
    print(f"Último parche: Coordenada (Y:{py_last}, X:{px_last}) | Dimensiones: {ultimo_parche.shape}")