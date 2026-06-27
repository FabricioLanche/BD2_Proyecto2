interface SidebarProps {
  currentPage: string
  onNavigate: (page: string) => void
}

const navItems = [
  { id: 'visual-search', label: 'Visual Search', icon: 'image_search' },
  { id: 'recommendation-engine', label: 'Recommendation Engine', icon: 'auto_awesome' },
]

export default function Sidebar({ currentPage, onNavigate }: SidebarProps) {
  return (
    <nav className="fixed left-0 top-0 h-full w-[260px] flex flex-col p-stack-md gap-stack-sm bg-surface-container-low border-r border-surface-container-highest z-20 hidden md:flex">
      <div className="flex items-center gap-stack-sm px-stack-sm mb-stack-lg pt-stack-sm">
        <div className="w-10 h-10 rounded-xl bg-primary text-on-primary flex items-center justify-center font-bold shadow-sm">
          <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>search</span>
        </div>
        <div>
          <h1 className="font-headline-md text-headline-md font-bold text-on-surface leading-tight">Visionary IR</h1>
          <p className="font-label-sm text-label-sm text-on-surface-variant/60">Multimodal Retrieval</p>
        </div>
      </div>

      <div className="flex flex-col gap-1 flex-1 px-stack-xs">
        <p className="font-label-sm text-label-sm text-on-surface-variant/50 uppercase tracking-wider px-stack-sm mb-stack-xs">Search modes</p>
        {navItems.map((item) => {
          const isActive = currentPage === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`flex items-center gap-stack-sm px-stack-md py-stack-sm rounded-xl transition-all duration-150 text-left ${
                isActive
                  ? 'bg-primary text-on-primary shadow-sm'
                  : 'text-on-surface-variant hover:bg-surface-container-hover active:scale-[0.98]'
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

      <div className="mt-auto flex flex-col gap-stack-sm pt-stack-lg border-t border-surface-container-highest px-stack-xs">
        <a
          href="https://github.com/FabricioLanche/BD2_Proyecto2"
          target="_blank"
          rel="noopener noreferrer"
          className="w-full py-stack-sm px-stack-md bg-surface-container-highest text-on-surface font-label-md text-label-md rounded-xl flex justify-center items-center gap-stack-sm hover:bg-surface-container-high transition-all active:scale-[0.98]"
        >
          <span className="material-symbols-outlined text-[18px]">menu_book</span>
          Documentation
        </a>
      </div>
    </nav>
  )
}
