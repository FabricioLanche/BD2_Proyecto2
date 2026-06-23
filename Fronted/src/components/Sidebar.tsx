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
      <div className="flex items-center gap-stack-sm mb-stack-lg px-stack-sm">
        <div className="w-10 h-10 rounded bg-primary text-on-primary flex items-center justify-center font-bold">
          <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>widgets</span>
        </div>
        <div>
          <h1 className="font-headline-md text-headline-md font-black text-on-primary-fixed">Visionary IR</h1>
          <p className="font-label-sm text-label-sm text-on-surface-variant">Multimodal Retrieval</p>
        </div>
      </div>

      <div className="flex flex-col gap-stack-xs flex-1">
        {navItems.map((item) => {
          const isActive = currentPage === item.id
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`flex items-center gap-stack-sm px-stack-md py-stack-sm font-label-md text-label-md rounded-lg transition-all duration-100 text-left ${
                isActive
                  ? 'bg-surface-container-highest text-primary font-bold'
                  : 'text-on-surface-variant hover:bg-surface-container hover:scale-[0.98]'
              }`}
            >
              <span
                className="material-symbols-outlined"
                style={isActive ? { fontVariationSettings: "'FILL' 1" } : undefined}
              >
                {item.icon}
              </span>
              <span>{item.label}</span>
            </button>
          )
        })}
      </div>

      <div className="mt-auto flex flex-col gap-stack-sm pt-stack-lg border-t border-surface-container-highest">
        <a
          href="https://github.com/FabricioLanche/BD2_Proyecto2"
          target="_blank"
          rel="noopener noreferrer"
          className="w-full py-stack-sm px-stack-md bg-primary text-on-primary font-label-md text-label-md rounded-lg flex justify-center items-center gap-stack-sm hover:opacity-90 transition-opacity"
        >
          <span className="material-symbols-outlined">menu_book</span>
          Documentation
        </a>
      </div>
    </nav>
  )
}
