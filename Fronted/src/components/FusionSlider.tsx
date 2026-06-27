interface FusionSliderProps {
  value?: number
  onChange?: (textWeight: number) => void
}

export default function FusionSlider({ value: controlledValue, onChange }: FusionSliderProps) {
  const imageWeight = 100 - (controlledValue ?? 40)

  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className="flex flex-col items-center gap-0 leading-none">
        <span className="font-code text-[11px] text-on-surface-variant/70 tabular-nums">{imageWeight}%</span>
        <span className="material-symbols-outlined text-[16px] text-on-surface-variant/50">image</span>
      </div>
      <input
        type="range"
        min="0"
        max="100"
        value={controlledValue ?? 40}
        onChange={(e) => onChange?.(Number(e.target.value))}
        className="flex-1 max-w-[180px]"
      />
      <div className="flex flex-col items-center gap-0 leading-none">
        <span className="font-code text-[11px] text-on-surface-variant/70 tabular-nums">{controlledValue ?? 40}%</span>
        <span className="material-symbols-outlined text-[16px] text-on-surface-variant/50">text_fields</span>
      </div>
    </div>
  )
}
