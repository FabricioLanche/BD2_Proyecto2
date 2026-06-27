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

  return (
    <>
      <div className="flex flex-col gap-stack-xs">
        <h2 className="font-display-lg text-display-lg text-on-surface">Recommendation Engine</h2>
        <p className="font-body-lg text-body-lg text-on-surface-variant">
          Fuse visual and textual queries to find precise product matches.
        </p>
      </div>

      <div className="flex items-center gap-4">
        <span className="font-label-sm text-label-sm text-on-surface-variant/70 uppercase tracking-wider">Fusion Balance</span>
        <FusionSlider value={textWeight} onChange={setTextWeight} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-stack-lg">
        <UploadZone imagePreview={imagePreview} onUpload={handleUpload} />
        <div className="border border-outline-variant bg-surface-container-lowest rounded-lg p-stack-md flex flex-col h-full min-h-[240px]">
          <label className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-stack-sm" htmlFor="text-query">
            Text Query
          </label>
          <textarea
            className="w-full flex-1 bg-transparent border-none resize-none focus:ring-0 p-0 font-body-lg text-body-lg text-on-surface placeholder:text-on-surface-variant/50"
            id="text-query"
            placeholder="Describe the product you are looking for... e.g., 'Modern minimalist wooden dining chair with a curved back'"
            value={textQuery}
            onChange={(e) => setTextQuery(e.target.value)}
          />
        </div>
      </div>

      <button
        onClick={handleSearch}
        disabled={loading || (!imageFile && !textQuery.trim())}
        className="self-start flex items-center gap-2 bg-primary text-on-primary font-label-md text-label-md px-6 py-2.5 rounded-lg hover:brightness-110 transition-all disabled:opacity-40 disabled:pointer-events-none"
      >
        {loading ? (
          <>
            <span className="material-symbols-outlined text-[18px] animate-spin">progress_activity</span>
            Searching…
          </>
        ) : (
          <>
            <span className="material-symbols-outlined text-[18px]">search</span>
            Search
          </>
        )}
      </button>

      {error && (
        <div className="bg-error-container text-on-error-container rounded-lg px-4 py-3 font-body-md text-body-md">
          {error}
        </div>
      )}

      {results.length > 0 && (
        <div>
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-stack-md">Recommendations</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-stack-sm md:gap-stack-md">
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
