import { useEffect, useState } from "react";
import type { Progress } from "../store/convertStore";

export default function InferenceProgress({ progress }: { progress: Progress }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const seconds = Math.max(0, Math.floor((now - progress.startedAt) / 1000));
  const percent = progress.total ? Math.round((progress.done / progress.total) * 100) : 0;

  return (
    <div role="status" aria-live="polite" className="rounded-2xl border-2 border-brand-600 bg-brand-50 p-5">
      <div className="flex items-center gap-3">
        <span className="spinner" aria-hidden="true" />
        <p className="text-lg font-bold">
          AI가 변환하고 있어요… ({progress.done}/{progress.total}쪽 완료 · {seconds}초 경과)
        </p>
      </div>
      <p className="mt-2 text-slate-800">
        PC 사양에 따라 수십 초 이상 걸릴 수 있어요. 창을 닫지 말고 잠시 기다려 주세요.
      </p>
      {progress.total > 1 && (
        <div className="mt-3 h-4 w-full overflow-hidden rounded-full bg-white" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} aria-label="전체 진행률">
          <div className="h-full bg-brand-600 transition-all" style={{ width: `${percent}%` }} />
        </div>
      )}
    </div>
  );
}
