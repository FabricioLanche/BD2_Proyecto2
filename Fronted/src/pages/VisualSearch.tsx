import { useMemo, useState } from 'react'
import UploadZone from '../components/UploadZone'
import ProcessingStepper from '../components/ProcessingStepper'
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

  return (
    <div className="flex flex-col lg:flex-row gap-gutter">
      <section className="flex-1 flex flex-col gap-stack-lg">
        <header className="flex items-center justify-between pb-stack-sm">
          <h1 className="font-display-lg text-display-lg text-on-surface">Visual Query Input</h1>
        </header>

        <UploadZone imagePreview={imagePreview} onUpload={handleUpload} />

        {loading && <ProcessingStepper running={loading} />}

        {error && (
          <div className="bg-error-container text-on-error-container rounded-lg px-4 py-3 font-body-md text-body-md">
            {error}
          </div>
        )}

        <div className={`flex flex-col gap-stack-md transition-opacity duration-500 ${results.length > 0 ? 'opacity-100' : 'opacity-50 pointer-events-none'}`}>
          <div className="flex items-center justify-between">
            <h3 className="font-headline-md text-headline-md text-on-surface">Retrieved Matches</h3>
            <span className="font-label-md text-label-md text-on-surface-variant bg-surface-container px-3 py-1 rounded-full">Top {results.length} Results</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-stack-sm">
            {visible.map((product) => (
              <ProductCard key={product.id} product={product} onClick={setSelectedProduct} />
            ))}
          </div>

          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </div>
      </section>

      {selectedProduct && (
        <DetailModal product={selectedProduct} onClose={() => setSelectedProduct(null)} />
      )}
    </div>
  )
}
