import { useEffect } from "react";
import { api } from "../api/client";
import ErrorAlert from "../components/ErrorAlert";
import ExportBar from "../components/ExportBar";
import ImageStage from "../components/ImageStage";
import InferenceProgress from "../components/InferenceProgress";
import PageSelector from "../components/PageSelector";
import ResultView from "../components/results/ResultView";
import TaskPicker from "../components/TaskPicker";
import UploadDropzone from "../components/UploadDropzone";
import { useConvertStore } from "../store/convertStore";
import type { LayoutBlock, TaskId } from "../types";

/** 레이아웃 영역 종류에 맞는 작업 (영역을 눌러 다시 변환할 때 사용) */
const BLOCK_TASK: Record<string, TaskId> = {
  table: "table",
  equation: "formula",
  code: "code",
  algorithm: "code",
  seal: "seal",
  char: "chart",
};

const SAMPLE_BUTTONS = [
  { id: "english_text", label: "영어 지문 샘플" },
  { id: "table", label: "표 샘플" },
  { id: "formula", label: "수식 샘플" },
];

export default function Convert() {
  const s = useConvertStore();
  const { upload, results, currentPage } = s;
  const current = results[currentPage];
  const busy = s.running || s.uploading;

  // 화면을 떠나거나 창을 닫으면 서버의 임시 파일을 지웁니다.
  useEffect(() => {
    const onUnload = () => {
      const id = useConvertStore.getState().upload?.upload_id;
      if (id) navigator.sendBeacon?.(`/api/uploads/${id}/delete-beacon`);
    };
    window.addEventListener("pagehide", onUnload);
    return () => window.removeEventListener("pagehide", onUnload);
  }, []);

  function selectBlock(block: LayoutBlock) {
    const [x1, y1, x2, y2] = block.bbox;
    s.setCropMode(true);
    s.setCrop({ x: x1, y: y1, width: Math.max(0.02, x2 - x1), height: Math.max(0.02, y2 - y1) });
    s.setTask(BLOCK_TASK[block.type] ?? "text");
  }

  if (!upload) {
    return (
      <div className="flex flex-col gap-6">
        <h1 className="text-3xl font-bold">변환하기</h1>
        <ErrorAlert message={s.error} onClose={() => s.setError(null)} />
        <UploadDropzone onFile={(f) => void s.uploadFile(f)} disabled={busy} />
        {s.uploading && (
          <p role="status" className="text-lg">
            파일을 준비하고 있어요…
          </p>
        )}
        <section aria-labelledby="sample-title" className="rounded-2xl border border-slate-300 bg-white p-4">
          <h2 id="sample-title" className="mb-2 text-lg font-bold">
            처음이라면 샘플로 먼저 해 보세요
          </h2>
          <div className="flex flex-wrap gap-2">
            {SAMPLE_BUTTONS.map((b) => (
              <button key={b.id} type="button" className="btn-secondary" disabled={busy} onClick={() => void s.loadSample(b.id)}>
                {b.label}
              </button>
            ))}
          </div>
        </section>
      </div>
    );
  }

  const allResults = Object.values(results).sort((a, b) => a.page - b.page);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-3xl font-bold">변환하기</h1>
        <span className="rounded-full bg-white px-3 py-1 font-medium ring-1 ring-slate-300">
          📎 {upload.filename} {upload.kind === "pdf" ? `(${upload.page_count}쪽)` : ""}
        </span>
        <button type="button" className="btn-ghost ml-auto" onClick={() => void s.reset()} disabled={busy}>
          다른 파일 올리기
        </button>
      </div>

      <ErrorAlert message={s.error} onClose={() => s.setError(null)} />

      <TaskPicker value={s.task} onChange={s.setTask} disabled={busy} />

      {upload.kind === "pdf" && upload.page_count > 1 && (
        <PageSelector
          pageCount={upload.page_count}
          selected={s.selectedPages}
          current={currentPage}
          onToggle={s.togglePage}
          onSelect={s.setSelectedPages}
          onView={s.setCurrentPage}
          disabled={busy}
        />
      )}

      <div className="flex flex-wrap items-center gap-3">
        <button type="button" className="btn-primary text-lg" onClick={() => void s.runConversion()} disabled={busy || (s.cropMode && !s.crop)}>
          {s.cropMode && s.crop ? "✂️ 자른 영역만 변환하기" : "▶ 변환하기"}
        </button>
        <button type="button" className="btn-secondary" aria-pressed={s.cropMode} onClick={() => s.setCropMode(!s.cropMode)} disabled={busy}>
          {s.cropMode ? "자르기 취소" : "✂️ 영역 잘라서 변환"}
        </button>
        <button type="button" className="btn-secondary" onClick={() => void s.runFullPage()} disabled={busy}>
          🧩 한 쪽 통째로 변환 (실험)
        </button>
      </div>
      {s.cropMode && (
        <p className="rounded-xl bg-amber-50 p-3 text-amber-950">
          왼쪽 사진에서 변환할 부분을 끌어서 선택하세요. 표 하나, 수식 하나처럼 요소 하나만 고르면 더 정확해요.
        </p>
      )}

      {s.progress && <InferenceProgress progress={s.progress} />}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section aria-label="원본 이미지" className="flex flex-col gap-2">
          <h2 className="text-xl font-bold">원본 ({currentPage + 1}쪽)</h2>
          <ImageStage
            key={`${upload.upload_id}-${currentPage}`}
            src={api.pageUrl(upload.upload_id, currentPage)}
            alt={`${upload.filename} ${currentPage + 1}쪽 원본`}
            cropMode={s.cropMode}
            crop={s.crop}
            onCropChange={s.setCrop}
            blocks={current?.blocks ?? null}
            onSelectBlock={selectBlock}
          />
        </section>
        <div>
          {current ? (
            <ResultView result={current} onChange={(content) => s.updateContent(currentPage, content)} onSelectBlock={selectBlock} />
          ) : (
            <p className="rounded-2xl border-2 border-dashed border-slate-300 p-8 text-center text-lg text-slate-700">
              작업을 고르고 <strong>변환하기</strong>를 누르면 여기에 결과가 나와요.
            </p>
          )}
        </div>
      </div>

      <ExportBar results={allResults} filename={upload.filename} />
    </div>
  );
}
