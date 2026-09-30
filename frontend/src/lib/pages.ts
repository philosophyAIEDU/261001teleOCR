/** "1-3, 5" 같은 쪽 범위 입력을 0부터 시작하는 쪽 번호 목록으로 바꿉니다. */
export function parsePageRange(input: string, pageCount: number): number[] {
  const result = new Set<number>();
  for (const part of input.split(/[,\s]+/)) {
    if (!part) continue;
    const match = /^(\d+)(?:-(\d+))?$/.exec(part);
    if (!match) continue;
    const start = Number(match[1]);
    const end = match[2] ? Number(match[2]) : start;
    for (let p = Math.min(start, end); p <= Math.max(start, end); p += 1) {
      if (p >= 1 && p <= pageCount) result.add(p - 1);
    }
  }
  return [...result].sort((a, b) => a - b);
}
