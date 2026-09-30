export default function ErrorAlert({ message, onClose }: { message: string | null; onClose?: () => void }) {
  if (!message) return null;
  return (
    <div role="alert" className="flex items-start gap-3 rounded-xl border-2 border-red-300 bg-red-50 p-4 text-red-900">
      <span aria-hidden="true" className="text-2xl">
        ⚠️
      </span>
      <p className="flex-1 font-medium">{message}</p>
      {onClose && (
        <button type="button" className="btn-ghost" onClick={onClose}>
          닫기
        </button>
      )}
    </div>
  );
}
