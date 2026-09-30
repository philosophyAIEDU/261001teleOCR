import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";

export const ACCEPT = ".jpg,.jpeg,.png,.webp,.pdf,image/jpeg,image/png,image/webp,application/pdf";
const ALLOWED = /\.(jpe?g|png|webp|pdf)$/i;

interface Props {
  onFile: (file: File) => void;
  disabled?: boolean;
  maxMb?: number;
}

/** 클립보드 붙여넣기에서 파일 이름이 없는 이미지에 이름을 붙여 줍니다. */
function nameClipboardFile(file: File): File {
  if (file.name && ALLOWED.test(file.name)) return file;
  const ext = file.type === "image/jpeg" ? "jpg" : file.type === "image/webp" ? "webp" : "png";
  return new File([file], `붙여넣은-이미지.${ext}`, { type: file.type || "image/png" });
}

export default function UploadDropzone({ onFile, disabled = false, maxMb = 50 }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  // Ctrl+V(⌘+V)로 캡처 이미지를 바로 붙여 넣을 수 있게 합니다.
  useEffect(() => {
    function onPaste(event: ClipboardEvent) {
      if (disabled) return;
      const target = event.target as HTMLElement | null;
      if (target && (target.tagName === "TEXTAREA" || target.tagName === "INPUT")) return;
      const file = Array.from(event.clipboardData?.files ?? []).find((f) => f.type.startsWith("image/") || f.type === "application/pdf");
      if (file) {
        event.preventDefault();
        onFile(nameClipboardFile(file));
      }
    }
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [onFile, disabled]);

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (disabled) return;
    const file = event.dataTransfer.files[0];
    if (file) onFile(file);
  }

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) onFile(file);
    event.target.value = "";
  }

  return (
    <div
      data-testid="dropzone"
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`flex flex-col items-center gap-4 rounded-2xl border-4 border-dashed p-8 text-center transition ${
        dragging ? "border-brand-600 bg-brand-50" : "border-slate-300 bg-white"
      }`}
    >
      <span aria-hidden="true" className="text-5xl">
        📥
      </span>
      <p className="text-xl font-bold">파일을 여기로 끌어다 놓거나, 아래 버튼을 눌러 선택하세요</p>
      <p className="text-slate-700">
        사진(JPG·PNG·WEBP) 또는 PDF · 최대 {maxMb}MB · 화면 캡처는 <kbd className="kbd">Ctrl</kbd>+
        <kbd className="kbd">V</kbd> 로 붙여 넣을 수 있어요
      </p>
      <button type="button" className="btn-primary text-lg" disabled={disabled} onClick={() => inputRef.current?.click()}>
        파일 선택하기
      </button>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="sr-only"
        aria-label="변환할 파일 선택"
        onChange={handleChange}
        tabIndex={-1}
      />
    </div>
  );
}
