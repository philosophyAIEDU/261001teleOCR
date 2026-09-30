import type { LayoutBlock } from "../../types";
import { blockColor } from "../LayoutOverlay";

interface Props {
  blocks: LayoutBlock[];
  onSelect: (block: LayoutBlock) => void;
}

export default function LayoutResult({ blocks, onSelect }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <p className="font-bold">왼쪽 사진에 찾은 영역 {blocks.length}개를 표시했어요.</p>
      <p className="text-slate-700">영역을 누르면 그 부분만 잘라서 알맞은 작업(글자·표·수식)으로 다시 변환할 수 있어요.</p>
      <ol className="flex flex-col gap-2">
        {blocks.map((block, index) => (
          <li key={index}>
            <button
              type="button"
              className="flex w-full items-center gap-3 rounded-xl border border-slate-300 bg-white p-3 text-left hover:border-brand-600"
              onClick={() => onSelect(block)}
            >
              <span className="h-5 w-5 shrink-0 rounded" style={{ backgroundColor: blockColor(block.type) }} aria-hidden="true" />
              <span className="font-bold">
                {index + 1}. {block.label}
              </span>
              <span className="text-slate-700">({block.type}{block.angle ? `, ${block.angle}° 회전` : ""})</span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
