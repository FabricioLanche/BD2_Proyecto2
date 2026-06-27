import { useMemo, useState } from 'react'
import UploadZone from '../components/UploadZone'
import ProductCard, { type ProductCardData } from '../components/ProductCard'
import DetailModal from '../components/DetailModal'
import Pagination from '../components/Pagination'
import { visualSearch } from '../services/api'

const PER_PAGE = 5

export default function VisualSearch() {
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [selectedProduct, setSelectedProduct] = useState<ProductCardData | null>(null)
  const [page, setPage] = useState(1)
  const [results, setResults] = useState<ProductCardData[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const totalPages = Math.max(1, Math.ceil(results.length / PER_PAGE))
  const visible = useMemo(() => results.slice((page - 1) * PER_PAGE, page * PER_PAGE), [results, page])

  const handleUpload = async (file: File) => {
    setImagePreview(URL.createObjectURL(file))
    setResults([])
    setError(null)
    setPage(1)
    setLoading(true)
    try {
      const data = await visualSearch(file)
      setResults(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    setImagePreview(null)
    setResults([])
    setError(null)
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-stack-lg">
      <header className="flex flex-col gap-1">
        <h1 className="font-display-lg text-display-lg text-on-surface">Visual Search</h1>
        <p className="font-body-lg text-body-lg text-on-surface-variant/70">Search products by uploading an image</p>
      </header>

      <UploadZone imagePreview={imagePreview} onUpload={handleUpload} onClear={handleClear} />

      {error && (
        <div className="bg-error-container/80 text-on-error-container rounded-xl px-4 py-3 font-body-md text-body-md border border-error/10">
          {error}
        </div>
      )}

      {results.length > 0 && (
        <div className="flex flex-col gap-stack-md animate-in fade-in slide-in-from-bottom-2 duration-500">
          <div className="flex items-center justify-between">
            <h3 className="font-headline-sm text-headline-sm text-on-surface">Retrieved Matches</h3>
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
    </div>
  )
}
