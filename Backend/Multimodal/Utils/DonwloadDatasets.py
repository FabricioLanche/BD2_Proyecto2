import os
import zipfile
import requests
import pandas as pd
from kagglehub import kagglehub, KaggleDatasetAdapter

TEXT_COLUMNS = [
    "gender", "masterCategory", "subCategory", "articleType",
    "baseColour", "season", "year", "usage", "productDisplayName",
]


IMAGES_ZIP_URL = (
    "https://github.com/FabricioLanche/BD2_Proyecto2/"
    "releases/download/v1.0/images.zip"
)


def _download_and_extract_images(data_dir: str) -> None:
    images_dir = os.path.join(data_dir, "images")
    if os.path.isdir(images_dir) and any(
        f.endswith(".jpg") for f in os.listdir(images_dir)
    ):
        print(f"Imagenes locales ya presentes en {images_dir}")
        return

    zip_path = os.path.join(data_dir, "images.zip")

    if not os.path.exists(zip_path):
        print(f"Descargando {IMAGES_ZIP_URL} ...")
        resp = requests.get(IMAGES_ZIP_URL, stream=True, timeout=120)
        resp.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Descarga completada")

    print("Extrayendo imagenes ...")
    os.makedirs(images_dir, exist_ok=True)

    with zipfile.ZipFile(zip_path) as z:
        for member in z.namelist():
            if not member.endswith(".jpg"):
                continue
            rel_path = os.path.relpath(member, "images")
            if rel_path.startswith(".."):
                rel_path = os.path.basename(member)
            target = os.path.join(images_dir, rel_path)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(member) as src, open(target, "wb") as dst:
                dst.write(src.read())
    os.remove(zip_path)
    print(f"Imagenes extraidas en {images_dir} ({len(os.listdir(images_dir))} archivos)")


def repair_line(fields):
    if len(fields) > 10:
        return fields[:9] + [",".join(fields[9:])]
    return fields


def _is_undefined(val) -> bool:
    if pd.isna(val):
        return True
    s = str(val).strip().lower()
    return s in ("", "undefined", "none", "null", "nan")


def download_datasets():

    data_dir = os.path.join(os.path.dirname(__file__), "..", "Data")
    os.makedirs(data_dir, exist_ok=True)

    _download_and_extract_images(data_dir)

    styles_path = os.path.join(data_dir, "styles.csv")
    images_path = os.path.join(data_dir, "images.csv")

    if not os.path.exists(styles_path) or not os.path.exists(images_path):
        print("Descargando datasets desde Kaggle...")
        styles_df = kagglehub.load_dataset(
            KaggleDatasetAdapter.PANDAS,
            "paramaggarwal/fashion-product-images-dataset",
            "fashion-dataset/styles.csv",
            pandas_kwargs={
                "engine": "python",
                "on_bad_lines": repair_line,
            },
        )
        images_df = kagglehub.load_dataset(
            KaggleDatasetAdapter.PANDAS,
            "paramaggarwal/fashion-product-images-dataset",
            "fashion-dataset/images.csv",
        )
        print(f"Descargados {len(styles_df)} productos y {len(images_df)} imagenes")
    else:
        print("Cargando CSVs existentes...")
        styles_df = pd.read_csv(styles_path)
        images_df = pd.read_csv(images_path)

    # ── Limpiar images.csv ──────────────────────────────────

    n_before = len(images_df)
    images_df = images_df[~images_df["link"].apply(_is_undefined)].copy()
    n_removed = n_before - len(images_df)
    print(f"images.csv: {n_removed} filas con link invalido eliminadas")

    def _extract_id(fname):
        base = os.path.splitext(os.path.basename(str(fname)))[0]
        return int(base)

    def _make_local_path(fname):
        base = os.path.basename(str(fname).strip())
        return "Backend/Multimodal/Data/images/" + base

    images_df = images_df.assign(
        id=images_df["filename"].apply(_extract_id),
        filename=images_df["filename"].apply(_make_local_path),
    )
    images_df = images_df[["id", "filename", "link"]]

    images_df.to_csv(images_path, index=False)
    print(f"images.csv guardado con {len(images_df)} filas (columnas: id, filename, link)")

    # ── Limpiar styles.csv ──────────────────────────────────

    valid_ids = set(images_df["id"])

    n_before = len(styles_df)
    styles_df = styles_df[styles_df["id"].isin(valid_ids)].copy()
    print(f"styles.csv: {n_before - len(styles_df)} filas sin imagen valida eliminadas")

    def _concat_text(row):
        parts = [str(row.get(col, "")) for col in TEXT_COLUMNS]
        return "|".join(parts)

    styles_df["texto"] = styles_df.apply(_concat_text, axis=1)
    styles_df = styles_df[["id", "texto"]]
    styles_df.to_csv(styles_path, index=False)
    print(f"styles.csv guardado con {len(styles_df)} filas (columnas: id, texto)")

    print("Limpieza de CSVs completada.")


if __name__ == "__main__":
    download_datasets()
