# BD2 Proyecto 2 — Motor de Búsqueda Multimodal

Sistema de búsqueda de productos de moda usando **imágenes** y **texto**, con un motor propio basado en índices invertidos y codebooks visuales/textuales. Implementa dos modos de búsqueda: **Postgres (pgvector)** y **SPIMI** (índice propio).

---

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo
- Windows (o cualquier SO con Docker)
- Al menos 8 GB de RAM libre

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/FabricioLanche/BD2_Proyecto2.git
cd BD2_Proyecto2

# 2. Extraer datos pre-generados (codebooks, índices, dumps)
#    Omite el pipeline offline que tarda ~45 min.
cd Backend/Multimodal/Data
unzip data_gen.zip
cd ../../..

# 3. Iniciar servicios
docker compose up --build -d

# 4. Verificar que los 3 contenedores estén "Up" y "Healthy"
docker ps
```

| Servicio    | Puerto | Descripción                               |
|-------------|--------|-------------------------------------------|
| **db**      | `5432` | PostgreSQL 16 + pgvector                  |
| **backend** | `8000` | FastAPI — motor de búsqueda multimodal     |
| **frontend**| `5173` | Vite + React — interfaz web               |

---

## Acceder

- **Frontend:** [http://localhost:5173](http://localhost:5173)
- **API:** [http://localhost:8000](http://localhost:8000)
- **Health:** [http://localhost:8000/](http://localhost:8000/)

---

## Cómo usar

### Búsqueda Visual
Pestaña **"Shop by photo"** — sube una foto, ajusta resultados (10–50) y haz clic en **"Search looks"**. Los resultados muestran % de similitud.

### Búsqueda Multimodal (Texto + Imagen)
Pestaña **"Find your look"** — sube una foto (opcional), escribe una descripción y usa el slider para priorizar texto o imagen.

### Toggle SPIMI / Postgres
En cualquier búsqueda puedes cambiar entre **Postgres** (pgvector, más rápido) y **SPIMI** (índice invertido propio) usando el selector en la parte superior.

### Métricas
Tras cada búsqueda se muestran: tiempo de consulta, páginas accedidas, hits en caché, lecturas/escrituras de disco, y tiempo de I/O.

---

## Dataset

| Variable         |  Opciones                |
|------------------|-------------------------|
| `DATASET_SIZE`   | 10000, 20000, 30000, 40000 |

Los datos pre-generados incluyen índices SPIMI (B+Tree + heap), codebooks visuales/textuales, y el dump CSV con descriptores. Si el directorio `Backend/Multimodal/Data/{size}` no existe al arrancar, el entrypoint ejecuta el pipeline offline automáticamente. Las imágenes se cargan por URL externa.

---

## Estructura

```
BD2_Proyecto2/
├── docker-compose.yml
├── Backend/
│   ├── API/              # FastAPI — endpoints REST
│   ├── Multimodal/
│   │   ├── Online/       # Motores Postgres + SPIMI
│   │   ├── Offline/      # Pipeline de indexación
│   │   ├── Utils/        # B+Tree, Hash Extensible, Buffer Manager
│   │   └── Data/         # Codebooks, índices, CSVs, data_gen.zip
│   └── ...
├── Frontend/
│   ├── src/pages/        # VisualSearch, RecommendationEngine
│   ├── src/components/   # ProductCard, UploadZone, FusionSlider
│   ├── src/services/     # api.ts — llamadas al backend
│   └── Dockerfile
└── README.md
```
