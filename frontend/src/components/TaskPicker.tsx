import { TASKS } from "../lib/tasks";
import type { TaskId } from "../types";

interface Props {
  value: TaskId;
  onChange: (task: TaskId) => void;
  disabled?: boolean;
}

/** 작업 유형을 큰 카드로 고르는 라디오 버튼 묶음 (방향키로도 이동 가능) */
export default function TaskPicker({ value, onChange, disabled = false }: Props) {
  return (
    <fieldset disabled={disabled}>
      <legend className="mb-3 text-xl font-bold">무엇으로 바꿀까요?</legend>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {TASKS.map((task) => {
          const checked = task.id === value;
          return (
            <label
              key={task.id}
              className={`task-card ${checked ? "border-brand-600 bg-brand-50 ring-2 ring-brand-600" : "border-slate-300 bg-white hover:border-brand-600"}`}
            >
              <input
                type="radio"
                name="task"
                value={task.id}
                checked={checked}
                onChange={() => onChange(task.id)}
                className="sr-only"
              />
              <span aria-hidden="true" className="text-3xl">
                {task.emoji}
              </span>
              <span className="text-lg font-bold">{task.name}</span>
              <span className="text-slate-700">{task.description}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
