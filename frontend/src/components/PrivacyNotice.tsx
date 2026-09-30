export default function PrivacyNotice({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <p className="bg-emerald-50 px-4 py-2 text-center font-medium text-emerald-900">
        <span aria-hidden="true">🔒 </span>
        올린 파일은 인터넷으로 보내지 않고 <strong>이 컴퓨터 안에서만</strong> 처리돼요.
      </p>
    );
  }
  return (
    <section
      aria-labelledby="privacy-title"
      className="rounded-2xl border-2 border-emerald-300 bg-emerald-50 p-5 text-emerald-950"
    >
      <h2 id="privacy-title" className="text-xl font-bold">
        <span aria-hidden="true">🔒 </span>학생 개인정보, 안심하고 변환하세요
      </h2>
      <ul className="mt-2 list-disc space-y-1 pl-6">
        <li>모든 변환은 이 컴퓨터 안에서만 이루어져요. 파일이 개발사나 다른 서버로 전송되지 않아요.</li>
        <li>인터넷은 처음 한 번 AI 모델을 내려받을 때만 사용해요.</li>
        <li>올린 파일은 임시 폴더에 잠시 보관했다가 자동으로 지워요.</li>
        <li>변환 결과 파일의 보관·공유는 학교 개인정보 지침을 따라 주세요.</li>
      </ul>
    </section>
  );
}
