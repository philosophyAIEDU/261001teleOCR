import CopyButton from "../CopyButton";

interface Props {
  value: string;
  onChange: (value: string) => void;
  mono?: boolean;
  label: string;
}

export default function TextResult({ value, onChange, mono = false, label }: Props) {
  const rows = Math.min(30, Math.max(8, value.split("\n").length + 2));
  return (
    <div className="flex flex-col gap-3">
      <label className="flex flex-col gap-2">
        <span className="font-bold">{label} (직접 고칠 수 있어요)</span>
        <textarea
          className={`input w-full ${mono ? "font-mono" : ""}`}
          rows={rows}
          value={value}
          spellCheck={!mono}
          onChange={(e) => onChange(e.target.value)}
        />
      </label>
      <div>
        <CopyButton text={value} label={mono ? "코드 복사" : "글자 복사"} />
      </div>
    </div>
  );
}
