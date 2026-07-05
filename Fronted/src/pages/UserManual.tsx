const sections = [
  {
    icon: 'image_search',
    title: 'Shop by photo',
    subtitle: 'Visual search with images',
    steps: [
      'Upload a fashion photo by clicking or dragging into the upload zone.',
      'Click "Search looks" to find visually similar products from the catalog.',
      'Browse results sorted by similarity percentage. Click any card for details.',
      'Use the detail modal to view attributes like colour, season, category, and more.',
    ],
  },
  {
    icon: 'auto_awesome',
    title: 'Find your look',
    subtitle: 'Multimodal search (image + text)',
    steps: [
      'Upload a photo, type a description, or use both for richer results.',
      'Adjust the fusion slider to control how much weight each input has.',
      'The slider lets you prioritise the image (drag left) or the text (drag right).',
      'Click "Search looks" to get recommendations combining both modalities.',
    ],
  },
  {
    icon: 'touch_app',
    title: 'Interacting with results',
    subtitle: 'Product cards & pagination',
    steps: [
      'Each product card shows a thumbnail, category, and match percentage.',
      'Click a card to open the detail modal with full product metadata.',
      'Use the pagination controls at the bottom to navigate through pages.',
      'Press Escape or click outside the modal to close it.',
    ],
  },
]

export default function UserManual() {
  return (
    <div className="flex flex-col gap-stack-lg">
      <header className="flex flex-col gap-1">
        <span className="flex items-center gap-1 font-label-sm text-label-sm text-primary/70 mb-1">
          <span className="material-symbols-outlined text-[13px]">help_outline</span>
          User guide
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
                'En "Find your look", combiná imagen y texto para búsquedas más precisas.',
                'El slider de fusión permite dar más importancia a la imagen o al texto según tu necesidad.',
                'Hacé clic en cualquier producto para ver sus atributos detallados.',
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
