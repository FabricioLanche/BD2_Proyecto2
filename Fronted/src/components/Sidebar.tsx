interface SidebarProps {
  currentPage: string
  onNavigate: (page: string) => void
}

const navItems = [
  { id: 'visual-search', label: 'Shop by photo', icon: 'image_search' },
  { id: 'recommendation-engine', label: 'Find your look', icon: 'auto_awesome' },
]

export default function Sidebar({ currentPage, onNavigate }: SidebarProps) {
  return (
    <nav className="fixed left-0 top-0 h-full w-[260px] flex flex-col p-stack-md gap-stack-sm bg-[#F5F0E8] border-r border-[#E0D8CC] z-20 hidden md:flex">
      <div className="flex items-center gap-stack-sm px-stack-sm mb-stack-lg pt-stack-sm">
        <div className="w-10 h-10 rounded-xl bg-[#E8DDD0] text-[#7A5C1E] flex items-center justify-center font-bold shadow-sm">
          <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>search</span>
        </div>
        <div>
          <h1 className="font-serif text-headline-md font-bold text-[#0F0F0D] leading-tight">Veür</h1>
          <p className="font-label-sm text-label-sm text-[#8C8880]">Fashion visual search</p>
        </div>
      </div>

      <div className="flex flex-col gap-1 flex-1 px-stack-xs">
        <p className="font-label-sm text-label-sm text-[#B0A898] uppercase tracking-wider px-stack-sm mb-stack-xs">DISCOVER</p>
        {navItems.map((item) => {
          const isActive = currentPage === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`flex items-center gap-stack-sm px-stack-md py-stack-sm rounded-xl transition-all duration-150 text-left ${
                isActive
                  ? 'bg-[#C9A96E]/10 text-[#7A5C1E] shadow-sm'
                  : 'text-[#6B5A45] hover:bg-black/5 active:scale-[0.98]'
              }`}
            >
              <span
                className="material-symbols-outlined text-[20px]"
                style={isActive ? { fontVariationSettings: "'FILL' 1" } : undefined}
              >
                {item.icon}
              </span>
              <span className="font-label-md text-label-md">{item.label}</span>
            </button>
          )
        })}
      </div>

      <div className="mt-auto flex flex-col gap-stack-xs pt-stack-lg border-t border-[#E0D8CC] px-stack-xs">
        <a
          href="https://github.com/FabricioLanche/BD2_Proyecto2"
          target="_blank"
          rel="noopener noreferrer"
          className="w-full py-stack-sm px-stack-md border border-[#D8CFC4] text-[#6B5A45] font-label-md text-label-md rounded-xl flex justify-center items-center gap-stack-sm hover:bg-black/5 transition-all active:scale-[0.98]"
        >
          <svg viewBox="0 0 16 16" className="w-[18px] h-[18px] fill-current" aria-hidden="true">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
          </svg>
          View on GitHub
        </a>
        <p className="font-code text-[11px] text-[#B0A898] text-center">Multimodal fashion retrieval · Academic project</p>
      </div>
    </nav>
  )
}
