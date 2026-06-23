import UploadZone from '../components/UploadZone'
import FusionSlider from '../components/FusionSlider'
import ProductCard, { type ProductCardData } from '../components/ProductCard'
import DetailModal from '../components/DetailModal'
import Pagination from '../components/Pagination'
import { useMemo, useState } from 'react'

const products: ProductCardData[] = [
  {
    id: 'FUR-001',
    title: 'Ashwood Curved Dining Chair',
    category: 'Furniture > Chairs',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCkRtb3DzlBBlpREtnnZlPmTcHZOoiAeMSzSnDWuu3VsjxUUsmFX5QQRvI-4MP8ncaFbgOU4YNZJPoH7tGAufQAcYBhNpArM4Kd5qFEpJyFCUCVapyrAoyZ7x-XGLgvEj-bEvJZdneAGU72ORYEpVETvd1uFaZvu0JTp0KhWknaqy3qh0mA3-7O-9ap_HhsVpqyb-2mMRPDeuGCmBkrGk8DIBEkYv1QxRNAUXEzNCQZXkSIDVyTMrvSMJgscCJTI6vTLG-_6TlzaNCI',
    matchPercentage: 85,
    visualScore: 92,
    textScore: 78,
    gender: 'Men',
    masterCategory: 'Furniture',
    subCategory: 'Seating',
    articleType: 'Chairs',
    baseColour: 'Ash Brown',
    season: 'All Season',
    year: 2024,
    usage: 'Casual',
    productDisplayName: 'Ashwood Curved Dining Chair',
  },
  {
    id: 'FUR-002',
    title: 'Eik Shell Lounge Chair',
    category: 'Furniture > Lounge',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDnkCMwkLwEPyYu0ezoBSZVczNF3fuuqnBBahaJ_thjzVcxRliSKdH8SwjKrlrRBTFI-_GRoq0537mPL_mV5MjbhYGS5QKEqMiSYE1ZJmKEC9LfDvUuv2ivSd9bM6YBUosLd2bpl_aOMesGVPplmgPgJqJonQ2p1YI13H7mP9IknE2VxD5hFjQSru_o6CBjuBTk4ZmGIZGx8MqRTlqHgtmoZ60doaf_RJ6RL6tjNsGMsjo60AwxCMzPdv_jl7HQvNJYOrkn7e6zjfgS',
    matchPercentage: 82,
    visualScore: 88,
    textScore: 76,
    gender: 'Women',
    masterCategory: 'Furniture',
    subCategory: 'Seating',
    articleType: 'Lounge Chair',
    baseColour: 'White',
    season: 'All Season',
    year: 2024,
    usage: 'Casual',
    productDisplayName: 'Eik Shell Lounge Chair',
  },
  {
    id: 'FUR-003',
    title: 'Birch Minimalist Stool',
    category: 'Furniture > Stools',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuD351kE_74tLw_PYJdWNkp_y39dsJszWFxUWayO2aDB3kwRnKwFTsuj-jcjDwIoq0gKXMPiWJ3ggRvKNygZiah2FdfIaaSAZXOqT48qLiqEETmKpetQ7NKTpPTRs_G-hNUJ6OzO554VkR3C_QV9gB_3H3PzSq3IYUsjDpejHXJNQsBsChkuQBadmIQ8Ao_9ChsZE4hNHZIC7kccyJMrJwME9KuEQ1jwSXcEuhOm7HGJjWFEchfXRNc4pCKw2QIJznqrCLIIozVrXulX',
    matchPercentage: 74,
    visualScore: 80,
    textScore: 68,
    gender: 'Unisex',
    masterCategory: 'Furniture',
    subCategory: 'Seating',
    articleType: 'Stool',
    baseColour: 'Birch',
    season: 'All Season',
    year: 2024,
    usage: 'Casual',
    productDisplayName: 'Birch Minimalist Stool',
  },
  {
    id: 'FUR-004',
    title: 'Metal Frame Rattan Chair',
    category: 'Furniture > Chairs',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCD8-E9TII4iBZgLwzjNOaopYCDBQM3vTGJD9TzuIMIkIDHCsdyHMgRHvZ8Vh5cmJiOdgrSUW-PNRNZkpZj-vy7tK2VtT8rzpZkJKQuatD8FV3MRhc1ImMr6wrPRO88efRHhu_wg_lJ0mDA9Cys1cJOQIV14-xwL7Omb-yHvW5YxbaOTTq1_R4P8sFHAhcVdw40SQ2pVPDPlDIcoX8qZ_Y48FfK3lGCErO3KMILGNdseuP-ToWHOXG2gZ9ceQfCUw5dRVGO3X0Y9rSF',
    matchPercentage: 68,
    visualScore: 75,
    textScore: 61,
    gender: 'Men',
    masterCategory: 'Furniture',
    subCategory: 'Seating',
    articleType: 'Chair',
    baseColour: 'Black',
    season: 'All Season',
    year: 2023,
    usage: 'Casual',
    productDisplayName: 'Metal Frame Rattan Chair',
  },
  {
    id: 'FUR-005',
    title: 'Walnut Coffee Table',
    category: 'Furniture > Tables',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAar42iNa-K5qGR6xGglZuvgPNT89jbGQvdRSd6m0l3Q47O2sR_8lFQHegIX6uO9r-sLQ2BbTT7-1RGXP5oL5v7KOJ2wEKn8yyN9UoreGodBXe0s4amuwmxg0xQow8o3mtZPkSK5pROV4DRlrulV8GNGhvyo_RBzw-wMtn-IAkMk_DioXTQmO0n5e1qLhGIQZtgFhofgSctsoUWTThJnWjPsGCDRSG-u6YEVQC9bbiZwO37tJTeAFRn9qTxBzwpQG0jhfHdFAC1QmkZ',
    matchPercentage: 62,
    visualScore: 55,
    textScore: 69,
    gender: 'Unisex',
    masterCategory: 'Furniture',
    subCategory: 'Tables',
    articleType: 'Coffee Table',
    baseColour: 'Walnut',
    season: 'All Season',
    year: 2024,
    usage: 'Casual',
    productDisplayName: 'Walnut Coffee Table',
  },
  {
    id: 'DEC-001',
    title: 'Brass Dome Table Lamp',
    category: 'Decor > Lighting',
    imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA6J68Hl_LY_vOnCuSXFX--7BYjbhgH1dOaEkx-4d_DwPBiTD37EFvZV7TC_ywpJK49dQZdS3u2gr5vjuvAIaBFIPnfQmyric9YaPjZi9XO0Dr305sHF2_r48Tgxo9mM-Dg9MgPM6jibE1TYcGG9u_LnWjqZ7KrCy1TbxxNbNgOzettDznvcxrqQTEzqO6AAbCSERXcYwM-8IHETRiZ6zEVHHylkXcnEX_cgAf0WxurSlsS-LBNSaH0BUFBQ11v-XuDmmH3pwtiMMDa',
    matchPercentage: 45,
    visualScore: 30,
    textScore: 60,
    gender: 'Women',
    masterCategory: 'Home Decor',
    subCategory: 'Lighting',
    articleType: 'Table Lamp',
    baseColour: 'Brass',
    season: 'All Season',
    year: 2024,
    usage: 'Casual',
    productDisplayName: 'Brass Dome Table Lamp',
  },
]

