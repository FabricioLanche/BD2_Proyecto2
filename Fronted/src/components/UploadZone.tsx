interface UploadZoneProps {
  imagePreview?: string | null
  onUpload: (file: File) => void
}

export default function UploadZone({ imagePreview, onUpload }: UploadZoneProps) {
  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) onUpload(file)
  }

  return (
    <div
      className={`border rounded-lg p-stack-lg flex flex-col items-center justify-center text-center min-h-[200px] transition-colors relative overflow-hidden ${
        imagePreview
          ? 'border-solid border-outline-variant bg-surface-container-lowest'
          : 'border-dashed border-outline-variant bg-surface hover:bg-surface-container hover:border-primary cursor-pointer group'
      }`}
    >
      {imagePreview ? (
        <img src={imagePreview} alt="Uploaded" className="max-h-[300px] w-full object-contain rounded" />
      ) : (
        <>
          <span className="material-symbols-outlined text-[48px] text-on-surface-variant group-hover:text-primary transition-colors mb-stack-sm">cloud_upload</span>
          <p className="font-label-md text-label-md text-on-surface">Upload a product image</p>
          <p className="font-body-md text-body-md text-on-surface-variant mt-1">Drag and drop or click to browse</p>
          <input className="absolute inset-0 opacity-0 cursor-pointer w-full h-full" type="file" accept="image/*" onChange={handleFile} />
        </>
      )}
    </div>
  )
}
