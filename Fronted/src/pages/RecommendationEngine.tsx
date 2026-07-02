import UploadZone from '../components/UploadZone'
import FusionSlider from '../components/FusionSlider'
import ProductCard, { type ProductCardData } from '../components/ProductCard'
import DetailModal from '../components/DetailModal'
import Pagination from '../components/Pagination'
import { useMemo, useState } from 'react'
import { multimodalSearch } from '../services/api'

const PER_PAGE = 3

export default function RecommendationEngine() {
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [textQuery, setTextQuery] = useState('')
  const [textWeight, setTextWeight] = useState(40)
  const [selectedProduct, setSelectedProduct] = useState<ProductCardData | null>(null)
  const [page, setPage] = useState(1)
  const [results, setResults] = useState<ProductCardData[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const totalPages = Math.max(1, Math.ceil(results.length / PER_PAGE))
  const visible = useMemo(() => results.slice((page - 1) * PER_PAGE, page * PER_PAGE), [results, page])

  const handleUpload = (file: File) => {
    setImagePreview(URL.createObjectURL(file))
    setImageFile(file)
  }

  const handleClear = () => {
    if (imagePreview) URL.revokeObjectURL(imagePreview)
    setImagePreview(null)
    setImageFile(null)
    setTextQuery('')
    setResults([])
    setError(null)
    setPage(1)
  }

  const handleSearch = async () => {
    if (!imageFile && !textQuery.trim()) return
    setResults([])
    setError(null)
    setPage(1)
    setLoading(true)
    try {
      const data = await multimodalSearch(
        imageFile,
        textQuery,
        100 - textWeight,
        textWeight
      )
      setResults(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  const disabled = loading || (!imageFile && !textQuery.trim())

  return (
    <>
      <div className="flex flex-col gap-1">
        <span className="flex items-center gap-1 font-label-sm text-label-sm text-primary/70 mb-1">
          <span className="material-symbols-outlined text-[13px]">auto_awesome</span>
          Visual search
        </span>
        <h2 className="font-serif text-display-lg text-on-surface">Find your look</h2>
        <p className="font-body-lg text-body-lg text-on-surface-variant/70">
          Upload a photo, describe what you're after, or combine both.
        </p>
      </div>

      <div className="border border-outline-variant/60 bg-surface-container-lowest rounded-2xl overflow-hidden">
        <div className="grid grid-cols-2 divide-x divide-outline-variant/40">
          <div className="min-h-[160px] p-4">
            <UploadZone imagePreview={imagePreview} onUpload={handleUpload} onClear={handleClear} />
          </div>
          <div className="min-h-[160px] p-4 flex flex-col">
            <div className="flex items-center justify-between mb-stack-xs">
              <label className="flex items-center gap-1.5 font-label-md text-label-md text-on-surface-variant/60" htmlFor="text-query">
                <span className="material-symbols-outlined text-[16px]">text_fields</span>
                Describe it
              </label>
              {textQuery && (
                <button
                  type="button"
                  onClick={() => setTextQuery('')}
                  className="text-on-surface-variant/30 hover:text-on-surface-variant/60 transition-colors"
                >
                  <span className="material-symbols-outlined text-[16px]">close</span>
                </button>
              )}
            </div>
            <textarea
              className="w-full flex-1 bg-transparent border-none resize-none outline-none focus:ring-0 p-0 font-body-lg text-body-lg text-on-surface placeholder:text-on-surface-variant/35 leading-relaxed"
              id="text-query"
              placeholder='e.g. Oversized cream linen blazer with gold buttons'
              value={textQuery}
              onChange={(e) => setTextQuery(e.target.value)}
            />
            <div className="flex items-center justify-between mt-stack-xs pt-stack-xs border-t border-outline-variant/30">
              <span className="font-code text-[11px] text-on-surface-variant/35">
                {textQuery.length > 0 ? `${textQuery.length} characters` : 'Type to describe'}
              </span>
              {textQuery && (
                <span className="font-code text-[11px] text-on-surface-variant/35">
                  {textQuery.trim() ? textQuery.trim().split(/\s+/).length : 0} words
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="border-t border-outline-variant/40 px-5 py-3 flex items-center gap-4">
          <span className="font-label-sm text-label-sm text-on-surface-variant/50 whitespace-nowrap shrink-0">Search weight</span>
          <div className="flex-1 flex justify-center">
            <div className="w-full max-w-md">
              <FusionSlider value={textWeight} onChange={setTextWeight} />
            </div>
          </div>
          <div className="w-[140px] shrink-0" />
        </div>

        <div className="border-t border-outline-variant/40 px-4 py-3 flex items-center justify-between">
          <button
            onClick={handleSearch}
            disabled={disabled}
            className="flex items-center gap-2 bg-search-bg text-search-text font-label-md text-label-md px-6 py-2.5 rounded-xl hover:brightness-125 transition-all disabled:opacity-40 disabled:pointer-events-none active:scale-[0.98] shadow-sm"
          >
            {loading ? (
              <>
                <span className="material-symbols-outlined text-[18px] animate-spin">progress_activity</span>
                Searching…
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[18px]">search</span>
                Search looks
              </>
            )}
          </button>
          {disabled && (
            <span className="font-body-sm text-body-sm text-on-surface-variant/40">Need at least a photo or description</span>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-error-container/80 text-on-error-container rounded-xl px-4 py-3 font-body-md text-body-md border border-error/10">
          {error}
        </div>
      )}

      {results.length > 0 && (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
          <div className="flex items-center justify-between mb-stack-md">
            <h3 className="font-headline-sm text-headline-sm text-on-surface">Recommendations</h3>
            <span className="font-label-md text-label-md text-on-surface-variant/60 bg-surface-container px-3 py-1 rounded-full">{results.length} results</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-stack-md">
            {visible.map((product) => (
              <ProductCard key={product.id} product={product} onClick={setSelectedProduct} />
            ))}
          </div>
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </div>
      )}

      {selectedProduct && (
        <DetailModal product={selectedProduct} onClose={() => setSelectedProduct(null)} />
      )}
    </>
  )
}
