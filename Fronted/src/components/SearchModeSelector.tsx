interface SearchModeSelectorProps {
  value: 'spimi' | 'postgres'
  onChange: (mode: 'spimi' | 'postgres') => void
}

const modes = [
  { value: 'spimi', label: 'SPIMI', description: 'Implementación propia' },
  { value: 'postgres', label: 'Postgres', description: 'HNSW + GIST' },
] as const

export default function SearchModeSelector({ value, onChange }: SearchModeSelectorProps) {
  return (
    <div className="flex items-center gap-3">
      <label className="font-label-sm text-label-sm text-on-surface-variant/50 whitespace-nowrap">Engine</label>
      <div className="flex bg-surface-container rounded-lg p-0.5 border border-outline-variant/30">
        {modes.map((mode) => (
          <button
            key={mode.value}
            type="button"
            onClick={() => onChange(mode.value)}
            className={`relative px-3 py-1.5 font-label-md text-label-md rounded-md transition-all duration-200 ${
              value === mode.value
                ? 'bg-primary text-on-primary shadow-sm'
                : 'text-on-surface-variant/60 hover:text-on-surface-variant/90'
            }`}
          >
            {mode.label}
          </button>
        ))}
      </div>
    </div>
  )
}
