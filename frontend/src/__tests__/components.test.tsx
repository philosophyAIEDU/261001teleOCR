import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import CopyButton from "../components/CopyButton";
import CropTool from "../components/CropTool";
import TaskPicker from "../components/TaskPicker";
import FormulaResult from "../components/results/FormulaResult";
import ResultView from "../components/results/ResultView";
import TableResult from "../components/results/TableResult";
import TextResult from "../components/results/TextResult";
import type { CropBox, PageResult, TaskId } from "../types";

function mockClipboard() {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  return writeText;
}

describe("TaskPicker", () => {
  it("shows all 8 task cards and selects one", async () => {
    const onChange = vi.fn();
    render(<TaskPicker value="text" onChange={onChange} />);
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(8);
    expect(screen.getByRole("radio", { name: /글자 뽑기/ })).toBeChecked();
    await userEvent.click(screen.getByText("표 만들기"));
    expect(onChange).toHaveBeenCalledWith("table");
    expect(screen.getByText("도장 인식")).toBeInTheDocument();
  });

  it("supports keyboard selection with arrow keys", async () => {
    function Harness() {
      const [task, setTask] = useState<TaskId>("text");
      return <TaskPicker value={task} onChange={setTask} />;
    }
    render(<Harness />);
    screen.getByRole("radio", { name: /글자 뽑기/ }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("radio", { name: /표 만들기/ })).toBeChecked();
  });

  it("can be disabled while converting", () => {
    render(<TaskPicker value="text" onChange={vi.fn()} disabled />);
    expect(screen.getByRole("radio", { name: /수식 변환/ })).toBeDisabled();
  });
});

describe("CopyButton", () => {
  it("copies text and shows feedback", async () => {
    const writeText = mockClipboard();
    render(<CopyButton text="hello" label="글자 복사" />);
    await userEvent.click(screen.getByRole("button", { name: /글자 복사/ }));
    expect(writeText).toHaveBeenCalledWith("hello");
    expect(await screen.findByText("✓ 복사했어요")).toBeInTheDocument();
  });

  it("shows failure message when copy fails", async () => {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
      configurable: true,
    });
    document.execCommand = vi.fn().mockReturnValue(false);
    render(<CopyButton text="x" />);
    await userEvent.click(screen.getByRole("button"));
    expect(await screen.findByText("복사하지 못했어요")).toBeInTheDocument();
  });
});

describe("result editing", () => {
  it("edits plain text results", async () => {
    function Harness() {
      const [value, setValue] = useState("Helo");
      return (
        <>
          <TextResult value={value} onChange={setValue} label="글자" />
          <output data-testid="value">{value}</output>
        </>
      );
    }
    render(<Harness />);
    const box = screen.getByRole("textbox", { name: /글자/ });
    await userEvent.clear(box);
    await userEvent.type(box, "Hello");
    expect(screen.getByTestId("value")).toHaveTextContent("Hello");
  });

  it("edits a table cell and keeps merged cells", async () => {
    function Harness() {
      const [value, setValue] = useState('<table><tr><td colspan="2">점수</td></tr><tr><td>민수</td><td>90</td></tr></table>');
      return (
        <>
          <TableResult value={value} onChange={setValue} />
          <output data-testid="html">{value}</output>
        </>
      );
    }
    render(<Harness />);
    const cell = screen.getByRole("textbox", { name: "2행 2번째 칸" });
    await userEvent.clear(cell);
    await userEvent.type(cell, "95");
    expect(screen.getByTestId("html").textContent).toBe(
      '<table><tr><td colspan="2">점수</td></tr><tr><td>민수</td><td>95</td></tr></table>',
    );
    await userEvent.click(screen.getByRole("button", { name: /행 추가/ }));
    expect(screen.getByRole("textbox", { name: "3행 1번째 칸" })).toBeInTheDocument();
  });

  it("copies the table as TSV for spreadsheets", async () => {
    const writeText = mockClipboard();
    render(<TableResult value="<table><tr><td>a</td><td>b</td></tr></table>" onChange={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /표 복사/ }));
    expect(writeText).toHaveBeenCalledWith("a\tb");
  });

  it("renders a KaTeX preview, edits LaTeX, and copies raw LaTeX", async () => {
    const writeText = mockClipboard();
    const onChange = vi.fn();
    render(<FormulaResult value={"$$\\frac{a}{b}$$"} onChange={onChange} />);
    expect(screen.getByTestId("katex-preview").querySelector(".katex")).not.toBeNull();
    const box = screen.getByRole("textbox", { name: /LaTeX 원문/ });
    expect(box).toHaveValue("\\frac{a}{b}");
    fireEvent.change(box, { target: { value: "x^2" } });
    expect(onChange).toHaveBeenCalledWith("$$x^2$$");
    await userEvent.click(screen.getByRole("button", { name: /LaTeX 원문 복사/ }));
    expect(writeText).toHaveBeenCalledWith("\\frac{a}{b}");
  });

  it("shows raw output notice when parsing failed", () => {
    const result: PageResult = {
      page: 0, task: "layout", taskName: "문서 구조 분석", resultFormat: "text", raw: "???",
      content: "???", blocks: null, parsed: false, elapsedSeconds: 1.2, cropped: false,
    };
    render(<ResultView result={result} onChange={vi.fn()} onSelectBlock={vi.fn()} />);
    expect(screen.getByRole("note")).toHaveTextContent("원문을 그대로");
    expect(screen.getByText(/1.2초/)).toBeInTheDocument();
  });

  it("lists layout blocks and selects one", async () => {
    const onSelect = vi.fn();
    const result: PageResult = {
      page: 1, task: "layout", taskName: "문서 구조 분석", resultFormat: "layout", raw: "", content: "",
      blocks: [{ type: "table", label: "표", points: [[0, 0], [1, 0], [1, 1], [0, 1]], bbox: [0, 0, 1, 1], angle: 0, content: null }],
      parsed: true, elapsedSeconds: 3, cropped: false,
    };
    render(<ResultView result={result} onChange={vi.fn()} onSelectBlock={onSelect} />);
    await userEvent.click(screen.getByRole("button", { name: /1\. 표/ }));
    expect(onSelect).toHaveBeenCalledWith(result.blocks![0]);
  });
});

