#!/bin/bash
set -e

DATASET_SIZE="${DATASET_SIZE:-44446}"
DATA_DIR="/app/Backend/Multimodal/Data/${DATASET_SIZE}"

if [ ! -d "$DATA_DIR" ] || [ -z "$(ls -A "$DATA_DIR" 2>/dev/null)" ]; then
    echo "========================================"
    echo " Data directory '$DATA_DIR' not found."
    echo " Running offline pipeline for"
    echo " $DATASET_SIZE documents..."
    echo "========================================"
    python -m Backend.Multimodal.Offline.Orquestador2 \
        --dataset-size "$DATASET_SIZE"
    echo "========================================"
    echo " Offline pipeline completed."
    echo "========================================"
else
    echo "Data directory '$DATA_DIR' exists, skipping offline pipeline."
fi

echo "Initializing database from CSV dump if needed..."
python /init_db.py

exec "$@"
