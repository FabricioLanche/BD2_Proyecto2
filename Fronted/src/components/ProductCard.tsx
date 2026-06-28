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
    <div
      className="group cursor-pointer bg-surface-container-lowest rounded-xl overflow-hidden border border-outline-variant/40 hover:border-outline-variant hover:shadow-md hover:-translate-y-0.5 transition-all duration-300"
      onClick={() => onClick?.(product)}
    >
      <div className="relative aspect-[1/1.25] bg-surface overflow-hidden">
        <img
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700 ease-out"
          src={product.imageUrl}
          alt={product.title}
        />
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/5 transition-colors duration-500" />
        <div className="absolute bottom-2 right-2 bg-white/90 backdrop-blur-sm text-on-surface font-code text-[11px] font-semibold px-2 py-0.5 rounded-full shadow-sm">
          {product.matchPercentage}%
        </div>
      </div>
      <div className="p-stack-md flex flex-col gap-0.5">
        <span className="font-body-md text-body-md text-on-surface truncate leading-tight">{product.title}</span>
        <span className="font-body-md text-body-md text-on-surface-variant/60 truncate text-[12px]">{product.category}</span>
      </div>
    </div>
  )
}
