/** "$$...$$" 에서 LaTeX 원문만 꺼냅니다. (한글·Word 수식 편집기에 붙여 넣을 때 사용) */
export function stripDisplayMath(content: string): string {
  const text = content.trim();
  if (text.startsWith("$$") && text.endsWith("$$") && text.length >= 4) {
    return text.slice(2, -2).trim();
  }
  return text;
}

export function wrapDisplayMath(latex: string): string {
  const inner = latex.trim();
  return inner ? `$$${inner}$$` : "";
}
