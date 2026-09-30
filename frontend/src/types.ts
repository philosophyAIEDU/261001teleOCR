export type TaskId =
  | "text"
  | "table"
  | "formula"
  | "code"
  | "layout"
  | "layout_distorted"
  | "chart"
  | "seal";

export type ResultFormat = "text" | "html_table" | "latex" | "code" | "layout";

export interface TaskInfo {
  id: TaskId;
  name: string;
  emoji: string;
  description: string;
  result_format: ResultFormat;
}

export interface UploadInfo {
  upload_id: string;
  filename: string;
  kind: "image" | "pdf";
  page_count: number;
}

export interface CropBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface LayoutBlock {
  type: string;
  label: string;
  points: number[][];
  bbox: number[];
  angle: number | null;
  content: string | null;
}

export interface ConvertResponse {
  task: TaskId;
  result_format: ResultFormat;
  raw: string;
  content: string;
  blocks: LayoutBlock[] | null;
  parsed: boolean;
  elapsed_seconds: number;
}

export interface ParsePageResponse {
  markdown: string;
  blocks: LayoutBlock[];
  elapsed_seconds: number;
}

export interface DeviceStatus {
  kind: "cuda" | "mps" | "cpu";
  name: string;
  dtype: string;
  torch_available: boolean;
  speed_hint: string;
}

export interface SystemStatus {
  backend: string;
  device: DeviceStatus;
  model: {
    loaded: boolean;
    loading: boolean;
    downloaded: boolean;
    model_id: string | null;
    configured_id: string;
    fallback_ids: string[];
    revision: string | null;
    configured_revision: string | null;
    error: string | null;
    attempts: { model_id: string; error: string }[];
  };
  download: {
    active: boolean;
    downloaded_bytes: number;
    total_bytes: number | null;
    percent: number | null;
  };
  queue: { busy: boolean; waiting: number };
  limits: { max_upload_mb: number };
}

export interface SampleInfo {
  id: string;
  file: string;
  task: TaskId;
  title: string;
}

export interface ExportItem {
  result_format: ResultFormat;
  content: string;
  title?: string | null;
}

/** 한 쪽(페이지)의 변환 결과. content 는 사용자가 고친 최종 결과입니다. */
export interface PageResult {
  page: number;
  task: TaskId | "full_page";
  taskName: string;
  resultFormat: ResultFormat;
  raw: string;
  content: string;
  blocks: LayoutBlock[] | null;
  parsed: boolean;
  elapsedSeconds: number;
  cropped: boolean;
}
