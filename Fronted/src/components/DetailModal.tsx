import { useEffect } from 'react'
import type { ProductCardData } from './ProductCard'

interface DetailModalProps {
  product: ProductCardData
  onClose: () => void
}

export default function DetailModal({ product, onClose }: DetailModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handler)
      document.body.style.overflow = ''
    }
  }, [onClose])

  const attrs: { label: string; value: string | number | undefined }[] = [
    { label: 'Gender', value: product.gender },
    { label: 'Category', value: product.masterCategory },
    { label: 'Subcategory', value: product.subCategory },
    { label: 'Type', value: product.articleType },
    { label: 'Colour', value: product.baseColour },
    { label: 'Season', value: product.season },
    { label: 'Year', value: product.year },
    { label: 'Usage', value: product.usage },
  ]

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="bg-surface-container-lowest w-full sm:max-w-lg sm:mx-4 max-h-[90vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl shadow-2xl animate-in slide-in-from-bottom-4 sm:slide-in-from-bottom-0 duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative">
          <div className="h-64 sm:h-72 w-full bg-surface overflow-hidden">
            <img src={product.imageUrl} alt={product.title} className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-black/10 to-transparent" />
          </div>
          <button
            onClick={onClose}
            className="absolute top-3 right-3 w-8 h-8 rounded-full bg-white/80 backdrop-blur-sm flex items-center justify-center text-on-surface hover:bg-white hover:scale-105 transition-all shadow-sm"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
          <div className="absolute bottom-3 left-4 flex gap-2">
            <span className="bg-white/90 backdrop-blur-sm text-on-surface font-code text-xs font-semibold px-2.5 py-1 rounded-full shadow-sm">
              {product.matchPercentage}% match
            </span>
          </div>
        </div>

        <div className="px-5 pt-5 pb-7 flex flex-col gap-5">
          <div>
            <h2 className="font-headline-md text-headline-md text-on-surface">{product.title}</h2>
            <p className="font-body-md text-body-md text-on-surface-variant/60 mt-0.5">{product.category}</p>
          </div>

          <div className="h-px bg-surface-container-highest/60" />

          <div className="grid grid-cols-2 gap-x-6 gap-y-3.5">
            {attrs.filter(a => a.value).map((a) => (
              <div key={a.label}>
                <span className="font-label-sm text-label-sm text-on-surface-variant/50 uppercase tracking-widest">{a.label}</span>
                <p className="font-body-md text-body-md text-on-surface mt-0.5 capitalize">{String(a.value)}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
