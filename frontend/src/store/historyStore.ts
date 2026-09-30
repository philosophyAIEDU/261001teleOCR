import { create } from "zustand";
import type { ResultFormat } from "../types";

/** 최근 변환 기록. 이 컴퓨터 브라우저(localStorage)에만 저장되고 서버·외부로는 보내지 않습니다. */
export interface HistoryEntry {
  id: string;
  createdAt: string;
  filename: string;
  page: number;
  taskName: string;
  resultFormat: ResultFormat;
  content: string;
}

const STORAGE_KEY = "teleocr-history-v1";
const ENABLED_KEY = "teleocr-history-enabled";
export const HISTORY_LIMIT = 30;

function readEntries(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? (parsed as HistoryEntry[]) : [];
  } catch {
    return [];
  }
}

function writeEntries(entries: HistoryEntry[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // 저장 공간이 부족하면 조용히 넘어갑니다.
  }
}

function readEnabled(): boolean {
  try {
    return localStorage.getItem(ENABLED_KEY) !== "false";
  } catch {
    return true;
  }
}

interface HistoryState {
  entries: HistoryEntry[];
  enabled: boolean;
  add: (entry: Omit<HistoryEntry, "id" | "createdAt">) => string | null;
  updateContent: (id: string, content: string) => void;
  remove: (id: string) => void;
  clear: () => void;
  setEnabled: (enabled: boolean) => void;
}

function newId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export const useHistoryStore = create<HistoryState>((set, get) => ({
  entries: readEntries(),
  enabled: readEnabled(),
  add: (entry) => {
    if (!get().enabled) return null;
    const item: HistoryEntry = { ...entry, id: newId(), createdAt: new Date().toISOString() };
    const entries = [item, ...get().entries].slice(0, HISTORY_LIMIT);
    writeEntries(entries);
    set({ entries });
    return item.id;
  },
  updateContent: (id, content) => {
    const entries = get().entries.map((e) => (e.id === id ? { ...e, content } : e));
    writeEntries(entries);
    set({ entries });
  },
  remove: (id) => {
    const entries = get().entries.filter((e) => e.id !== id);
    writeEntries(entries);
    set({ entries });
  },
  clear: () => {
    writeEntries([]);
    set({ entries: [] });
  },
  setEnabled: (enabled) => {
    try {
      localStorage.setItem(ENABLED_KEY, String(enabled));
    } catch {
      // 무시
    }
    set({ enabled });
  },
}));
