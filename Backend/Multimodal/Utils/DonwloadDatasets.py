import os
import pandas as pd
from kagglehub import kagglehub, KaggleDatasetAdapter

def repair_line(fields):
    if len(fields) > 10:
        return fields[:9] + [",".join(fields[9:])]
    return fields

def download_datasets():

    data_dir = os.path.join(
        os.path.dirname(__file__),
        "..",
        "Data"
    )
    os.makedirs(data_dir, exist_ok=True)

    styles_path = os.path.join(data_dir, "styles.csv")
    images_path = os.path.join(data_dir, "images.csv")

    if os.path.exists(styles_path) and os.path.exists(images_path):
        return

    styles_df = kagglehub.load_dataset(
        KaggleDatasetAdapter.PANDAS,
        "paramaggarwal/fashion-product-images-dataset",
        "fashion-dataset/styles.csv",
        pandas_kwargs={
            "engine": "python",
            "on_bad_lines": repair_line
        }
    )

    images_df = kagglehub.load_dataset(
        KaggleDatasetAdapter.PANDAS,
        "paramaggarwal/fashion-product-images-dataset",
        "fashion-dataset/images.csv",
    )

    styles_df.to_csv(styles_path, index=False)
    images_df.to_csv(images_path, index=False)