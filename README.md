# BD2 Proyecto 2 — Motor de Búsqueda Multimodal

Sistema de búsqueda de productos de moda usando **imágenes** y **texto**, con un motor propio basado en índices invertidos y codebooks visuales/textuales.

---

## Requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo
- Windows (o cualquier SO con Docker)
- Al menos 8 GB de RAM libre

---

## Levantar el sistema

```bash
# Desde la raíz del proyecto
docker compose build
docker compose up -d
```

Esto levanta tres servicios:

| Servicio    | Puerto | Descripción                                     |
|-------------|--------|-------------------------------------------------|
| **db**      | `5432` | PostgreSQL 16 + pgvector                        |
| **backend** | `8000` | FastAPI — motor de búsqueda multimodal           |
| **frontend**| `5173` | Vite + React — interfaz web                     |

Para verificar que todo esta listo:

```bash
docker ps
# Deberías ver 3 contenedores con estado "Up" y "Healthy"
```

---

## Acceder a la aplicación

- **Frontend:** [http://localhost:5173](http://localhost:5173)
- **Backend (API):** [http://localhost:8000](http://localhost:8000)
- **Health check:** [http://localhost:8000/](http://localhost:8000/)

---

## Cómo usar

### 1. Búsqueda Visual

En la pestaña **"Shop by photo"**:

1. Arrastra una foto de producto o haz clic para seleccionar una
2. Ajusta el número de resultados deseado (10–50)
3. Haz clic en **"Search looks"**
4. Los resultados se muestran con un porcentaje de similitud
5. Haz clic en cualquier producto para ver detalles

### 2. Búsqueda Multimodal (Texto + Imagen)

En la pestaña **"Find your look"**:

1. Sube una foto (opcional)
2. Escribe una descripción textual (ej. *"oversized cream linen blazer"*)
3. Ajusta el peso de búsqueda con el slider: mueve hacia **texto** o **imagen** según quieras priorizar
4. Haz clic en **"Search looks"**
5. Los resultados combinan ambas modalidades según el peso elegido

## Notas importantes

- **Dataset size:** Por defecto se usa `DATASET_SIZE=40000`. Si cambias este valor, el entrypoint podría ejecutar el pipeline offline la primera vez (depende del valor brindado, actualmente soporta para: 1000, 10000, 20000, 30000 y 40000).
- **Datos de imágenes:** Las imágenes de los productos no están incluidas en el repositorio. El sistema usa URLs externas para mostrarlas en los resultados.
- **Sin conexión a internet:** El frontend necesita carga inicial de assets vía CDN (Vite, Google Fonts, Material Symbols).

---

## Estructura del proyecto

```
BD2_Proyecto2/
├── docker-compose.yml          # Orquestación de servicios
├── Backend/
│   ├── API/                    # FastAPI (endpoints REST)
│   │   ├── main.py             # Punto de entrada
│   │   ├── controller/         # Rutas (/api/visual, /api/multimodal, /api/details)
│   │   ├── service/            # Lógica de búsqueda
│   │   ├── entrypoint.sh       # Script de inicio del contenedor
│   │   └── init_db.py          # Inicialización de BD
│   └── Multimodal/
│       ├── Online/             # Motor de búsqueda en línea
│       ├── Offline/            # Pipeline de indexación offline
│       ├── Utils/              # B+Tree, Hash Extensible, Buffer Manager
│       └── Data/               # Codebooks, índices y dumps CSV
├── Fronted/
│   ├── src/
│   │   ├── pages/              # VisualSearch, RecommendationEngine
│   │   ├── components/         # ProductCard, UploadZone, FusionSlider
│   │   └── services/api.ts     # Llamadas al backend
│   └── Dockerfile
└── README.md
```