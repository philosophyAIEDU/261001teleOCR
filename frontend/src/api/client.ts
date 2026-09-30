import type {
  ConvertResponse,
  CropBox,
  ExportItem,
  ParsePageResponse,
  SampleInfo,
  SystemStatus,
  TaskId,
  TaskInfo,
  UploadInfo,
} from "../types";

export const CONNECTION_ERROR =
  "프로그램과 연결이 끊겼어요. 검은 창(start 스크립트)이 켜져 있는지 확인하고 새로고침해 주세요.";

/** 서버가 보낸 한국어 오류 메시지를 담는 예외 */
export class ApiError extends Error {
  status: number;
  code: string | undefined;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

interface ErrorBody {
  detail?: unknown;
  code?: string;
}

async function parseError(response: Response): Promise<ApiError> {
  let message = `요청을 처리하지 못했어요. (오류 ${response.status})`;
  let code: string | undefined;
  try {
    const body = (await response.json()) as ErrorBody;
    if (typeof body.detail === "string") message = body.detail;
    else if (Array.isArray(body.detail)) message = "입력값이 올바르지 않아요. 다시 시도해 주세요.";
    code = body.code;
  } catch {
    // JSON 이 아니면 기본 메시지를 씁니다.
  }
  return new ApiError(message, response.status, code);
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError(CONNECTION_ERROR, 0, "network");
  }
  if (!response.ok) throw await parseError(response);
  return response;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await request(path, init);
  return (await response.json()) as T;
}

function postJson<T>(path: string, body: unknown): Promise<T> {
  return json<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const api = {
  getSystem: () => json<SystemStatus>("/api/system"),
  loadModel: () => postJson<{ started: boolean }>("/api/model/load", {}),
  getTasks: () => json<TaskInfo[]>("/api/tasks"),
  getSamples: () => json<SampleInfo[]>("/api/samples"),
  useSample: (id: string) => postJson<UploadInfo & { task: TaskId }>(`/api/samples/${id}`, {}),

  upload: (file: File): Promise<UploadInfo> => {
    const form = new FormData();
    form.append("file", file, file.name);
    return json<UploadInfo>("/api/uploads", { method: "POST", body: form });
  },
  deleteUpload: (uploadId: string) =>
    json<{ deleted: boolean }>(`/api/uploads/${uploadId}`, { method: "DELETE" }),
  pageUrl: (uploadId: string, page: number) => `/api/uploads/${uploadId}/pages/${page}`,

  convert: (uploadId: string, page: number, task: TaskId, crop: CropBox | null = null) =>
    postJson<ConvertResponse>("/api/convert", { upload_id: uploadId, page, task, crop }),
  parsePage: (uploadId: string, page: number, crop: CropBox | null = null) =>
    postJson<ParsePageResponse>("/api/parse-page", { upload_id: uploadId, page, crop }),

  exportFile: async (format: "md" | "docx" | "xlsx", items: ExportItem[], filename: string): Promise<Blob> => {
    const response = await request(`/api/export/${format}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items, filename }),
    });
    return response.blob();
  },
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "알 수 없는 문제가 생겼어요. 다시 시도해 주세요.";
}
