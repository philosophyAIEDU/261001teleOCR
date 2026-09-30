import type { LayoutBlock, PageResult } from "../../types";
import CopyButton from "../CopyButton";
import FormulaResult from "./FormulaResult";
import LayoutResult from "./LayoutResult";
import TableResult from "./TableResult";
import TextResult from "./TextResult";

interface Props {
  result: PageResult;
  onChange: (content: string) => void;
  onSelectBlock: (block: LayoutBlock) => void;
}

export default function ResultView({ result, onChange, onSelectBlock }: Props) {
  let body;
  switch (result.resultFormat) {
    case "html_table":
      body = <TableResult value={result.content} onChange={onChange} />;
      break;
    case "latex":
      body = <FormulaResult value={result.content} onChange={onChange} />;
      break;
    case "code":
      body = <TextResult value={result.content} onChange={onChange} mono label="코드" />;
      break;
    case "layout":
      body = <LayoutResult blocks={result.blocks ?? []} onSelect={onSelectBlock} />;
      break;
    default:
      body = <TextResult value={result.content} onChange={onChange} label={result.task === "full_page" ? "전체 페이지 결과(Markdown)" : "글자"} />;
  }

  return (
    <section aria-label="변환 결과" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-xl font-bold">
          {result.page + 1}쪽 · {result.taskName}
          {result.cropped ? " (자른 영역)" : ""}
        </h2>
        <span className="rounded-full bg-slate-200 px-3 py-1">{result.elapsedSeconds.toFixed(1)}초</span>
      </div>
      {!result.parsed && (
        <p role="note" className="rounded-xl border-2 border-amber-400 bg-amber-50 p-3 text-amber-950">
          결과 형식을 해석하지 못해 AI가 출력한 원문을 그대로 보여 드려요. 필요한 부분을 직접 고쳐 쓰세요.
        </p>
      )}
      <p className="rounded-xl bg-amber-50 p-3 text-amber-950">
        ⚠️ AI 결과에는 오류가 있을 수 있어요. 수업 자료로 쓰기 전에 꼭 원본과 비교해 주세요.
      </p>
      {body}
      <details className="rounded-xl border border-slate-300 bg-white p-3">
        <summary className="cursor-pointer font-medium">AI 원본 출력 보기</summary>
        <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-all font-mono">{result.raw}</pre>
        <CopyButton text={result.raw} label="원본 복사" />
      </details>
    </section>
  );
}
