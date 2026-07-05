import { useCallback, useRef } from 'react'

interface FusionSliderProps {
  value?: number
  onChange?: (textWeight: number) => void
}

export default function FusionSlider({ value: controlledValue, onChange }: FusionSliderProps) {
  const textWeight = controlledValue ?? 40
  const imageWeight = 100 - textWeight
  const trackRef = useRef<HTMLDivElement>(null)

  const handleMove = useCallback((clientX: number) => {
    const track = trackRef.current
    if (!track) return
    const rect = track.getBoundingClientRect()
    // left = 0% image, right = 100% image (thumb es el divisor)
    const raw = (clientX - rect.left) / rect.width
    const imagePct = Math.round(Math.max(0, Math.min(1, raw)) * 100)
    onChange?.(100 - imagePct)  // convertir a textWeight
  }, [onChange])

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    handleMove(e.clientX)
    const onMove = (ev: MouseEvent) => handleMove(ev.clientX)
    const onUp = () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [handleMove])

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    e.preventDefault()
    handleMove(e.touches[0].clientX)
    const onMove = (ev: TouchEvent) => handleMove(ev.touches[0].clientX)
    const onEnd = () => {
      document.removeEventListener('touchmove', onMove)
      document.removeEventListener('touchend', onEnd)
    }
    document.addEventListener('touchmove', onMove, { passive: false })
    document.addEventListener('touchend', onEnd)
  }, [handleMove])

  // imageWeight% from left = thumb position (thumb divide imagen a la izq, texto a la der)
  const thumbLeftPct = imageWeight

  return (
    <div className="flex items-center gap-3 w-full select-none">
      {/* Image side */}
      <div className="flex items-center gap-1.5 shrink-0">
        <span className="material-symbols-outlined text-[15px] text-primary/60">image</span>
        <span className="font-code text-[13px] text-primary font-semibold tabular-nums w-7">
          {imageWeight}%
        </span>
      </div>

      {/* Track */}
      <div
        ref={trackRef}
        className="relative flex-1 h-1.5 rounded-full bg-surface-container-highest cursor-pointer"
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
      >
        {/* Image fill — left portion, desde el borde hasta el thumb */}
        <div
          className="absolute left-0 top-0 bottom-0 bg-primary/40 rounded-full pointer-events-none transition-[width] duration-75"
          style={{ width: `${thumbLeftPct}%` }}
        />
        {/* Text fill — right portion, desde el thumb hasta el borde */}
        <div
          className="absolute right-0 top-0 bottom-0 bg-secondary/30 rounded-full pointer-events-none transition-[width] duration-75"
          style={{ width: `${100 - thumbLeftPct}%` }}
        />
        {/* Thumb */}
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 rounded-full bg-white border-2 border-primary shadow-md hover:scale-110 active:scale-95 transition-transform cursor-grab active:cursor-grabbing z-10"
          style={{ left: `${thumbLeftPct}%` }}
          onMouseDown={(e) => { e.stopPropagation(); handleMouseDown(e) }}
          onTouchStart={(e) => { e.stopPropagation(); handleTouchStart(e) }}
        />
      </div>

      {/* Text side */}
      <div className="flex items-center gap-1.5 shrink-0">
        <span className="font-code text-[13px] text-secondary font-semibold tabular-nums w-7 text-right">
          {textWeight}%
        </span>
        <span className="material-symbols-outlined text-[15px] text-secondary/60">text_fields</span>
      </div>
    </div>
  )
}