import { useState } from "react";
import { copyText } from "../lib/clipboard";

interface Props {
  text: string;
  label?: string;
  className?: string;
}

export default function CopyButton({ text, label = "복사하기", className = "btn-secondary" }: Props) {
  const [state, setState] = useState<"idle" | "done" | "fail">("idle");

  async function handleClick() {
    const ok = await copyText(text);
    setState(ok ? "done" : "fail");
    setTimeout(() => setState("idle"), 2000);
  }

  return (
    <button type="button" className={className} onClick={handleClick}>
      <span aria-live="polite">
        {state === "done" ? "✓ 복사했어요" : state === "fail" ? "복사하지 못했어요" : `📋 ${label}`}
      </span>
    </button>
  );
}
