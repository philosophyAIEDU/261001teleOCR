import katex from "katex";
import { useMemo } from "react";
import { stripDisplayMath, wrapDisplayMath } from "../../lib/latex";
import CopyButton from "../CopyButton";

interface Props {
  value: string;
  onChange: (value: string) => void;
}

export default function FormulaResult({ value, onChange }: Props) {
  const latex = stripDisplayMath(value);
  const html = useMemo(
    () => katex.renderToString(latex, { displayMode: true, throwOnError: false, output: "htmlAndMathml" }),
    [latex],
  );
  return (
    <div className="flex flex-col gap-3">
      <div className="font-bold">미리보기</div>
      <div
        data-testid="katex-preview"
        className="overflow-x-auto rounded-xl border border-slate-300 bg-white p-4 text-xl"
        dangerouslySetInnerHTML={{ __html: html }}
      />
      <label className="flex flex-col gap-2">
        <span className="font-bold">LaTeX 원문 (직접 고칠 수 있어요)</span>
        <textarea
          className="input w-full font-mono"
          rows={Math.max(3, latex.split("\n").length + 1)}
          value={latex}
          spellCheck={false}
          onChange={(e) => onChange(wrapDisplayMath(e.target.value))}
        />
      </label>
      <div className="flex flex-wrap gap-2">
        <CopyButton text={latex} label="LaTeX 원문 복사" />
        <CopyButton text={value} label="$$ 포함 복사" />
      </div>
      <p className="text-slate-700">
        한글(HWP)은 수식 편집기의 LaTeX 입력, Word 는 [삽입 → 수식 → LaTeX], 구글 문서는 수식 도구에 붙여 넣어 쓰세요.
      </p>
    </div>
  );
}
