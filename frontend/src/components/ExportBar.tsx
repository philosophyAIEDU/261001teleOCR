import { useState } from "react";
import { api, errorMessage } from "../api/client";
import { copyText, saveBlob } from "../lib/clipboard";
import type { ExportItem, PageResult } from "../types";

interface Props {
  results: PageResult[];
  filename: string;
}

function toItems(results: PageResult[], filename: string): ExportItem[] {
  return results
    .filter((r) => r.resultFormat !== "layout")
    .map((r) => ({
      result_format: r.resultFormat,
      content: r.content,
      title: results.length > 1 ? `${filename} - ${r.page + 1}쪽 (${r.taskName})` : null,
    }));
}

export default function ExportBar({ results, filename }: Props) {
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const items = toItems(results, filename);
  const hasTable = items.some((i) => i.result_format === "html_table");
  const base = filename.replace(/\.[^.]+$/, "") || "teleocr";

  if (items.length === 0) return null;

  async function download(format: "md" | "docx" | "xlsx") {
    setBusy(true);
    setMessage(null);
    try {
      const blob = await api.exportFile(format, items, `${base}-변환`);
      saveBlob(blob, `${base}-변환.${format}`);
      setMessage(`${format.toUpperCase()} 파일을 저장했어요. 다운로드 폴더를 확인해 주세요.`);
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }

  async function copyAll() {
    const text = items.map((i) => i.content).join("\n\n");
    setMessage((await copyText(text)) ? "모든 결과를 복사했어요." : "복사하지 못했어요.");
  }

  return (
    <section aria-labelledby="export-title" className="rounded-2xl border border-slate-300 bg-white p-4">
      <h2 id="export-title" className="mb-3 text-lg font-bold">
        내보내기 ({items.length}건)
      </h2>
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn-secondary" onClick={copyAll} disabled={busy}>
          📋 클립보드에 복사
        </button>
        <button type="button" className="btn-secondary" onClick={() => download("md")} disabled={busy}>
          📝 Markdown(.md)
        </button>
        <button type="button" className="btn-secondary" onClick={() => download("docx")} disabled={busy}>
          📄 Word(.docx)
        </button>
        {hasTable && (
          <button type="button" className="btn-secondary" onClick={() => download("xlsx")} disabled={busy}>
            📊 Excel(.xlsx)
          </button>
        )}
      </div>
      {message && (
        <p role="status" className="mt-3">
          {message}
        </p>
      )}
    </section>
  );
}
