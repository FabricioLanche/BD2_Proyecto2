import Sidebar from './Sidebar'

interface LayoutProps {
  currentPage: string
  onNavigate: (page: string) => void
  children: React.ReactNode
}

export default function Layout({ currentPage, onNavigate, children }: LayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-background text-on-background font-body-md text-body-md antialiased">
      <Sidebar currentPage={currentPage} onNavigate={onNavigate} />
      <main className="flex-1 ml-0 md:ml-[260px] h-full overflow-y-auto bg-surface-container-lowest">
        <header className="md:hidden flex justify-between items-center w-full px-margin-mobile h-16 border-b border-surface-container-highest bg-surface-container-lowest sticky top-0 z-10">
          <h1 className="font-headline-sm text-headline-sm font-bold text-on-surface">Visionary IR</h1>
          <button className="text-on-surface-variant">
            <span className="material-symbols-outlined">menu</span>
          </button>
        </header>
        <div className="max-w-container-max-width mx-auto p-margin-mobile md:p-gutter flex flex-col gap-stack-lg">
          {children}
        </div>
      </main>
    </div>
  )
}