const PER_PAGE = 3

export default function RecommendationEngine() {
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [selectedProduct, setSelectedProduct] = useState<ProductCardData | null>(null)
  const [page, setPage] = useState(1)

  const totalPages = Math.ceil(products.length / PER_PAGE)
  const visible = useMemo(() => products.slice((page - 1) * PER_PAGE, page * PER_PAGE), [page])

  const handleUpload = (file: File) => {
    setImagePreview(URL.createObjectURL(file))
  }

  return (
    <>
      <div className="flex flex-col gap-stack-xs">
        <h2 className="font-display-lg text-display-lg text-on-surface">Recommendation Engine</h2>
        <p className="font-body-lg text-body-lg text-on-surface-variant">
          Fuse visual and textual queries to find precise product matches.
        </p>
      </div>

      <FusionSlider />

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
          />
        </div>
      </div>

      <div>
        <h3 className="font-headline-sm text-headline-sm text-on-surface mb-stack-md">Recommendations</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-stack-sm md:gap-stack-md">
          {visible.map((product) => (
            <ProductCard key={product.id} product={product} onClick={setSelectedProduct} />
          ))}
        </div>
        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      </div>

      {selectedProduct && (
        <DetailModal product={selectedProduct} onClose={() => setSelectedProduct(null)} />
      )}
    </>
  )
}
