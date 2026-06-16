import numpy as np

def generate_image_histograms(
    features: list[tuple[int, np.ndarray]],
    codebook: list[np.ndarray],
) -> list[tuple[int, np.ndarray]]:
    k_codewords = len(codebook)

    histograms: dict[int, np.ndarray] = {}

    for image_id, descriptor in features:
        descriptor = np.asarray(descriptor, dtype=np.float32)

        dists = np.linalg.norm(
            np.asarray(codebook) - descriptor,
            axis=1,
        )

        codeword = int(np.argmin(dists))

        if image_id not in histograms:
            histograms[image_id] = np.zeros(
                k_codewords,
                dtype=np.float32,
            )

        histograms[image_id][codeword] += 1

    return list(histograms.items())

def generate_text_histograms(
    features: list[tuple[int, np.ndarray]],
    codebook: list[str],
    vocabulary: np.ndarray,
) -> list[tuple[int, np.ndarray]]:
    vocab_index = {
        word: idx
        for idx, word in enumerate(vocabulary)
    }

    codebook_idx = np.array(
        [vocab_index[word] for word in codebook],
        dtype=int,
    )

    histograms: list[tuple[int, np.ndarray]] = []

    for doc_id, bow in features:
        bow = np.asarray(bow, dtype=np.float32)
        histogram = bow[codebook_idx]
        histograms.append((doc_id, histogram))

    return histograms