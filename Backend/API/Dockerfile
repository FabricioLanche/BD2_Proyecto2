FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY Backend/API/requirements.txt Backend/API/requirements.txt
COPY Backend/Multimodal/requirements.txt Backend/Multimodal/requirements.txt
RUN pip install --no-cache-dir \
    -r Backend/API/requirements.txt \
    -r Backend/Multimodal/requirements.txt

COPY Backend/ Backend/

COPY Backend/API/entrypoint.sh  /entrypoint.sh
COPY Backend/API/init_db.py    /init_db.py
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "Backend.API.main:app", "--host", "0.0.0.0", "--port", "8000"]
