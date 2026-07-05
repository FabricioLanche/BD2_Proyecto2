"""
Analiza estadísticas BOW del dataset de texto (styles.csv) para distintos
tamaños de muestra.  Sirve para elegir la k del text_codebook.

Uso:
    python -m Backend.Multimodal.Utils.AnalyzeBowStats
"""

import csv
import re
from collections import Counter
from pathlib import Path
from typing import List, Set

import matplotlib.pyplot as plt
import numpy as np
from nltk.stem.snowball import SnowballStemmer

TEXT_COLUMNS = [
    "gender", "masterCategory", "subCategory", "articleType",
    "baseColour", "season", "year", "usage", "productDisplayName",
]
SAMPLE_SIZES = [10_000, 20_000, 30_000, 44_446]

DATA_DIR = Path(__file__).resolve().parent.parent / "Data"
OUT_DIR = Path(__file__).resolve().parent.parent / "Data"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_stopwords() -> Set[str]:
    path = DATA_DIR / "stopwords.txt"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return {line.strip().lower() for line in f if line.strip()}
    except FileNotFoundError:
        print(f"Advertencia: no se encontró {path}, usando vacías")
        return set()


def preprocess(text: str, stop_words: Set[str], stemmer: SnowballStemmer) -> List[str]:
    text = text.lower()
    tokens = re.findall(r"\b[a-z0-9]+\b", text)
    tokens = [t for t in tokens if t not in stop_words]
    tokens = [stemmer.stem(t) for t in tokens]
    return tokens


def compute_coverage(counter: Counter, top_k: int) -> float:
    total = sum(counter.values())
    if total == 0:
        return 0.0
    top_total = sum(freq for _, freq in counter.most_common(top_k))
    return top_total / total


def freq_histogram_buckets(counter: Counter) -> dict:
    buckets = {"1": 0, "2-5": 0, "6-20": 0, "21-100": 0, "101-1000": 0, "1001+": 0}
    for freq in counter.values():
        if freq == 1:
            buckets["1"] += 1
        elif freq <= 5:
            buckets["2-5"] += 1
        elif freq <= 20:
            buckets["6-20"] += 1
        elif freq <= 100:
            buckets["21-100"] += 1
        elif freq <= 1000:
            buckets["101-1000"] += 1
        else:
            buckets["1001+"] += 1
    return buckets


def analyze(dataset_size: int, stop_words: Set[str], stemmer: SnowballStemmer) -> dict:
    styles_path = DATA_DIR / "styles.csv"
    if not styles_path.exists():
        raise FileNotFoundError(f"No se encontró {styles_path}")

    counter: Counter = Counter()
    docs = 0
    with open(styles_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if docs >= dataset_size:
                break

            parts: List[str] = []
            for col in TEXT_COLUMNS:
                val = row.get(col, "")
                parts.append(val if val else "")
            texto = "|".join(parts)

            tokens = preprocess(texto, stop_words, stemmer)
            counter.update(tokens)
            docs += 1

    total_terms = len(counter)
    total_freq = sum(counter.values())
    hapax = sum(1 for f in counter.values() if f == 1)

    coverage_points = [10, 50, 100, 200, 500, 1000, 2000, 5000]
    coverages = {str(k): round(compute_coverage(counter, k) * 100, 2) for k in coverage_points}

    hist = freq_histogram_buckets(counter)

    return {
        "docs": docs,
        "vocab_size": total_terms,
        "total_occurrences": total_freq,
        "hapax": hapax,
        "hapax_pct": round(hapax / total_terms * 100, 2) if total_terms else 0,
        "coverage_pct": coverages,
        "histogram": hist,
    }


def plot_coverage(stats: dict) -> None:
    n = stats["docs"]
    k_vals = [int(k) for k in stats["coverage_pct"].keys()]
    cov_vals = [stats["coverage_pct"][k] for k in stats["coverage_pct"].keys()]

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(k_vals, cov_vals, marker="o", color="#2ecc71",
            linewidth=2, markersize=8, zorder=3)
    ax.set_xlabel("top-k", fontsize=12)
    ax.set_ylabel("Cobertura acumulada (%)", fontsize=12)
    ax.set_title(f"Cobertura acumulada del vocabulario (n={n:,})", fontsize=13)
    ax.set_xscale("log")
    ax.set_xticks(k_vals)
    ax.set_xticklabels([str(k) for k in k_vals])
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)

    for k, v in zip(k_vals, cov_vals):
        ax.annotate(f"{v}%",
                    (k, v),
                    textcoords="offset points",
                    xytext=(0, 12),
                    ha="center",
                    fontsize=9,
                    fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.3",
                              facecolor="white",
                              edgecolor="#2ecc71",
                              alpha=0.9))

    plt.tight_layout()
    path = OUT_DIR / f"bow_coverage_{n}.png"
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Gráfico guardado: {path}")


def print_report(stats: dict) -> None:
    sep = "─" * 62
    print(f"\n{'='*62}")
    print(f"  Documentos analizados: {stats['docs']:>8,}")
    print(sep)
    print(f"  Vocabulario (términos únicos):      {stats['vocab_size']:>10,}")
    print(f"  Ocurrencias totales (sum freq):      {stats['total_occurrences']:>10,}")
    print(f"  Hapax (freq=1):                      {stats['hapax']:>8,}  ({stats['hapax_pct']}%)")
    print(sep)
    print(f"  Cobertura acumulada (top-k):")
    for k_str, pct in stats['coverage_pct'].items():
        print(f"    top {k_str:>5}: {pct:>6.2f}%")
    print(sep)

    plot_coverage(stats)


def main() -> None:
    stop_words = load_stopwords()
    stemmer = SnowballStemmer("english")
    print(f"Stopwords cargadas: {len(stop_words)}")
    print(f"Muestras a analizar: {SAMPLE_SIZES}")

    for size in SAMPLE_SIZES:
        print(f"\n{'#'*62}")
        print(f"  ANALIZANDO TAMAÑO: {size:,} documentos")
        print(f"{'#'*62}")
        stats = analyze(size, stop_words, stemmer)
        print_report(stats)

    print("\nAnálisis completado. Revisa los PNG en Data/ para las curvas de cobertura.")


if __name__ == "__main__":
    main()
