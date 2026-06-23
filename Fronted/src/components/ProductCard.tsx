export interface ProductCardData {
  id: string
  title: string
  category: string
  imageUrl: string
  matchPercentage: number
  visualScore?: number
  textScore?: number
  gender?: string
  masterCategory?: string
  subCategory?: string
  articleType?: string
  baseColour?: string
  season?: string
  year?: number
  usage?: string
  productDisplayName?: string
}

interface ProductCardProps {
  product: ProductCardData
  onClick?: (product: ProductCardData) => void
}

export default function ProductCard({ product, onClick }: ProductCardProps) {
  return (
    <div className="group cursor-pointer" onClick={() => onClick?.(product)}>
      <div className="relative aspect-[1/1.25] bg-surface overflow-hidden rounded-sm">
        <img
          className="w-full h-full object-cover group-hover:scale-[1.04] transition-transform duration-700 ease-out"
          src={product.imageUrl}
          alt={product.title}
        />
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/5 transition-colors duration-500" />
        <div className="absolute bottom-1.5 right-1.5 bg-white/90 backdrop-blur-sm text-on-surface font-code text-[10px] font-semibold px-1.5 py-0.5 rounded-full shadow-sm">
          {product.matchPercentage}%
        </div>
      </div>
      <div className="mt-1.5 flex flex-col gap-0">
        <span className="font-body-md text-body-md text-on-surface truncate leading-tight">{product.title}</span>
        <span className="font-body-md text-body-md text-on-surface-variant/70 truncate text-[12px]">{product.category}</span>
      </div>
    </div>
  )
}
