import type { LayoutBlock } from "../types";

// 영역 종류별 색상(배경이 어떤 색이어도 잘 보이도록 진한 색 사용)
const COLORS: Record<string, string> = {
  title: "#b91c1c",
  text: "#1d4ed8",
  table: "#047857",
  equation: "#7e22ce",
  image: "#c2410c",
  code: "#0f766e",
  seal: "#be123c",
  char: "#a16207",
};

export function blockColor(type: string): string {
  return COLORS[type] ?? "#475569";
}

interface Props {
  blocks: LayoutBlock[];
  onSelect?: (block: LayoutBlock) => void;
}

/** 원본 이미지 위에 레이아웃 영역(사각형·다각형)을 겹쳐 그립니다. 좌표는 0~1 정규화 값입니다. */
export default function LayoutOverlay({ blocks, onSelect }: Props) {
  return (
    <div className="pointer-events-none absolute inset-0" data-testid="layout-overlay">
      <svg viewBox="0 0 1 1" preserveAspectRatio="none" className="absolute inset-0 h-full w-full" aria-hidden="true">
        {blocks.map((block, index) => (
          <polygon
            key={index}
            points={block.points.map((p) => `${p[0]},${p[1]}`).join(" ")}
            fill={`${blockColor(block.type)}22`}
            stroke={blockColor(block.type)}
            strokeWidth={3}
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </svg>
      {blocks.map((block, index) => (
        <button
          key={index}
          type="button"
          className={`pointer-events-auto absolute rounded px-2 py-0.5 font-bold text-white ${block.bbox[1] < 0.06 ? "" : "-translate-y-full"}`}
          style={{
            left: `${block.bbox[0] * 100}%`,
            top: `${block.bbox[1] * 100}%`,
            backgroundColor: blockColor(block.type),
          }}
          onClick={() => onSelect?.(block)}
          title="이 영역만 잘라서 다시 변환하기"
        >
          {index + 1}. {block.label}
        </button>
      ))}
    </div>
  );
}
