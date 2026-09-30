import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import App from "../App";
import { api } from "../api/client";
import { useConvertStore } from "../store/convertStore";
import { useHistoryStore } from "../store/historyStore";
import type { ConvertResponse } from "../types";

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      upload: vi.fn(),
      deleteUpload: vi.fn().mockResolvedValue({ deleted: true }),
      convert: vi.fn(),
      exportFile: vi.fn(),
      useSample: vi.fn(),
      parsePage: vi.fn(),
      getSystem: vi.fn(),
    },
  };
});

const mocked = vi.mocked(api);

const tableResponse: ConvertResponse = {
  task: "table",
  result_format: "html_table",
  raw: "<fcel>a<fcel>b<nl>",
  content: "<table><tr><td>a</td><td>b</td></tr></table>",
  blocks: null,
  parsed: true,
  elapsed_seconds: 2.5,
};

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  useConvertStore.setState(useConvertStore.getInitialState(), true);
  useHistoryStore.setState({ entries: [], enabled: true });
  vi.clearAllMocks();
});

describe("convert flow", () => {
  it("uploads a file, converts as a table, edits it and shows Excel export", async () => {
    mocked.upload.mockResolvedValue({ upload_id: "u1", filename: "성적표.png", kind: "image", page_count: 1 });
    mocked.convert.mockResolvedValue(tableResponse);
    renderAt("/convert");

    const input = screen.getByLabelText("변환할 파일 선택");
    await userEvent.upload(input, new File(["x"], "성적표.png", { type: "image/png" }));
    expect(await screen.findByText(/성적표.png/)).toBeInTheDocument();

    await userEvent.click(screen.getByText("표 만들기"));
    await userEvent.click(screen.getByRole("button", { name: "▶ 변환하기" }));
    expect(mocked.convert).toHaveBeenCalledWith("u1", 0, "table", null);

    const cell = await screen.findByRole("textbox", { name: "1행 1번째 칸" });
    await userEvent.type(cell, "!");
    expect(useConvertStore.getState().results[0].content).toContain("<td>a!</td>");
    // 기록에도 고친 내용이 반영됩니다.
    expect(useHistoryStore.getState().entries[0].content).toContain("a!");

    expect(screen.getByRole("button", { name: /Excel/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Word/ })).toBeInTheDocument();
  });

  it("hides Excel export for non-table results and shows server errors in Korean", async () => {
    mocked.upload.mockResolvedValue({ upload_id: "u2", filename: "a.png", kind: "image", page_count: 1 });
    mocked.convert.mockResolvedValueOnce({ ...tableResponse, task: "text", result_format: "text", content: "hello" });
    renderAt("/convert");
    await userEvent.upload(screen.getByLabelText("변환할 파일 선택"), new File(["x"], "a.png", { type: "image/png" }));
    await userEvent.click(await screen.findByRole("button", { name: "▶ 변환하기" }));
    expect(await screen.findByDisplayValue("hello")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Excel/ })).toBeNull();

    const { ApiError } = await import("../api/client");
    mocked.convert.mockRejectedValueOnce(new ApiError("메모리가 부족해요. 이미지를 더 작게 잘라서 다시 시도해 주세요.", 507));
    await userEvent.click(screen.getByRole("button", { name: "▶ 변환하기" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("메모리가 부족해요");
  });

  it("crops a region and converts only that region", async () => {
    mocked.upload.mockResolvedValue({ upload_id: "u3", filename: "b.png", kind: "image", page_count: 1 });
    mocked.convert.mockResolvedValue({ ...tableResponse, task: "formula", result_format: "latex", content: "$$x$$" });
    renderAt("/convert");
    await userEvent.upload(screen.getByLabelText("변환할 파일 선택"), new File(["x"], "b.png", { type: "image/png" }));
    await userEvent.click(await screen.findByRole("button", { name: /영역 잘라서 변환/ }));
    expect(screen.getByRole("button", { name: "▶ 변환하기" })).toBeDisabled();
    screen.getByTestId("crop-area").focus();
    await userEvent.keyboard("{Enter}");
    await userEvent.click(screen.getByRole("button", { name: /자른 영역만 변환하기/ }));
    expect(mocked.convert).toHaveBeenCalledWith("u3", 0, "text", { x: 0.25, y: 0.25, width: 0.5, height: 0.5 });
    await waitFor(() => expect(screen.getByText(/자른 영역/)).toBeInTheDocument());
  });

  it("converts selected PDF pages with progress", async () => {
    mocked.upload.mockResolvedValue({ upload_id: "p1", filename: "시험지.pdf", kind: "pdf", page_count: 3 });
    mocked.convert.mockResolvedValue({ ...tableResponse, result_format: "text", content: "page" });
    renderAt("/convert");
    await userEvent.upload(screen.getByLabelText("변환할 파일 선택"), new File(["x"], "시험지.pdf", { type: "application/pdf" }));
    await userEvent.click(await screen.findByRole("button", { name: "전체 선택" }));
    await userEvent.click(screen.getByRole("button", { name: "▶ 변환하기" }));
    await waitFor(() => expect(mocked.convert).toHaveBeenCalledTimes(3));
    expect(mocked.convert.mock.calls.map((c) => c[1])).toEqual([0, 1, 2]);
    expect(Object.keys(useConvertStore.getState().results)).toHaveLength(3);
  });
});

describe("pages", () => {
  it("renders the about page with developer info and limitations", () => {
    renderAt("/about");
    expect(screen.getByRole("heading", { name: "TeleOCR 모델 소개" })).toBeInTheDocument();
    expect(screen.getAllByText(/Xingchen/).length).toBeGreaterThan(0);
    expect(screen.getByText(/한국어 인식 품질은 공식적으로 보장되지 않으므로/)).toBeInTheDocument();
  });

  it("renders guide cards with the online demo warning", () => {
    renderAt("/guide");
    expect(screen.getByRole("heading", { name: /영어 — 지문을 어휘 목록/ })).toBeInTheDocument();
    expect(screen.getByText(/온라인 데모는 파일이 외부 서버로 전송돼요/)).toBeInTheDocument();
  });

  it("shows CPU warning on the system check page", async () => {
    mocked.getSystem.mockResolvedValue({
      backend: "transformers",
      device: { kind: "cpu", name: "CPU (x86_64)", dtype: "float32", torch_available: true, speed_hint: "GPU 없이 CPU 로만 실행해요. 느려요." },
      model: {
        loaded: false, loading: false, downloaded: false, model_id: null, configured_id: "XingChen-AGI/TeleOCR",
        fallback_ids: ["StarDoc-AI/TeleOCR"], revision: null, configured_revision: null,
        error: "AI 모델을 불러오지 못했어요.", attempts: [{ model_id: "XingChen-AGI/TeleOCR", error: "OSError" }],
      },
      download: { active: false, downloaded_bytes: 0, total_bytes: null, percent: null },
      queue: { busy: false, waiting: 0 },
      limits: { max_upload_mb: 50 },
    });
    renderAt("/system");
    expect(await screen.findByText(/느려요/)).toBeInTheDocument();
    expect(screen.getByText("CPU 전용")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("불러오지 못했어요");
    expect(screen.getByRole("button", { name: "모델 내려받고 준비하기" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "샘플로 테스트하기" })).toBeInTheDocument();
  });

  it("deletes history entries from the home page", async () => {
    useHistoryStore.getState().add({ filename: "x.png", page: 0, taskName: "글자 뽑기", resultFormat: "text", content: "abc" });
    renderAt("/");
    expect(screen.getByText("x.png")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /x.png 1쪽 기록 삭제/ }));
    expect(screen.queryByText("x.png")).toBeNull();
    expect(JSON.parse(localStorage.getItem("teleocr-history-v1") ?? "[]")).toEqual([]);
  });
});
