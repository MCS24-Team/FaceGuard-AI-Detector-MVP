import { useCallback, useEffect, useRef, useState } from "react";

export default function FileDropzone({
  onFileSelected,
  acceptedFormats,
  previewUrl,
  fileName,
  isAnalyzing = false,
  onClear
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);
  const dropzoneRef = useRef(null);

  const handleFile = useCallback(
    (file) => {
      if (!file) return;
      onFileSelected(file);
    },
    [onFileSelected]
  );

  const openFilePicker = useCallback(() => {
    if (isAnalyzing) return;
    inputRef.current?.click();
  }, [isAnalyzing]);

  const handleKeyDown = (event) => {
    if (isAnalyzing) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openFilePicker();
    }
  };

  // Paste from clipboard anywhere on the page while the dropzone has no preview.
  useEffect(() => {
    const onPaste = (event) => {
      if (isAnalyzing) return;
      const items = event.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
        if (item.type?.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) {
            handleFile(file);
            event.preventDefault();
            return;
          }
        }
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [handleFile, isAnalyzing]);

  return (
    <div
      ref={dropzoneRef}
      className={dragging ? "dropzone dropzone-active" : "dropzone"}
      role="button"
      tabIndex={0}
      aria-label="Upload image by click, drag and drop, or paste"
      onDragOver={(event) => {
        if (isAnalyzing) return;
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        if (isAnalyzing) return;
        event.preventDefault();
        setDragging(false);
        handleFile(event.dataTransfer.files?.[0]);
      }}
      onClick={openFilePicker}
      onKeyDown={handleKeyDown}
    >
      <input
        ref={inputRef}
        type="file"
        className="hidden-input"
        accept={acceptedFormats.join(",")}
        disabled={isAnalyzing}
        onChange={(event) => handleFile(event.target.files?.[0])}
      />

      {!previewUrl ? <div className="dropzone-brackets" aria-hidden="true"><span /></div> : null}

      {previewUrl ? (
        <>
          <div className="dropzone-preview-frame">
            <img src={previewUrl} alt="Uploaded preview" className="dropzone-preview-image" />
            <div className="preview-corners-bottom" aria-hidden="true" />
            {isAnalyzing ? (
              <div className="scan-overlay" aria-hidden="true">
                <div className="scan-reticle">
                  <span />
                </div>
                <div className="scan-glow" />
                <div className="scan-line" />
              </div>
            ) : null}
          </div>

          <div className="dropzone-preview-meta">
            <p className="dropzone-file-name" title={fileName || "Selected image"}>
              {fileName || "Selected image"}
            </p>
            <div className="dropzone-actions">
              <button
                type="button"
                className="secondary-btn"
                onClick={(event) => {
                  event.stopPropagation();
                  openFilePicker();
                }}
                disabled={isAnalyzing}
              >
                Replace Image
              </button>
              <button
                type="button"
                className="ghost-btn"
                onClick={(event) => {
                  event.stopPropagation();
                  onClear?.();
                }}
                disabled={isAnalyzing}
              >
                Remove
              </button>
            </div>
          </div>
        </>
      ) : (
        <>
          <p className="dropzone-title">Drop an image to begin</p>
          <p className="dropzone-subtitle">or click to browse · paste from clipboard</p>
          <p className="dropzone-formats">
            {acceptedFormats.join(" · ")}
            <kbd>Ctrl</kbd>
            <kbd>V</kbd>
          </p>
          <button
            type="button"
            className="secondary-btn"
            style={{ marginTop: "20px" }}
            onClick={(event) => {
              event.stopPropagation();
              openFilePicker();
            }}
          >
            Choose File
          </button>
        </>
      )}
    </div>
  );
}
