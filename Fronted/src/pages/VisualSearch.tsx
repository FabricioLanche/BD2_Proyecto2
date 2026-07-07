import { useState, useEffect } from 'react'
import UploadZone from '../components/UploadZone'
import ProductCard, { type ProductCardData } from '../components/ProductCard'
import DetailModal from '../components/DetailModal'
import SearchModeSelector from '../components/SearchModeSelector'
import { visualSearch, type SearchMetrics } from '../services/api'

function useItemsPerPage(): number {
  const [items, setItems] = useState(() => {
    if (typeof window === 'undefined') return 10
    if (window.innerWidth < 640) return 4
    if (window.innerWidth < 1024) return 6
    if (window.innerWidth < 1280) return 8
    return 10
  })
  useEffect(() => {
    const onResize = () => {
      setItems(
        window.innerWidth < 640 ? 4 :
        window.innerWidth < 1024 ? 6 :
        window.innerWidth < 1280 ? 8 : 10
      )
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  return items
}

export default function VisualSearch() {
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [selectedProduct, setSelectedProduct] = useState<ProductCardData | null>(null)
  const [page, setPage] = useState(1)
  const [results, setResults] = useState<ProductCardData[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [topK, setTopK] = useState<number | string>('')
  const [searched, setSearched] = useState(false)
  const [searchMode, setSearchMode] = useState<'spimi' | 'postgres'>('spimi')
  const [metrics, setMetrics] = useState<SearchMetrics | null>(null)
  const perPage = useItemsPerPage()
  const totalPages = Math.max(1, Math.ceil(results.length / perPage))

  const handleUpload = (file: File) => {
    setImagePreview(URL.createObjectURL(file))
    setImageFile(file)
    setResults([])
    setError(null)
    setSearched(false)
  }

  const handleSearch = async () => {
    if (!imageFile) return
    setResults([])
    setPage(1)
    setMetrics(null)
    setError(null)
    setLoading(true)
    setSearched(false)
    try {
      const { results, metrics } = await visualSearch(imageFile, topK || 10, searchMode)
      setResults(results)
      setMetrics(metrics)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed')
    } finally {
      setSearched(true)
      setLoading(false)
    }
  }

  useEffect(() => { setPage(1) }, [results.length, perPage])

  const handleClear = () => {
    if (imagePreview) URL.revokeObjectURL(imagePreview)
    setImagePreview(null)
    setImageFile(null)
    setResults([])
    setError(null)
  }

  const disabled = loading || !imageFile

  const searchBtn = (
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
  )

  const inputCard = (
    <div className="border border-outline-variant/60 bg-surface-container-lowest rounded-2xl overflow-hidden w-full">
      <div className="p-4">
        <UploadZone
          imagePreview={imagePreview}
          onUpload={handleUpload}
          onClear={handleClear}
          label="Drop a fashion photo here"
          subLabel="Or click to browse your files"
        />
      </div>
      <div className="border-t border-outline-variant/40 px-4 py-3 flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="font-label-sm text-label-sm text-on-surface-variant/50 whitespace-nowrap">Results</label>
            <input
              type="number"
              min={1}
              value={topK}
              onChange={(e) => setTopK(e.target.value === '' ? '' : Number(e.target.value))}
              placeholder="K"
              className={`w-16 bg-surface-container border rounded-lg px-2.5 py-1.5 font-label-sm text-label-sm outline-none focus:ring-1 focus:ring-primary/40 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none ${
                topK === ''
                  ? 'border-dashed border-outline-variant/30 text-on-surface-variant/35'
                  : 'border-outline-variant/40 text-on-surface'
              }`}
            />
          </div>
          <SearchModeSelector value={searchMode} onChange={setSearchMode} />
        </div>
        {searchBtn}
      </div>
    </div>
  )

  return results.length > 0 ? (
    <div className="md:grid md:grid-cols-[minmax(340px,420px)_1fr] md:gap-6 min-h-[calc(100vh-5rem)]">
        <div className="flex flex-col min-h-0 md:sticky md:top-6 md:max-h-[calc(100vh-3rem)] md:overflow-y-auto">
          <div className="flex-none sticky top-0 z-10 bg-surface-container-lowest">
            <div className="flex flex-col gap-1 mb-4">
              <span className="flex items-center gap-1 font-label-sm text-label-sm text-primary/70 mb-1">
                <span className="material-symbols-outlined text-[13px]">image_search</span>
                Visual search
              </span>
              <h1 className="font-serif text-display-lg text-on-surface">Shop by photo</h1>
              <p className="font-body-lg text-body-lg text-on-surface-variant/70">Upload any photo and we'll find similar styles for you</p>
            </div>
          </div>

        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex-1 min-h-0" />
          <div className="flex-none">
            {inputCard}

            {metrics && (
              <div className="flex items-center gap-3 flex-wrap mt-4">
                <span className="inline-flex items-center gap-1 font-code text-[11px] text-on-surface-variant/50 bg-surface-container px-2.5 py-1 rounded-full">
                  <span className="material-symbols-outlined text-[13px]">timer</span>
                  {metrics.query_ms.toFixed(1)} ms
                </span>
                <span className="inline-flex items-center gap-1 font-code text-[11px] text-on-surface-variant/50 bg-surface-container px-2.5 py-1 rounded-full">
                  <span className="material-symbols-outlined text-[13px]">storage</span>
                  {metrics.page_requests} page req
                </span>
                <span className="inline-flex items-center gap-1 font-code text-[11px] text-on-surface-variant/50 bg-surface-container px-2.5 py-1 rounded-full">
                  <span className="material-symbols-outlined text-[13px]">memory</span>
                  {metrics.cache_hits} cache hits
                </span>
                <span className="inline-flex items-center gap-1 font-code text-[11px] text-on-surface-variant/50 bg-surface-container px-2.5 py-1 rounded-full">
                  <span className="material-symbols-outlined text-[13px]">database</span>
                  {metrics.disk_reads} reads / {metrics.disk_writes} writes
                </span>
              </div>
            )}

            {error && (
              <div className="bg-error-container/80 text-on-error-container rounded-xl px-4 py-3 font-body-md text-body-md border border-error/10 mt-4">
                {error}
              </div>
            )}
          </div>
          <div className="flex-1 min-h-0" />
        </div>
      </div>

      <div className="flex flex-col min-h-0">
        <div className="flex-1 flex flex-col min-h-0">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-headline-sm text-headline-sm text-on-surface">Retrieved Matches</h3>
            <span className="font-label-md text-label-md text-on-surface-variant/60 bg-surface-container px-3 py-1 rounded-full">{results.length} results</span>
          </div>

          <div className="flex items-center gap-1 sm:gap-2">
            {page > 1 && (
              <button
                onClick={() => setPage((p) => p - 1)}
                className="shrink-0 w-8 sm:w-9 h-8 sm:h-9 flex items-center justify-center rounded-full bg-surface-container border border-outline-variant/30 shadow-sm hover:bg-surface-container-high transition-colors"
                aria-label="Previous page"
              >
                <span className="material-symbols-outlined text-[16px] sm:text-[18px]">chevron_left</span>
              </button>
            )}
            <div className="flex-1 overflow-hidden rounded-lg min-w-0">
              <div
                className="flex transition-transform duration-300 ease-out will-change-transform"
                style={{ transform: `translateX(-${(page - 1) * 100}%)` }}
              >
                {Array.from({ length: totalPages }, (_, i) => (
                  <div key={i} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-stack-md min-w-0 flex-[0_0_100%]">
                    {results.slice(i * perPage, (i + 1) * perPage).map((product) => (
                      <ProductCard key={product.id} product={product} onClick={setSelectedProduct} />
                    ))}
                  </div>
                ))}
              </div>
            </div>
            {page < totalPages && (
              <button
                onClick={() => setPage((p) => p + 1)}
                className="shrink-0 w-8 sm:w-9 h-8 sm:h-9 flex items-center justify-center rounded-full bg-surface-container border border-outline-variant/30 shadow-sm hover:bg-surface-container-high transition-colors"
                aria-label="Next page"
              >
                <span className="material-symbols-outlined text-[16px] sm:text-[18px]">chevron_right</span>
              </button>
            )}
          </div>

          {totalPages > 1 && (
            <div className="flex justify-center gap-2 mt-3">
              {Array.from({ length: totalPages }, (_, i) => (
                <button
                  key={i}
                  onClick={() => setPage(i + 1)}
                  className={`h-2 rounded-full transition-all duration-300 ${
                    page === i + 1
                      ? 'bg-primary w-5'
                      : 'bg-outline-variant/30 hover:bg-outline-variant/50 w-2'
                  }`}
                  aria-label={`Page ${i + 1}`}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {selectedProduct && (
        <DetailModal product={selectedProduct} onClose={() => setSelectedProduct(null)} />
      )}
    </div>
  ) : (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-5rem)]">
      <div className="flex flex-col items-center gap-1 text-center mb-6 max-w-lg">
        <span className="flex items-center gap-1 font-label-sm text-label-sm text-primary/70">
          <span className="material-symbols-outlined text-[13px]">image_search</span>
          Visual search
        </span>
        <h1 className="font-serif text-display-lg text-on-surface">Shop by photo</h1>
        <p className="font-body-lg text-body-lg text-on-surface-variant/70">Upload any photo and we'll find similar styles for you</p>
      </div>

      <div className="w-full max-w-xl">
        {inputCard}

        {searched && results.length === 0 && !loading && !error && (
          <div className="bg-surface-container/60 text-on-surface-variant rounded-xl px-5 py-4 font-body-md text-body-md border border-outline-variant/20 mt-4 text-center">
            No matching products found for the uploaded image.
          </div>
        )}
      </div>

      {selectedProduct && (
        <DetailModal product={selectedProduct} onClose={() => setSelectedProduct(null)} />
      )}
    </div>
  )
}
