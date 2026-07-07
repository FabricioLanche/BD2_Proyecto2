import type { ProductCardData } from '../components/ProductCard'

const API_BASE = '/api'

interface SearchResult {
  id: string
  name: string
  match_percentage: string
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

interface ProductDetail {
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

async function getProductDetails(docId: string): Promise<ProductDetail | null> {
  const res = await fetch(`${API_BASE}/details/${docId}`)
  if (!res.ok) return null
  const data: { product: ProductDetail } = await res.json()
  return data.product
}

async function enrichResults(results: SearchResult[]): Promise<ProductCardData[]> {
  const detailPromises = results.map(r => getProductDetails(r.id))
  const details = await Promise.allSettled(detailPromises)

  return results.map((r, i) => {
    const d = details[i].status === 'fulfilled' ? details[i].value : null
    return {
      id: r.id,
      title: d?.name ?? r.name,
      category: d?.category ?? '',
      imageUrl: d?.image_url ?? '',
      matchPercentage: parseInt(r.match_percentage) || 0,
      gender: d?.details?.gender,
      masterCategory: d?.category,
      subCategory: d?.details?.subcategory,
      articleType: d?.details?.type,
      baseColour: d?.details?.colour,
      season: d?.details?.season,
      year: d?.details?.year ? parseInt(d.details.year) : undefined,
      usage: d?.details?.usage,
      productDisplayName: d?.name,
    }
  })
}

export async function visualSearch(
  image: File,
  topK = 10,
  searchType: string = 'spimi'
): Promise<EnrichedResult> {
  const formData = new FormData()
  formData.append('image', image)
  formData.append('top_k', String(topK))
  formData.append('search_type', searchType)

  const res = await fetch(`${API_BASE}/visual`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error('Visual search failed')
  const data: SearchResponse = await res.json()
  const results = await enrichResults(data.results)
  return { results, metrics: data.metrics }
}

export async function multimodalSearch(
  image: File | null,
  textQuery: string,
  weightVisual: number,
  weightText: number,
  topK = 10,
  searchType: string = 'spimi'
): Promise<EnrichedResult> {
  const formData = new FormData()
  if (image) formData.append('image', image)
  formData.append('text_query', textQuery)
  formData.append('weight_visual', String(weightVisual))
  formData.append('weight_text', String(weightText))
  formData.append('top_k', String(topK))
  formData.append('search_type', searchType)

  const res = await fetch(`${API_BASE}/multimodal`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error('Multimodal search failed')
  const data: SearchResponse = await res.json()
  const results = await enrichResults(data.results)
  return { results, metrics: data.metrics }
}
