import type { ProductCardData } from '../components/ProductCard'

const API_BASE = '/api'

interface SearchResult {
  id: string
  name: string
  match_percentage: string
  image_url: string
}

export interface SearchMetrics {
  query_ms: number
  page_requests: number
  cache_hits: number
  disk_reads: number
  disk_writes: number
  disk_read_ms: number
  disk_write_ms: number
}

interface SearchResponse {
  results: SearchResult[]
  metrics: SearchMetrics
}

interface EnrichedResult {
  results: ProductCardData[]
  metrics: SearchMetrics
}

export interface ProductDetail {
  id: string
  name: string
  category: string
  image_url: string
  details: {
    gender: string
    subcategory: string
    type: string
    colour: string
    season: string
    year: string
    usage: string
  }
}

export async function getProductDetails(docId: string): Promise<ProductDetail | null> {
  const res = await fetch(`${API_BASE}/details/${docId}`)
  if (!res.ok) return null
  const data: { product: ProductDetail } = await res.json()
  return data.product
}

function toCard(r: SearchResult): ProductCardData {
  return {
    id: r.id,
    title: r.name,
    category: '',
    imageUrl: r.image_url,
    matchPercentage: parseInt(r.match_percentage) || 0,
  }
}

export async function visualSearch(
  image: File,
  topK = 10,
  searchType?: string
): Promise<EnrichedResult> {
  const formData = new FormData()
  formData.append('image', image)
  formData.append('top_k', String(topK))

  const params = searchType ? `?search_type=${searchType}` : ''
  const res = await fetch(`${API_BASE}/visual${params}`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error('Visual search failed')
  const data: SearchResponse = await res.json()
  return { results: data.results.map(toCard), metrics: data.metrics }
}

export async function multimodalSearch(
  image: File | null,
  textQuery: string,
  weightVisual: number,
  weightText: number,
  topK = 10,
  searchType?: string
): Promise<EnrichedResult> {
  const formData = new FormData()
  if (image) formData.append('image', image)
  formData.append('text_query', textQuery)
  formData.append('weight_visual', String(weightVisual))
  formData.append('weight_text', String(weightText))
  formData.append('top_k', String(topK))

  const params = searchType ? `?search_type=${searchType}` : ''
  const res = await fetch(`${API_BASE}/multimodal${params}`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error('Multimodal search failed')
  const data: SearchResponse = await res.json()
  return { results: data.results.map(toCard), metrics: data.metrics }
}
