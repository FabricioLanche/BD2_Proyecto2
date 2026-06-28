interface PaginationProps {
  page: number
  totalPages: number
  onPageChange: (page: number) => void
}

export default function Pagination({ page, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null

  const pages: number[] = []
  const start = Math.max(1, page - 1)
  const end = Math.min(totalPages, page + 1)
  for (let i = start; i <= end; i++) pages.push(i)

  return (
    <div className="flex items-center justify-center gap-1.5 pt-stack-md">
      <button
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
        className="w-8 h-8 flex items-center justify-center rounded-lg text-sm text-on-surface-variant hover:bg-surface-container disabled:opacity-30 disabled:pointer-events-none transition-all active:scale-95"
      >
        <span className="material-symbols-outlined text-[18px]">chevron_left</span>
      </button>
      {start > 1 && (
        <>
          <button onClick={() => onPageChange(1)} className="w-8 h-8 flex items-center justify-center rounded-lg text-sm text-on-surface-variant hover:bg-surface-container transition-all active:scale-95">1</button>
          {start > 2 && <span className="w-8 h-8 flex items-center justify-center text-sm text-on-surface-variant/40">...</span>}
        </>
      )}
      {pages.map((p) => (
        <button
          key={p}
          onClick={() => onPageChange(p)}
          className={`w-8 h-8 flex items-center justify-center rounded-lg text-sm font-medium transition-all active:scale-95 ${
            p === page ? 'bg-primary text-on-primary shadow-sm' : 'text-on-surface-variant hover:bg-surface-container'
          }`}
        >
          {p}
        </button>
      ))}
      {end < totalPages && (
        <>
          {end < totalPages - 1 && <span className="w-8 h-8 flex items-center justify-center text-sm text-on-surface-variant/40">...</span>}
          <button onClick={() => onPageChange(totalPages)} className="w-8 h-8 flex items-center justify-center rounded-lg text-sm text-on-surface-variant hover:bg-surface-container transition-all active:scale-95">{totalPages}</button>
        </>
      )}
      <button
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
        className="w-8 h-8 flex items-center justify-center rounded-lg text-sm text-on-surface-variant hover:bg-surface-container disabled:opacity-30 disabled:pointer-events-none transition-all active:scale-95"
      >
        <span className="material-symbols-outlined text-[18px]">chevron_right</span>
      </button>
    </div>
  )
}
