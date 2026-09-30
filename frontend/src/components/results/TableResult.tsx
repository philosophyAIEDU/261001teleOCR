import { useMemo } from "react";
import { addRow, parseHtmlTable, serializeTable, tableToTsv, updateCell } from "../../lib/htmlTable";
import CopyButton from "../CopyButton";

interface Props {
  value: string;
  onChange: (value: string) => void;
}

/** 표 결과: 칸마다 글자를 고칠 수 있는 표(병합 칸 유지) */
export default function TableResult({ value, onChange }: Props) {
  const model = useMemo(() => parseHtmlTable(value), [value]);
  if (!model) {
    return <p>표를 표시할 수 없어요. 아래 원본 출력을 확인해 주세요.</p>;
  }
  return (
    <div className="flex flex-col gap-3">
      <p className="font-bold">칸을 눌러 글자를 고칠 수 있어요.</p>
      <div className="overflow-auto">
        <table className="result-table">
          <tbody>
            {model.map((row, r) => (
              <tr key={r}>
                {row.map((cell, c) => (
                  <td key={c} rowSpan={cell.rowSpan} colSpan={cell.colSpan}>
                    <input
                      className="cell-input"
                      value={cell.text}
                      aria-label={`${r + 1}행 ${c + 1}번째 칸`}
                      onChange={(e) => onChange(serializeTable(updateCell(model, r, c, e.target.value)))}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap gap-2">
        <CopyButton text={tableToTsv(model)} label="표 복사 (엑셀·한글에 붙여넣기)" />
        <CopyButton text={value} label="HTML 복사" />
        <button type="button" className="btn-secondary" onClick={() => onChange(serializeTable(addRow(model)))}>
          ➕ 행 추가
        </button>
      </div>
    </div>
  );
}
