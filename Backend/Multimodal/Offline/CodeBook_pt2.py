import numpy as np

def generate_image_histograms(
    features: list[tuple[int, np.ndarray]],
    codebook: list[np.ndarray],
) -> tuple[
    list[np.ndarray],
    list[tuple[int, np.ndarray]],
    list[tuple[int, int]]
]:
    k_codewords = len(codebook)
    codebook_np = np.asarray(codebook)

    histograms: dict[int, np.ndarray] = {}
    spimi_stream: list[tuple[int, int]] = []

    for image_id, descriptor in features:
        descriptor = np.asarray(descriptor, dtype=np.float32)

        dists = np.linalg.norm(
            codebook_np - descriptor,
            axis=1,
        )

        codeword_id = int(np.argmin(dists))

        if image_id not in histograms:
            histograms[image_id] = np.zeros(
                k_codewords,
                dtype=np.float32,
            )

        histograms[image_id][codeword_id] += 1
        spimi_stream.append((image_id, codeword_id))

    histograms = list(histograms.items())
    return codebook, histograms, spimi_stream

def generate_text_histograms(
    features: list[tuple[int, np.ndarray]],
    codebook: list[str],
    vocabulary: np.ndarray,
) -> tuple[
    list[str],
    list[tuple[int, np.ndarray]],
    list[tuple[int, int]]
]:
    vocab_index = {
        word: idx
        for idx, word in enumerate(vocabulary)
    }

    codebook_idx = np.array(
        [vocab_index[word] for word in codebook],
        dtype=int,
    )

    histograms: list[tuple[int, np.ndarray]] = []
    spimi_stream: list[tuple[int, int]] = []

    for doc_id, bow in features:
        bow = np.asarray(bow, dtype=np.float32)
        histogram = bow[codebook_idx]
        histograms.append((doc_id, histogram))

        for codeword_id in codebook_idx:
            spimi_stream.append((doc_id, codeword_id))

    return codebook, histograms, spimi_stream