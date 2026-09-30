/** HTML 표 ↔ 편집 가능한 칸 모델 변환 (병합 칸 rowspan/colspan 유지) */

export interface CellModel {
  text: string;
  rowSpan: number;
  colSpan: number;
}

export type TableModel = CellModel[][];

function span(value: string | null): number {
  const n = Number.parseInt(value ?? "1", 10);
  return Number.isFinite(n) && n > 0 ? n : 1;
}

export function parseHtmlTable(html: string): TableModel | null {
  const doc = new DOMParser().parseFromString(html, "text/html");
  const table = doc.querySelector("table");
  if (!table) return null;
  const rows: TableModel = [];
  table.querySelectorAll("tr").forEach((tr) => {
    if (tr.closest("table") !== table) return; // 표 안의 표는 무시
    const cells: CellModel[] = [];
    tr.querySelectorAll("td, th").forEach((cell) => {
      if (cell.parentElement !== tr) return;
      cells.push({
        text: (cell.textContent ?? "").trim(),
        rowSpan: span(cell.getAttribute("rowspan")),
        colSpan: span(cell.getAttribute("colspan")),
      });
    });
    rows.push(cells);
  });
  return rows;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function serializeTable(model: TableModel): string {
  const body = model
    .map((row) => {
      const cells = row
        .map((cell) => {
          const attrs =
            (cell.rowSpan > 1 ? ` rowspan="${cell.rowSpan}"` : "") +
            (cell.colSpan > 1 ? ` colspan="${cell.colSpan}"` : "");
          return `<td${attrs}>${escapeHtml(cell.text)}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");
  return `<table>${body}</table>`;
}

export function updateCell(model: TableModel, row: number, col: number, text: string): TableModel {
  return model.map((cells, r) =>
    r === row ? cells.map((cell, c) => (c === col ? { ...cell, text } : cell)) : cells,
  );
}

/** 표 끝에 빈 행을 하나 추가합니다(열 수는 가장 넓은 행 기준). */
export function addRow(model: TableModel): TableModel {
  const width = Math.max(1, ...model.map((row) => row.reduce((sum, c) => sum + c.colSpan, 0)));
  return [...model, Array.from({ length: width }, () => ({ text: "", rowSpan: 1, colSpan: 1 }))];
}

/** 탭으로 구분된 텍스트(엑셀·한글 표에 붙여 넣기 좋은 형식)로 바꿉니다. */
export function tableToTsv(model: TableModel): string {
  return model.map((row) => row.map((c) => c.text.replace(/[\t\n]/g, " ")).join("\t")).join("\n");
}
