import { useRef, useState } from 'react'

interface UploadZoneProps {
  imagePreview?: string | null
  onUpload: (file: File) => void
  onClear?: () => void
  label?: string
  subLabel?: string
}

export default function UploadZone({ imagePreview, onUpload, onClear, label = 'Drop a photo here', subLabel = 'Or click to browse your files' }: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const handleFile = (file: File) => {
    if (file.type.startsWith('image/')) {
      onUpload(file)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFile(file)
      e.target.value = ''
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!imagePreview) setDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.currentTarget.contains(e.relatedTarget as Node)) return
    setDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) handleFile(file)
  }

  return (
    <div
      className={`rounded-xl border-2 flex flex-col items-center justify-center text-center min-h-[200px] transition-all duration-300 relative overflow-hidden ${
        imagePreview
          ? 'border-outline-variant/60 bg-surface-container-lowest p-1'
          : dragging
            ? 'border-primary border-solid bg-primary/5 scale-[1.02] cursor-pointer'
            : 'border-dashed border-outline-variant bg-surface hover:bg-surface-container hover:border-primary/40 cursor-pointer group py-stack-lg px-stack-md'
      }`}
      onClick={() => !imagePreview && inputRef.current?.click()}
      onDragOver={handleDragOver}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {imagePreview ? (
        <div className="relative w-full h-full group/preview">
          <img
            src={imagePreview}
            alt="Uploaded"
            className="max-h-[300px] w-full object-contain rounded-lg pointer-events-none"
          />
          <div className="absolute inset-0 bg-black/0 group-hover/preview:bg-black/10 transition-colors rounded-lg" />
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onClear?.() }}
            className="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/50 text-white flex items-center justify-center hover:bg-black/70 transition-all opacity-0 group-hover/preview:opacity-100 scale-90 group-hover/preview:scale-100"
          >
            <span className="material-symbols-outlined text-[16px]">close</span>
          </button>
        </div>
      ) : (
        <>
          <span className={`material-symbols-outlined text-[44px] transition-colors mb-stack-sm ${dragging ? 'text-primary' : 'text-on-surface-variant/60 group-hover:text-primary/60'}`}>
            {dragging ? 'move_down' : 'cloud_upload'}
          </span>
          <p className="font-label-md text-label-md text-on-surface">{dragging ? 'Drop it!' : label}</p>
          <p className="font-body-md text-body-md text-on-surface-variant/60 mt-1 max-w-[260px]">{subLabel}</p>
        </>
      )}
      <input ref={inputRef} className="hidden" type="file" accept="image/*" onChange={handleInputChange} />
    </div>
  )
}
