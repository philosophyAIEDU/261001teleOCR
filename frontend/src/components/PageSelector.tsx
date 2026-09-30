import { useState } from "react";
import { parsePageRange } from "../lib/pages";

interface Props {
  pageCount: number;
  selected: number[];
  current: number;
  onToggle: (page: number) => void;
  onSelect: (pages: number[]) => void;
  onView: (page: number) => void;
  disabled?: boolean;
}

export default function PageSelector({ pageCount, selected, current, onToggle, onSelect, onView, disabled = false }: Props) {
  const [range, setRange] = useState("");
  const all = Array.from({ length: pageCount }, (_, i) => i);

  return (
    <fieldset disabled={disabled} className="rounded-2xl border border-slate-300 bg-white p-4">
      <legend className="px-1 text-lg font-bold">
        변환할 쪽 선택 <span className="font-normal text-slate-700">({selected.length}/{pageCount}쪽 선택됨)</span>
      </legend>
      <div className="mb-3 flex flex-wrap items-end gap-2">
        <button type="button" className="btn-secondary" onClick={() => onSelect(all)}>
          전체 선택
        </button>
        <button type="button" className="btn-secondary" onClick={() => onSelect([])}>
          전체 해제
        </button>
        <label className="flex flex-col">
          <span>쪽 범위 입력 (예: 1-3, 5)</span>
          <span className="flex gap-2">
            <input className="input w-40" value={range} onChange={(e) => setRange(e.target.value)} />
            <button type="button" className="btn-secondary" onClick={() => onSelect(parsePageRange(range, pageCount))}>
              적용
            </button>
          </span>
        </label>
      </div>
      <ul className="flex max-h-48 flex-wrap gap-2 overflow-y-auto" aria-label="쪽 목록">
        {all.map((page) => (
          <li key={page} className={`flex items-center rounded-lg border ${page === current ? "border-brand-600 bg-brand-50" : "border-slate-300"}`}>
            <label className="flex cursor-pointer items-center gap-2 px-3 py-2">
              <input type="checkbox" className="h-5 w-5" checked={selected.includes(page)} onChange={() => onToggle(page)} />
              {page + 1}쪽
            </label>
            <button
              type="button"
              className="border-l border-slate-300 px-3 py-2 text-brand-700 hover:bg-slate-100"
              onClick={() => onView(page)}
              aria-label={`${page + 1}쪽 보기`}
              aria-current={page === current ? "page" : undefined}
            >
              보기
            </button>
          </li>
        ))}
      </ul>
    </fieldset>
  );
}
