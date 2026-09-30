import { useHistoryStore } from "../store/historyStore";
import CopyButton from "./CopyButton";

function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString("ko-KR", { dateStyle: "short", timeStyle: "short" });
}

export default function HistoryList() {
  const { entries, enabled, remove, clear, setEnabled } = useHistoryStore();

  return (
    <section aria-labelledby="history-title" className="rounded-2xl border border-slate-300 bg-white p-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 id="history-title" className="text-xl font-bold">
          최근 변환 기록
        </h2>
        <label className="flex items-center gap-2">
          <input type="checkbox" className="h-5 w-5" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          기록 남기기
        </label>
        {entries.length > 0 && (
          <button type="button" className="btn-ghost ml-auto" onClick={() => clear()}>
            🗑️ 기록 전체 삭제
          </button>
        )}
      </div>
      <p className="mt-1 text-slate-700">
        기록은 이 컴퓨터의 브라우저에만 저장돼요(최근 30건). 여러 사람이 쓰는 컴퓨터라면 사용 후 지워 주세요.
      </p>
      {entries.length === 0 ? (
        <p className="mt-3 text-slate-700">아직 기록이 없어요.</p>
      ) : (
        <ul className="mt-3 flex flex-col gap-2">
          {entries.map((entry) => (
            <li key={entry.id} className="rounded-xl border border-slate-200 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <strong>{entry.filename || "(이름 없음)"}</strong>
                <span>
                  {entry.page + 1}쪽 · {entry.taskName}
                </span>
                <span className="text-slate-700">{formatDate(entry.createdAt)}</span>
                <span className="ml-auto flex gap-2">
                  <CopyButton text={entry.content} label="결과 복사" />
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => remove(entry.id)}
                    aria-label={`${entry.filename} ${entry.page + 1}쪽 기록 삭제`}
                  >
                    삭제
                  </button>
                </span>
              </div>
              <p className="mt-1 line-clamp-2 break-all text-slate-700">{entry.content.slice(0, 200)}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
