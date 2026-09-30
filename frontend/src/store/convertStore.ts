import { create } from "zustand";
import { api, errorMessage } from "../api/client";
import { taskName } from "../lib/tasks";
import type { CropBox, PageResult, TaskId, UploadInfo } from "../types";
import { useHistoryStore } from "./historyStore";

export interface Progress {
  done: number;
  total: number;
  startedAt: number;
}

interface ConvertState {
  upload: UploadInfo | null;
  uploading: boolean;
  task: TaskId;
  selectedPages: number[];
  currentPage: number;
  results: Record<number, PageResult>;
  historyIds: Record<number, string>;
  running: boolean;
  progress: Progress | null;
  error: string | null;
  cropMode: boolean;
  crop: CropBox | null;

  setTask: (task: TaskId) => void;
  setCurrentPage: (page: number) => void;
  togglePage: (page: number) => void;
  setSelectedPages: (pages: number[]) => void;
  setCropMode: (on: boolean) => void;
  setCrop: (crop: CropBox | null) => void;
  setError: (message: string | null) => void;
  updateContent: (page: number, content: string) => void;
  uploadFile: (file: File) => Promise<void>;
  loadSample: (sampleId: string) => Promise<void>;
  runConversion: () => Promise<void>;
  runFullPage: () => Promise<void>;
  reset: () => Promise<void>;
}

const initial = {
  upload: null,
  uploading: false,
  task: "text" as TaskId,
  selectedPages: [] as number[],
  currentPage: 0,
  results: {} as Record<number, PageResult>,
  historyIds: {} as Record<number, string>,
  running: false,
  progress: null,
  error: null,
  cropMode: false,
  crop: null,
};

export const useConvertStore = create<ConvertState>((set, get) => {
  /** 새 파일을 올리기 전에 이전 업로드의 임시 파일을 서버에서 지웁니다. */
  async function discardPrevious(): Promise<void> {
    const previous = get().upload;
    if (previous) {
      try {
        await api.deleteUpload(previous.upload_id);
      } catch {
        // 이미 지워졌으면 무시
      }
    }
  }

  function startWith(upload: UploadInfo, task?: TaskId): void {
    set({
      ...initial,
      task: task ?? get().task,
      upload,
      selectedPages: [0],
    });
  }

  function saveResult(result: PageResult): void {
    const upload = get().upload;
    const historyId = useHistoryStore.getState().add({
      filename: upload?.filename ?? "",
      page: result.page,
      taskName: result.taskName,
      resultFormat: result.resultFormat,
      content: result.content,
    });
    set((s) => ({
      results: { ...s.results, [result.page]: result },
      historyIds: historyId ? { ...s.historyIds, [result.page]: historyId } : s.historyIds,
    }));
  }

  return {
    ...initial,

    setTask: (task) => set({ task }),
    setCurrentPage: (page) => set({ currentPage: page, crop: null }),
    togglePage: (page) =>
      set((s) => ({
        selectedPages: s.selectedPages.includes(page)
          ? s.selectedPages.filter((p) => p !== page)
          : [...s.selectedPages, page].sort((a, b) => a - b),
      })),
    setSelectedPages: (pages) => set({ selectedPages: [...pages].sort((a, b) => a - b) }),
    setCropMode: (on) => set({ cropMode: on, crop: on ? get().crop : null }),
    setCrop: (crop) => set({ crop }),
    setError: (message) => set({ error: message }),

    updateContent: (page, content) => {
      const current = get().results[page];
      if (!current) return;
      set((s) => ({ results: { ...s.results, [page]: { ...current, content } } }));
      const historyId = get().historyIds[page];
      if (historyId) useHistoryStore.getState().updateContent(historyId, content);
    },

    uploadFile: async (file) => {
      set({ uploading: true, error: null });
      try {
        await discardPrevious();
        const upload = await api.upload(file);
        startWith(upload);
      } catch (error) {
        set({ uploading: false, error: errorMessage(error) });
      }
    },

    loadSample: async (sampleId) => {
      set({ uploading: true, error: null });
      try {
        await discardPrevious();
        const { task, ...upload } = await api.useSample(sampleId);
        startWith(upload, task);
      } catch (error) {
        set({ uploading: false, error: errorMessage(error) });
      }
    },

    runConversion: async () => {
      const { upload, task, crop, cropMode, currentPage } = get();
      if (!upload) return;
      // 자르기 영역이 있으면 지금 보고 있는 쪽의 그 영역만 변환합니다.
      const useCrop = cropMode && crop !== null;
      const pages = useCrop ? [currentPage] : get().selectedPages;
      if (pages.length === 0) {
        set({ error: "변환할 쪽을 하나 이상 선택해 주세요." });
        return;
      }
      set({ running: true, error: null, progress: { done: 0, total: pages.length, startedAt: Date.now() } });
      try {
        for (const [index, page] of pages.entries()) {
          set({ currentPage: page });
          const res = await api.convert(upload.upload_id, page, task, useCrop ? crop : null);
          saveResult({
            page,
            task,
            taskName: taskName(task),
            resultFormat: res.result_format,
            raw: res.raw,
            content: res.content,
            blocks: res.blocks,
            parsed: res.parsed,
            elapsedSeconds: res.elapsed_seconds,
            cropped: useCrop,
          });
          set((s) => ({ progress: s.progress && { ...s.progress, done: index + 1 } }));
        }
        if (useCrop) set({ cropMode: false, crop: null });
      } catch (error) {
        set({ error: errorMessage(error) });
      } finally {
        set({ running: false, progress: null });
      }
    },

    runFullPage: async () => {
      const { upload, currentPage, crop, cropMode } = get();
      if (!upload) return;
      const useCrop = cropMode && crop !== null;
      set({ running: true, error: null, progress: { done: 0, total: 1, startedAt: Date.now() } });
      try {
        const res = await api.parsePage(upload.upload_id, currentPage, useCrop ? crop : null);
        saveResult({
          page: currentPage,
          task: "full_page",
          taskName: taskName("full_page"),
          resultFormat: "text",
          raw: res.markdown,
          content: res.markdown,
          blocks: res.blocks.length ? res.blocks : null,
          parsed: true,
          elapsedSeconds: res.elapsed_seconds,
          cropped: useCrop,
        });
      } catch (error) {
        set({ error: errorMessage(error) });
      } finally {
        set({ running: false, progress: null });
      }
    },

    reset: async () => {
      await discardPrevious();
      set({ ...initial, task: get().task });
    },
  };
});
