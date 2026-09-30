import { useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent } from "react";
import type { CropBox } from "../types";

interface Props {
  value: CropBox | null;
  onChange: (crop: CropBox | null) => void;
}

const MIN_SIZE = 0.02;
const STEP = 0.02;

const clamp = (v: number, min = 0, max = 1) => Math.min(max, Math.max(min, v));

/**
 * 이미지 위에서 끌어서 사각형 영역을 고르는 도구.
 * - 마우스·손가락(태블릿)·펜: 누른 채로 끌기
 * - 키보드: Enter 로 가운데 영역 만들기, 방향키로 이동, Shift+방향키로 크기 조절, Esc 로 지우기
 * 좌표는 이미지 크기에 상관없이 0~1 로 정규화해 서버에 보냅니다.
 */
export default function CropTool({ value, onChange }: Props) {
  const areaRef = useRef<HTMLDivElement>(null);
  const [start, setStart] = useState<{ x: number; y: number } | null>(null);

  function point(event: PointerEvent<HTMLDivElement>) {
    const rect = areaRef.current?.getBoundingClientRect();
    if (!rect || rect.width === 0 || rect.height === 0) return { x: 0, y: 0 };
    return { x: clamp((event.clientX - rect.left) / rect.width), y: clamp((event.clientY - rect.top) / rect.height) };
  }

  function onPointerDown(event: PointerEvent<HTMLDivElement>) {
    event.preventDefault();
    areaRef.current?.setPointerCapture?.(event.pointerId);
    const p = point(event);
    setStart(p);
    onChange(null);
  }

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!start) return;
    const p = point(event);
    onChange({
      x: Math.min(start.x, p.x),
      y: Math.min(start.y, p.y),
      width: Math.abs(p.x - start.x),
      height: Math.abs(p.y - start.y),
    });
  }

  function onPointerUp() {
    setStart(null);
    if (value && (value.width < MIN_SIZE || value.height < MIN_SIZE)) onChange(null);
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      onChange(null);
      return;
    }
    if (event.key === "Enter" && !value) {
      event.preventDefault();
      onChange({ x: 0.25, y: 0.25, width: 0.5, height: 0.5 });
      return;
    }
    if (!value) return;
    const deltas: Record<string, [number, number]> = {
      ArrowLeft: [-STEP, 0],
      ArrowRight: [STEP, 0],
      ArrowUp: [0, -STEP],
      ArrowDown: [0, STEP],
    };
    const delta = deltas[event.key];
    if (!delta) return;
    event.preventDefault();
    const [dx, dy] = delta;
    if (event.shiftKey) {
      const width = clamp(value.width + dx, MIN_SIZE, 1 - value.x);
      const height = clamp(value.height + dy, MIN_SIZE, 1 - value.y);
      onChange({ ...value, width, height });
    } else {
      onChange({
        ...value,
        x: clamp(value.x + dx, 0, 1 - value.width),
        y: clamp(value.y + dy, 0, 1 - value.height),
      });
    }
  }

  return (
    <div
      ref={areaRef}
      data-testid="crop-area"
      role="application"
      aria-label="자를 영역 선택: 끌어서 사각형을 그리세요. 키보드는 Enter로 영역 만들기, 방향키로 이동, Shift+방향키로 크기 조절"
      tabIndex={0}
      className="absolute inset-0 cursor-crosshair touch-none bg-slate-900/10 focus:outline-none focus-visible:ring-4 focus-visible:ring-amber-400"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onKeyDown={onKeyDown}
    >
      {value && (
        <div
          data-testid="crop-selection"
          className="pointer-events-none absolute border-4 border-amber-400 bg-amber-200/20 shadow-[0_0_0_9999px_rgba(15,23,42,0.45)]"
          style={{
            left: `${value.x * 100}%`,
            top: `${value.y * 100}%`,
            width: `${value.width * 100}%`,
            height: `${value.height * 100}%`,
          }}
        />
      )}
    </div>
  );
}
