import { useMemo, useState } from 'react'
import UploadZone from '../components/UploadZone'
import ProcessingStepper from '../components/ProcessingStepper'
import ProductCard, { type ProductCardData } from '../components/ProductCard'
import DetailModal from '../components/DetailModal'
import Pagination from '../components/Pagination'

const products: ProductCardData[] = [
  { id: 'BAG-001', title: 'Onyx Leather Tote', category: 'Accessories / Bags', imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuC4RhVb6-vDw_UBRK7laZ5nON6nudJ9kjxsxN3W9H0OewXjZ5EXpeu_6L69uvL-NseWrSSd-qIqIqYzaM5xT93dKh6eP3mbsMvd3iVF61pljP5KjaCGTFAbuonLStAixcleip3GYHbuDQk9QaxRR-kyY60J89NPDY7ENbLxbos8RPZ08P3nCN280tfC7sEeWj8kAsYUVP3AVRQMFsFda6AUJF1oOacJzaCHx2W6unBOdO0M0zVz9QPG5G4lYd5WUI011jEPHqu4hlll', matchPercentage: 98.4, gender: 'Women', masterCategory: 'Accessories', subCategory: 'Bags', articleType: 'Tote', baseColour: 'Black', season: 'All Season', year: 2024, usage: 'Casual', productDisplayName: 'Onyx Leather Tote' },
  { id: 'BAG-002', title: 'Navy Canvas Messenger', category: 'Accessories / Bags', imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDRkM8Pc_eaiIOTLZkepnT53zN2fDKiOqa9DZwQdwnIE_Hi9x11l2Rv8X_kvYpA8v8dLY0gXp93YBuUszAp43ZPUtA1_AIJZtx5_IJqfCS9CuBnGr2dm7wHEOX9PCZGqEoxyaYZmuyJlFIjWgGlCWczdmsTRHnnUl_Jj7YU9bT-dTQi4-yD6IT2FGr6q0ol4G-QsdZvH9YtxqpF9KeDc3dvFMYpq18Rb34lo1qlsdT9pc8kO_hw4j1qQC9IiZAIbomSBht-mbZq8iy5', matchPercentage: 94.1, gender: 'Men', masterCategory: 'Accessories', subCategory: 'Bags', articleType: 'Messenger Bag', baseColour: 'Navy Blue', season: 'Fall', year: 2024, usage: 'Casual', productDisplayName: 'Navy Canvas Messenger' },
  { id: 'BAG-003', title: 'Charcoal Daypack', category: 'Accessories / Bags', imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCe-OYgxyRUrG5lJvVBQNtxVw9jLjsbpUyAdZIeOUYT_dUlwQPJM_0ms6j1KhLqM3DEE_kd6Y2hmeo3IsSUTRZGc6990d_gRkHcgZwAuJH76DkaOEUjE0k5C6kGDUoDnbBr2-moA1OM1yUZ9uC6DuczwpdVURheYS2cG08DDRfoqURTDqLjZbAA1lmPE_x2cSVt8T9vunkFvz9w9viB2l_nkAGpMp-0c2tBVBulC2vOsBXvoP37yRuLdVU1QDQ1IHa6w_u8Jpobavx1', matchPercentage: 89.7, gender: 'Men', masterCategory: 'Accessories', subCategory: 'Bags', articleType: 'Backpack', baseColour: 'Charcoal', season: 'All Season', year: 2024, usage: 'Sports', productDisplayName: 'Charcoal Daypack' },
  { id: 'BAG-004', title: 'Suede Hobo Bag', category: 'Accessories / Bags', imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDlxlpiROWvGXHbzQQkYCssDZZ2N17rVy7uofVkuWar6wZ5BSAu6f0om0WdQbCiMvB-0RkRzyfov18FXxnBpRWIiM0yiahf4EeyCcReJw2-YYa-8DVODbkOjnFKOvUlCL5b9xlPF4_bpwtbEqfLbAa7hePhcl6idRwKEPJ2CmpgRxjrvxgARKiEotXUvQEZsVviS1gmsWM333r1rq0QuKYKsDYS_RM6LwGTCdrRyMkaViC6J5TdIloltbaCskPQKjmFdUqz7bzPWnqo', matchPercentage: 85.2, gender: 'Women', masterCategory: 'Accessories', subCategory: 'Bags', articleType: 'Hobo Bag', baseColour: 'Brown', season: 'Fall', year: 2023, usage: 'Casual', productDisplayName: 'Suede Hobo Bag' },
  { id: 'BAG-005', title: 'Vegan Satchel', category: 'Accessories / Bags', imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuA937LtXJ67tEn6opqhSn3TeOsKQ2J37oTp98GWWupxJszSq7jMv39ke76rmhSrg-i9IP-8jevAvQq4TOXiD0f3AsBa9oa_aEA4Mr9R_ej7tARes8K8UmJTLyRGs2cCp6bnx8yWCw7GRLY8aJy7gbX3FuttwL904XGOCKzlX0RYPZ17in9ZJLMoTb_jJ64A1KbZFF17ffPRjkZ8YE_NmyCKoI9FeYHJeHV4hlMmp5z8ABZ1N2LTNvppBzdWLRGoEyXEReor9WLY76JG', matchPercentage: 82.9, gender: 'Women', masterCategory: 'Accessories', subCategory: 'Bags', articleType: 'Satchel', baseColour: 'Black', season: 'All Season', year: 2024, usage: 'Casual', productDisplayName: 'Vegan Satchel' },
  { id: 'BAG-006', title: 'Ivory Crossbody', category: 'Accessories / Bags', imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDBAU8bDfCqaHT9H_s0ozvP5XpkQDXj4kQ7l43ZspickgEfJQOnipOn9X1oI5hItGBR5kiIJWMWutZV88v6vD5s1Wf13tXDjqT6tjyCNgSmoEVhPUOUGIYpF0DpsU4MsgXmstfQiHOWgixqnlCJdPSnio2t55vjpfiOU_VL9IKFFwAIEPtbneNjPO4VDov2Sj444D5ns-ZDlpEwcr6fD8BsWUi0yhgmWRc34X3AtTDNfC_W9hng0F37gB8rJPEUYjo00QeScMMODrNK', matchPercentage: 78.5, gender: 'Women', masterCategory: 'Accessories', subCategory: 'Bags', articleType: 'Crossbody', baseColour: 'Ivory', season: 'Summer', year: 2024, usage: 'Casual', productDisplayName: 'Ivory Crossbody' },
  { id: 'BAG-007', title: 'Nylon Weekender', category: 'Accessories / Bags', imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBwNvoDMiyiQOyGVL7DdP7OPJLK_0g2B4gMkP4wvAzNQ-po1HaQ6tfX20oSAHxhM0BDcidpMxKUZULlFG_6oje-qcQkdCbgT1pV2Sqr22HcAEBB5AYRZ2zZUeDPN7ru-4P3F7kxIZR0a5vPQB5P4Of6xT81QaHl1s6l8pfiZQ-RyvSiJGLp1CL8nMcAxWzze24WcWVXQb4Wc2uVCJYiqwam4I02qRm-HLNp1m-YIh3Mn1Cyev1Aa4ZSh7BIm4gPMcOQCMQv9m6am9R8', matchPercentage: 76.1, gender: 'Men', masterCategory: 'Accessories', subCategory: 'Bags', articleType: 'Duffel', baseColour: 'Black', season: 'All Season', year: 2023, usage: 'Travel', productDisplayName: 'Nylon Weekender' },
  { id: 'BAG-008', title: 'Tan Briefcase', category: 'Accessories / Bags', imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAGbDr79tyQLgkMeJ-cxxxrjNJj6vjNYCAzYJE7onlTUxfl42BLZib5H4a5kk1soV2ydbvUgINMoJbKB2DEd4HiPDf-ZBTT1TxLRkyLf0LH_dZ-aro8YY6i4zkspHSpZF87UD1IBKhKiiLVfDDEUMt8zf9qV_iCGeVxK_w-nnTSRHx_-lNCgoczfhz0PAk0zIeSXJjedkYD4AhDJ2lPdVovETCkvo1jaJrQdc4Pt_oBNhE1ZSAcSAuXIGQzFGe7lAKo9G5V3mWMXaT8', matchPercentage: 74.0, gender: 'Men', masterCategory: 'Accessories', subCategory: 'Bags', articleType: 'Briefcase', baseColour: 'Tan', season: 'All Season', year: 2024, usage: 'Formal', productDisplayName: 'Tan Briefcase' },
  { id: 'BAG-009', title: 'Woven Summer Tote', category: 'Accessories / Bags', imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBnJkAJ8FLEbXiVldUfLKFdY1pHHhwwgHEyjxDyogcCa06jwlIkVV8koKyzDJcyiq1eHesW6d55oxTUwZ7l6-dpPcpSccXtb_s3kibfWY_uT_OH2DRqLXUXELII6FjtUpGXHHlLAQS3CgoUXVnh3cISvUmkHaJvz-2tM2rVffkvihorHVoJJbqLsXY4oukzDXWYlrulz0wgcLPw4aPuaKpbZxYj4tYjfgnKu-ZEw0mmMJwowOOcv4J86t_3wAkPZQMRdS0IOK9GDQY_', matchPercentage: 69.8, gender: 'Women', masterCategory: 'Accessories', subCategory: 'Bags', articleType: 'Tote', baseColour: 'Natural', season: 'Summer', year: 2024, usage: 'Casual', productDisplayName: 'Woven Summer Tote' },
  { id: 'BAG-010', title: 'Clear Mini PVC', category: 'Accessories / Bags', imageUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCAWVMBEsGUwto8TrxmGceK2JERIrGFf5WOuyywKaqtTK_7ejKnXrwYRmp_RTI5WsCo3hpp-5OL866ds7foRdTaxsstk0boMLR9q9ej5jGl-OsUvEDtkhITfE5ZQ7ybpaKI8qD2bLlGM6qhxWvitZ8iUtWPVOzt3HzOJ01yu29G1TzhqjlfgXQjajzKshfDQ7MDUNTYY6wLM4YhVlvr3zeRY0xhYU1Hy3mCyUJHCs_YmCGa5zv_XeBeBBQxrgJ74g-n_HTl4_lcxXrn', matchPercentage: 65.4, gender: 'Women', masterCategory: 'Accessories', subCategory: 'Bags', articleType: 'Mini Bag', baseColour: 'Transparent', season: 'Summer', year: 2024, usage: 'Casual', productDisplayName: 'Clear Mini PVC' },
]

const PER_PAGE = 5

export default function VisualSearch() {
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [selectedProduct, setSelectedProduct] = useState<ProductCardData | null>(null)
  const [page, setPage] = useState(1)

  const totalPages = Math.ceil(products.length / PER_PAGE)
  const visible = useMemo(() => products.slice((page - 1) * PER_PAGE, page * PER_PAGE), [page])

  const handleUpload = (file: File) => {
    setImagePreview(URL.createObjectURL(file))
  }

  return (
    <div className="flex flex-col lg:flex-row gap-gutter">
      <section className="flex-1 flex flex-col gap-stack-lg">
        <header className="flex items-center justify-between pb-stack-sm">
          <h1 className="font-display-lg text-display-lg text-on-surface">Visual Query Input</h1>
        </header>

        <UploadZone imagePreview={imagePreview} onUpload={handleUpload} />

        {!!imagePreview && <ProcessingStepper running={!!imagePreview} />}

        <div className={`flex flex-col gap-stack-md transition-opacity duration-500 ${imagePreview ? 'opacity-100' : 'opacity-50 pointer-events-none'}`}>
          <div className="flex items-center justify-between">
            <h3 className="font-headline-md text-headline-md text-on-surface">Retrieved Matches</h3>
            <span className="font-label-md text-label-md text-on-surface-variant bg-surface-container px-3 py-1 rounded-full">Top {products.length} Results</span>
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
