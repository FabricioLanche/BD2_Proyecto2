import { useEffect, useState } from 'react'

const stepLabels = [
  'Splitting into patches',
  'Extracting SIFT features',
  'Quantizing with Codebook',
  'Querying Inverted Index',
]

type StepState = 'pending' | 'in-progress' | 'completed'

export default function ProcessingStepper({ running }: { running: boolean }) {
  const [stepStates, setStepStates] = useState<StepState[]>(() => stepLabels.map(() => 'pending'))

  useEffect(() => {
    if (!running) {
      setStepStates(stepLabels.map(() => 'pending'))
      return
    }

    let cancelled = false
    const delays = [800, 1200, 900, 1500]

    const run = async () => {
      for (let i = 0; i < stepLabels.length; i++) {
        await new Promise((r) => setTimeout(r, delays[i]))
        if (cancelled) return
        setStepStates((prev) => {
          const next = [...prev]
          if (i > 0) next[i - 1] = 'completed'
          next[i] = 'in-progress'
          return next
        })
      }
      await new Promise((r) => setTimeout(r, 400))
      if (!cancelled) {
        setStepStates((prev) => {
          const next = [...prev]
          next[stepLabels.length - 1] = 'completed'
          return next
        })
      }
    }

    run()
    return () => { cancelled = true }
  }, [running])

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-stack-lg">
      <h2 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-stack-lg">
        Pipeline Execution Status
      </h2>
      <div className="flex flex-col md:flex-row justify-between relative">
        <div className="absolute top-[11px] left-0 w-full h-[2px] bg-surface-container-high hidden md:block z-0" />
        {stepLabels.map((label, i) => {
          const state = stepStates[i]
          return (
            <div
              key={i}
              className={`flex-1 flex md:flex-col items-center gap-stack-sm relative z-10 ${state === 'in-progress' ? 'step-in-progress' : ''}`}
            >
              <div
                className={`w-6 h-6 rounded-full border-2 flex items-center justify-center text-[10px] font-bold transition-colors relative ${
                  state === 'completed'
                    ? 'bg-secondary border-secondary text-on-secondary'
                    : state === 'in-progress'
                      ? 'border-secondary bg-surface-container-lowest'
                      : 'border-outline bg-surface-container-lowest'
                }`}
              >
                {state === 'completed' && (
                  <span className="material-symbols-outlined text-[14px]">check</span>
                )}
                {state === 'in-progress' && (
                  <div className="step-dot absolute w-2 h-2 bg-secondary rounded-full top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
                )}
              </div>
              <span className={`font-code text-code text-center mt-2 ${state === 'pending' ? 'text-on-surface-variant' : 'text-on-surface'}`}>
                {label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
