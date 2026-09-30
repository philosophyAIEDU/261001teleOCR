import { addRow, parseHtmlTable, serializeTable, tableToTsv, updateCell } from "../lib/htmlTable";
import { stripDisplayMath, wrapDisplayMath } from "../lib/latex";
import { parsePageRange } from "../lib/pages";
import { splitSections } from "../pages/Guide";

const MERGED = '<table><tr><td rowspan="2">Name</td><td colspan="2">Score</td></tr><tr><td>Math</td><td>Eng</td></tr></table>';

describe("htmlTable", () => {
  it("parses spans and serializes back", () => {
    const model = parseHtmlTable(MERGED);
    expect(model?.[0][0]).toEqual({ text: "Name", rowSpan: 2, colSpan: 1 });
    expect(model?.[0][1].colSpan).toBe(2);
    expect(serializeTable(model!)).toBe(MERGED);
  });

  it("escapes edited text and updates one cell", () => {
    const model = updateCell(parseHtmlTable(MERGED)!, 1, 0, "a<b & c");
    expect(serializeTable(model)).toContain("<td>a&lt;b &amp; c</td>");
    expect(model[0][0].text).toBe("Name");
  });

  it("returns null for non-table input", () => {
    expect(parseHtmlTable("just text")).toBeNull();
  });

  it("adds a row with full width and exports TSV", () => {
    const model = addRow(parseHtmlTable(MERGED)!);
    expect(model).toHaveLength(3);
    expect(model[2]).toHaveLength(3);
    expect(tableToTsv(parseHtmlTable("<table><tr><td>a\tb</td><td>c</td></tr></table>")!)).toBe("a b\tc");
  });
});

describe("latex", () => {
  it("strips and wraps display math", () => {
    expect(stripDisplayMath("$$x^2$$")).toBe("x^2");
    expect(stripDisplayMath(" y ")).toBe("y");
    expect(wrapDisplayMath(" x ")).toBe("$$x$$");
    expect(wrapDisplayMath("  ")).toBe("");
  });
});

describe("parsePageRange", () => {
  it("parses ranges and ignores out-of-range pages", () => {
    expect(parsePageRange("1-3, 5 9 x 3-2", 6)).toEqual([0, 1, 2, 4]);
    expect(parsePageRange("", 3)).toEqual([]);
  });
});

describe("guide sections", () => {
  it("splits markdown into intro and cards", () => {
    const { intro, sections } = splitSections("# 제목\n소개\n## A\n내용\n## B\n내용2");
    expect(intro).toBe("# 제목\n소개");
    expect(sections).toEqual(["## A\n내용", "## B\n내용2"]);
    expect(splitSections("## Only").sections).toEqual(["## Only"]);
  });
});