describe("CropTool", () => {
  function Harness({ onValue }: { onValue: (c: CropBox | null) => void }) {
    const [crop, setCrop] = useState<CropBox | null>(null);
    return (
      <CropTool
        value={crop}
        onChange={(c) => {
          setCrop(c);
          onValue(c);
        }}
      />
    );
  }

  function mockRect(el: HTMLElement) {
    el.getBoundingClientRect = () =>
      ({ left: 0, top: 0, width: 200, height: 100, right: 200, bottom: 100, x: 0, y: 0, toJSON: () => ({}) }) as DOMRect;
  }

  it("draws a normalized selection by dragging", () => {
    const onValue = vi.fn();
    render(<Harness onValue={onValue} />);
    const area = screen.getByTestId("crop-area");
    mockRect(area);
    fireEvent.pointerDown(area, { clientX: 150, clientY: 80, pointerId: 1 });
    fireEvent.pointerMove(area, { clientX: 50, clientY: 20, pointerId: 1 });
    fireEvent.pointerUp(area, { pointerId: 1 });
    const last = onValue.mock.calls.at(-1)?.[0] as CropBox;
    expect(last.x).toBeCloseTo(0.25);
    expect(last.y).toBeCloseTo(0.2);
    expect(last.width).toBeCloseTo(0.5);
    expect(last.height).toBeCloseTo(0.6);
    expect(screen.getByTestId("crop-selection")).toHaveStyle({ left: "25%" });
  });

  it("drops a too-small selection", () => {
    const onValue = vi.fn();
    render(<Harness onValue={onValue} />);
    const area = screen.getByTestId("crop-area");
    mockRect(area);
    fireEvent.pointerDown(area, { clientX: 10, clientY: 10 });
    fireEvent.pointerMove(area, { clientX: 11, clientY: 11 });
    fireEvent.pointerUp(area);
    expect(onValue).toHaveBeenLastCalledWith(null);
    expect(screen.queryByTestId("crop-selection")).toBeNull();
  });

  it("works with the keyboard", async () => {
    const onValue = vi.fn();
    render(<Harness onValue={onValue} />);
    screen.getByTestId("crop-area").focus();
    await userEvent.keyboard("{Enter}");
    expect(onValue).toHaveBeenLastCalledWith({ x: 0.25, y: 0.25, width: 0.5, height: 0.5 });
    await userEvent.keyboard("{ArrowRight}");
    expect((onValue.mock.calls.at(-1)?.[0] as CropBox).x).toBeCloseTo(0.27);
    await userEvent.keyboard("{Shift>}{ArrowDown}{/Shift}");
    expect((onValue.mock.calls.at(-1)?.[0] as CropBox).height).toBeCloseTo(0.52);
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByTestId("crop-selection")).toBeNull());
  });
});
