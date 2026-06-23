import { useState } from 'react'

export default function FusionSlider() {
  const [textWeight, setTextWeight] = useState(40)
  const imageWeight = 100 - textWeight

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
        value={textWeight}
        onChange={(e) => setTextWeight(Number(e.target.value))}
        className="flex-1 max-w-[180px]"
      />
      <div className="flex flex-col items-center gap-0 leading-none">
        <span className="font-code text-[11px] text-on-surface-variant/70 tabular-nums">{textWeight}%</span>
        <span className="material-symbols-outlined text-[16px] text-on-surface-variant/50">text_fields</span>
      </div>
    </div>
  )
}
