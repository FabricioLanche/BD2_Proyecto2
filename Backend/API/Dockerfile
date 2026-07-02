# Usa una imagen ligera de Python
FROM python:3.11-slim

# Evita que Python escriba archivos .pyc en disco y fuerza a que el output de consola sea inmediato
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala dependencias del sistema necesarias para librerías de procesamiento de imágenes (ej. OpenCV)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copia primero el archivo de requerimientos para aprovechar el caché de Docker
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el código fuente del backend al contenedor
COPY . .

# Expone el puerto en el que corre FastAPI
EXPOSE 8000

# Comando por defecto para iniciar el servidor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]