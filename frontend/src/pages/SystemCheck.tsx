import { useCallback, useEffect, useState } from "react";
import { api, errorMessage } from "../api/client";
import ErrorAlert from "../components/ErrorAlert";
import { taskName } from "../lib/tasks";
import type { SampleInfo, SystemStatus } from "../types";

interface SampleRun {
  sample: SampleInfo;
  status: "waiting" | "running" | "done" | "error";
  seconds?: number;
  preview?: string;
  error?: string;
}

function formatBytes(bytes: number): string {
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(2)}GB`;
  return `${(bytes / 1024 ** 2).toFixed(0)}MB`;
}

const DEVICE_LABEL: Record<string, string> = {
  cuda: "NVIDIA GPU",
  mps: "Apple Silicon",
  cpu: "CPU 전용",
};

export default function SystemCheck() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runs, setRuns] = useState<SampleRun[]>([]);
  const [testing, setTesting] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setStatus(await api.getSystem());
      setError(null);
    } catch (e) {
      setError(errorMessage(e));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // 모델을 내려받거나 불러오는 동안에는 2초마다 상태를 새로 확인합니다.
  const polling = Boolean(status?.model.loading || status?.download.active || testing);
  useEffect(() => {
    if (!polling) return;
    const timer = setInterval(() => void refresh(), 2000);
    return () => clearInterval(timer);
  }, [polling, refresh]);

  async function prepareModel() {
    try {
      await api.loadModel();
      await refresh();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  async function runSamples() {
    setTesting(true);
    setError(null);
    try {
      const samples = (await api.getSamples()).filter((s) => s.id !== "korean_text");
      const list: SampleRun[] = samples.map((sample) => ({ sample, status: "waiting" }));
      setRuns(list);
      for (const [index, item] of list.entries()) {
        setRuns((prev) => prev.map((r, i) => (i === index ? { ...r, status: "running" } : r)));
        try {
          const upload = await api.useSample(item.sample.id);
          const res = await api.convert(upload.upload_id, 0, item.sample.task);
          await api.deleteUpload(upload.upload_id);
          setRuns((prev) =>
            prev.map((r, i) =>
              i === index ? { ...r, status: "done", seconds: res.elapsed_seconds, preview: res.content.slice(0, 160) } : r,
            ),
          );
        } catch (e) {
          setRuns((prev) => prev.map((r, i) => (i === index ? { ...r, status: "error", error: errorMessage(e) } : r)));
          break;
        }
      }
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setTesting(false);
      void refresh();
    }
  }

  const device = status?.device;
  const model = status?.model;
  const download = status?.download;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-3xl font-bold">시스템 점검</h1>
      <ErrorAlert message={error} />
      {!status ? (
        <p role="status">상태를 확인하고 있어요…</p>
      ) : (
        <>
          <section aria-labelledby="device-title" className="card">
            <h2 id="device-title" className="text-xl font-bold">
              💻 실행 장치
            </h2>
            <dl className="mt-3 grid grid-cols-[max-content_1fr] gap-x-6 gap-y-2">
              <dt className="font-bold">종류</dt>
              <dd>{device ? DEVICE_LABEL[device.kind] : "-"}</dd>
              <dt className="font-bold">이름</dt>
              <dd>{device?.name}</dd>
              <dt className="font-bold">계산 정밀도</dt>
              <dd>{device?.dtype}</dd>
            </dl>
            <p className={`mt-4 rounded-xl p-3 ${device?.kind === "cpu" ? "border-2 border-amber-400 bg-amber-50 text-amber-950" : "bg-emerald-50 text-emerald-950"}`}>
              {device?.kind === "cpu" ? "🐢 " : "⚡ "}
              {device?.speed_hint}
            </p>
            {device && !device.torch_available && (
              <p className="mt-3 rounded-xl border-2 border-red-300 bg-red-50 p-3 text-red-900">
                AI 실행 프로그램(PyTorch)이 설치되지 않았어요. 설치 스크립트(install)를 다시 실행해 주세요.
              </p>
            )}
          </section>

          <section aria-labelledby="model-title" className="card">
            <h2 id="model-title" className="text-xl font-bold">
              🧠 AI 모델
            </h2>
            <dl className="mt-3 grid grid-cols-[max-content_1fr] gap-x-6 gap-y-2">
              <dt className="font-bold">상태</dt>
              <dd>
                {model?.loaded
                  ? "✅ 준비 완료 (메모리에 올라가 있어요)"
                  : model?.loading
                    ? "⏳ 준비 중…"
                    : model?.downloaded
                      ? "💾 내려받음 (첫 변환 때 자동으로 불러와요)"
                      : "⬇️ 아직 내려받지 않았어요 (수 GB, 처음 한 번만 인터넷 필요)"}
              </dd>
              <dt className="font-bold">사용 중인 모델 ID</dt>
              <dd className="break-all font-mono">{model?.model_id ?? "-"}</dd>
              <dt className="font-bold">설정된 모델 ID</dt>
              <dd className="break-all font-mono">
                {model?.configured_id}
                {model?.fallback_ids.length ? ` (대체: ${model.fallback_ids.join(", ")})` : ""}
              </dd>
              <dt className="font-bold">버전(revision)</dt>
              <dd className="break-all font-mono">
                {model?.revision ?? "-"}
                {model?.configured_revision ? " (고정됨)" : " (최신 버전 사용 중 · config.yaml 에서 고정 권장)"}
              </dd>
            </dl>

            {download?.active && (
              <div className="mt-4">
                <p className="font-bold">
                  모델 내려받는 중… {formatBytes(download.downloaded_bytes)}
                  {download.total_bytes ? ` / ${formatBytes(download.total_bytes)}` : ""}
                </p>
                <div
                  className="mt-2 h-5 w-full overflow-hidden rounded-full bg-slate-200"
                  role="progressbar"
                  aria-label="모델 내려받기 진행률"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={Math.round(download.percent ?? 0)}
                >
                  <div className="h-full bg-brand-600 transition-all" style={{ width: `${download.percent ?? 5}%` }} />
                </div>
              </div>
            )}

            {model?.error && (
              <div className="mt-4">
                <ErrorAlert message={model.error} />
                {model.attempts.length > 0 && (
                  <details className="mt-2">
                    <summary className="cursor-pointer">자세한 오류 내용 (도움을 요청할 때 보여 주세요)</summary>
                    <ul className="mt-2 list-disc pl-6 font-mono">
                      {model.attempts.map((a) => (
                        <li key={a.model_id} className="break-all">
                          {a.model_id}: {a.error}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            )}

            <div className="mt-4 flex flex-wrap gap-2">
              {!model?.loaded && (
                <button type="button" className="btn-primary" onClick={() => void prepareModel()} disabled={model?.loading}>
                  {model?.downloaded ? "모델 불러오기" : "모델 내려받고 준비하기"}
                </button>
              )}
              <button type="button" className="btn-secondary" onClick={() => void refresh()}>
                🔄 상태 새로고침
              </button>
            </div>
          </section>

          <section aria-labelledby="sample-test-title" className="card">
            <h2 id="sample-test-title" className="text-xl font-bold">
              🧪 샘플로 테스트하기
            </h2>
            <p className="mt-1 text-slate-700">
              함께 들어 있는 영어 지문·표·수식 사진으로 변환이 잘 되는지 확인해요. 모델이 준비되지 않았다면 먼저 내려받아요.
            </p>
            <button type="button" className="btn-primary mt-3" onClick={() => void runSamples()} disabled={testing}>
              {testing ? "테스트 중…" : "샘플로 테스트하기"}
            </button>
            {runs.length > 0 && (
              <ul className="mt-4 flex flex-col gap-2" aria-live="polite">
                {runs.map((run) => (
                  <li key={run.sample.id} className="rounded-xl border border-slate-200 p-3">
                    <p className="font-bold">
                      {run.status === "done" ? "✅" : run.status === "error" ? "❌" : run.status === "running" ? "⏳" : "⏸️"}{" "}
                      {run.sample.title} ({taskName(run.sample.task)})
                      {run.seconds !== undefined ? ` · ${run.seconds.toFixed(1)}초` : ""}
                    </p>
                    {run.preview && <pre className="mt-1 whitespace-pre-wrap break-all font-mono">{run.preview}</pre>}
                    {run.error && <p className="mt-1 text-red-800">{run.error}</p>}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
