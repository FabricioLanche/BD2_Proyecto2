const sections = [
  {
    icon: 'image_search',
    title: 'Buscar por foto',
    subtitle: 'Búsqueda visual con imágenes',
    steps: [
      'Sube una foto de moda haciendo clic o arrastrándola al área de carga.',
      'Haz clic en "Search looks" para encontrar productos visualmente similares del catálogo.',
      'Navega los resultados ordenados por porcentaje de similitud. Haz clic en cualquier tarjeta para ver detalles.',
      'Usa el modal de detalle para ver atributos como color, temporada, categoría y más.',
    ],
  },
  {
    icon: 'auto_awesome',
    title: 'Encuentra tu look',
    subtitle: 'Búsqueda multimodal (imagen + texto)',
    steps: [
      'Sube una foto, escribe una descripción, o usa ambas para resultados más precisos.',
      'Ajusta el slider de fusión para controlar el peso de cada entrada.',
      'El slider permite priorizar la imagen (arrastra a la izquierda) o el texto (arrastra a la derecha).',
      'Haz clic en "Search looks" para obtener recomendaciones combinando ambas modalidades.',
    ],
  },
  {
    icon: 'toggle_off',
    title: 'Modo de búsqueda',
    subtitle: 'SPIMI vs Postgres',
    steps: [
      'Usa el selector "Search mode" en la parte superior de cualquier pantalla de búsqueda.',
      'Selecciona Postgres para búsqueda con pgvector (más rápido, usa índices de PostgreSQL).',
      'Selecciona SPIMI para búsqueda con índices invertidos propios (B+Tree, heap).',
      'El cambio es inmediato — no necesitas recargar la página ni re-subir la imagen.',
    ],
  },
  {
    icon: 'touch_app',
    title: 'Interactuar con resultados',
    subtitle: 'Tarjetas, paginación y métricas',
    steps: [
      'Cada tarjeta muestra una miniatura, categoría y porcentaje de coincidencia.',
      'Haz clic en una tarjeta para abrir el modal con todos los metadatos del producto.',
      'Usa los controles de paginación para navegar entre páginas. Las tarjetas se reorganizan según el ancho de pantalla.',
      'Tras cada búsqueda se muestran métricas: tiempo de consulta, páginas accedidas, hits en caché, lecturas/escrituras de disco y tiempos de I/O.',
    ],
  },
]

export default function UserManual() {
  return (
    <div className="flex flex-col gap-stack-lg">
      <header className="flex flex-col gap-1">
        <span className="flex items-center gap-1 font-label-sm text-label-sm text-primary/70 mb-1">
          <span className="material-symbols-outlined text-[13px]">help_outline</span>
          Guía de usuario
        </span>
        <h1 className="font-serif text-display-lg text-on-surface">Mini manual de usuario</h1>
        <p className="font-body-lg text-body-lg text-on-surface-variant/70">
          Aprende a usar Veür para buscar y descubrir prendas de moda.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-stack-md">
        {sections.map((section) => (
          <div
            key={section.title}
            className="bg-surface-container-lowest border border-outline-variant/60 rounded-2xl p-stack-lg flex flex-col gap-stack-md"
          >
            <div className="flex items-center gap-stack-sm">
              <div className="w-9 h-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                <span className="material-symbols-outlined text-[20px]">{section.icon}</span>
              </div>
              <div>
                <h2 className="font-headline-sm text-headline-sm text-on-surface">{section.title}</h2>
                <p className="font-label-sm text-label-sm text-on-surface-variant/60">{section.subtitle}</p>
              </div>
            </div>

            <ol className="flex flex-col gap-stack-md">
              {section.steps.map((step, i) => (
                <li key={i} className="flex gap-stack-sm">
                  <span className="mt-0.5 w-5 h-5 rounded-full bg-primary/10 text-primary font-code text-xs flex items-center justify-center shrink-0 font-semibold">
                    {i + 1}
                  </span>
                  <span className="font-body-md text-body-md text-on-surface-variant/80 leading-relaxed">{step}</span>
                </li>
              ))}
            </ol>
          </div>
        ))}
      </div>

      <div className="bg-primary/5 border border-primary/20 rounded-2xl p-stack-lg">
        <div className="flex items-start gap-stack-md">
          <span className="material-symbols-outlined text-primary text-[22px] mt-0.5">lightbulb</span>
          <div className="flex flex-col gap-stack-xs">
            <h3 className="font-headline-sm text-headline-sm text-on-surface">Tips rápidos</h3>
            <ul className="flex flex-col gap-stack-sm">
              {[
                'Usa fotos con buena iluminación y la prenda bien visible para mejores resultados.',
                'En "Find your look", combina imagen y texto para búsquedas más precisas.',
                'El slider de fusión permite dar más importancia a la imagen o al texto según tu necesidad.',
                'Prueba cambiar entre SPIMI y Postgres para comparar velocidad y resultados.',
                'Las métricas de I/O te ayudan a entender el rendimiento de cada motor de búsqueda.',
                'Haz clic en cualquier producto para ver sus atributos detallados.',
              ].map((tip, i) => (
                <li key={i} className="flex gap-2 font-body-md text-body-md text-on-surface-variant/80">
                  <span className="text-primary mt-1">•</span>
                  <span>{tip}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <footer className="border-t border-outline-variant/40 pt-stack-md">
        <p className="font-body-md text-body-md text-on-surface-variant/50 text-center">
          Veür — Multimodal fashion retrieval · Academic project
        </p>
      </footer>
    </div>
  )
}
