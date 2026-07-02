import { useState, useEffect } from 'react'
import Layout from './components/Layout'
import RecommendationEngine from './pages/RecommendationEngine'
import VisualSearch from './pages/VisualSearch'
import './index.css'

export default function App() {
  const [page, setPage] = useState(() => localStorage.getItem('opencode_page') || 'visual-search')

  useEffect(() => {
    localStorage.setItem('opencode_page', page)
  }, [page])

  return (
    <Layout currentPage={page} onNavigate={setPage}>
      {page === 'visual-search' && <VisualSearch />}
      {page === 'recommendation-engine' && <RecommendationEngine />}
    </Layout>
  )
}
