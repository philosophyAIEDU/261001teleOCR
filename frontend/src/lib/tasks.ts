import type { TaskInfo } from "../types";

/** 작업 카드 목록. 백엔드 backend/ocr/tasks.py 의 TASK_SPECS 와 같은 순서·이름입니다. */
export const TASKS: TaskInfo[] = [
  { id: "text", name: "글자 뽑기", emoji: "📝", description: "사진 속 글자를 편집할 수 있는 텍스트로 바꿔요.", result_format: "text" },
  { id: "table", name: "표 만들기", emoji: "📊", description: "표 사진을 고칠 수 있는 표로 바꾸고 엑셀로 내보내요.", result_format: "html_table" },
  { id: "formula", name: "수식 변환", emoji: "➗", description: "수식 사진을 LaTeX 수식으로 바꿔요.", result_format: "latex" },
  { id: "code", name: "코드 옮기기", emoji: "💻", description: "교재 속 코드 사진을 실행할 수 있는 코드로 옮겨요.", result_format: "code" },
  { id: "layout", name: "문서 구조 분석", emoji: "🗂️", description: "제목·본문·표·그림이 어디 있는지 찾아 표시해요.", result_format: "layout" },
  { id: "layout_distorted", name: "휘어진 사진 분석", emoji: "📱", description: "비스듬히·휘어지게 찍은 사진의 구조를 찾아요.", result_format: "layout" },
  { id: "chart", name: "그래프→데이터표", emoji: "📈", description: "그래프 그림에서 데이터 표를 뽑아내요.", result_format: "html_table" },
  { id: "seal", name: "도장 인식", emoji: "🔖", description: "도장(인장) 속 글자를 읽어요.", result_format: "text" },
];

export function taskName(id: string): string {
  if (id === "full_page") return "한 쪽 통째로 변환";
  return TASKS.find((t) => t.id === id)?.name ?? id;
}
