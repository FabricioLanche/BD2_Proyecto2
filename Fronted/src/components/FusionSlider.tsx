import { useCallback, useRef } from 'react'

interface FusionSliderProps {
  value?: number
  onChange?: (textWeight: number) => void
}

export default function FusionSlider({ value: controlledValue, onChange }: FusionSliderProps) {
  const val = controlledValue ?? 40
  const imageWeight = 100 - val
  const trackRef = useRef<HTMLDivElement>(null)

  const handleMove = useCallback((clientY: number) => {
    const track = trackRef.current
    if (!track) return
    const rect = track.getBoundingClientRect()
    const y = Math.max(0, Math.min(rect.height, rect.bottom - clientY))
    const pct = Math.round((y / rect.height) * 100)
    onChange?.(Math.max(0, Math.min(100, pct)))
  }, [onChange])

  const handleMouseDown = (e: React.MouseEvent) => {
    handleMove(e.clientY)
    const onMove = (ev: MouseEvent) => handleMove(ev.clientY)
    const onUp = () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }

  return (
    <div className="flex items-center h-full min-h-[80px] max-h-[120px] select-none gap-2.5 justify-center">
      <div className="flex flex-col items-center gap-1 min-w-[28px]">
        <span className="font-code text-[11px] text-primary font-semibold tabular-nums">{imageWeight}%</span>
        <span className="material-symbols-outlined text-[16px] text-primary/40">image</span>
      </div>

      <div
        ref={trackRef}
        className="relative w-2 flex-1 min-h-[40px] max-h-[80px] bg-surface-container-highest rounded-full cursor-pointer"
        onMouseDown={handleMouseDown}
      >
        <div
          className="absolute bottom-0 left-0 right-0 bg-primary/30 rounded-full pointer-events-none transition-[height] duration-75"
          style={{ height: `${imageWeight}%` }}
        />
        <div
          className="absolute left-1/2 -translate-x-1/2 w-3.5 h-3.5 rounded-full bg-white border-[3px] border-primary shadow-md hover:scale-110 active:scale-95 transition-transform -translate-y-1/2"
          style={{ bottom: `${imageWeight}%` }}
          onMouseDown={(e) => { e.stopPropagation(); handleMouseDown(e.nativeEvent) }}
        />
      </div>

      <div className="flex flex-col items-center gap-1 min-w-[28px]">
        <span className="material-symbols-outlined text-[16px] text-secondary/40">text_fields</span>
        <span className="font-code text-[11px] text-secondary font-semibold tabular-nums">{val}%</span>
      </div>
    </div>
  )
}
