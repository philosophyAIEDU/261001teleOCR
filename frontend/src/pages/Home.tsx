import { Link } from "react-router-dom";
import HistoryList from "../components/HistoryList";
import PrivacyNotice from "../components/PrivacyNotice";
import { TASKS } from "../lib/tasks";

export default function Home() {
  return (
    <div className="flex flex-col gap-8">
      <section className="rounded-3xl bg-brand-700 p-8 text-white">
        <h1 className="text-3xl font-bold md:text-4xl">종이 자료를 편집할 수 있는 파일로</h1>
        <p className="mt-3 max-w-3xl text-lg">
          학습지·교과서·시험지·판서 사진을 올리면 AI가 글자, 표, 수식, 코드로 바꿔 드려요. 모든 처리는 이 컴퓨터 안에서만
          이루어져요.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/convert" className="btn-light text-lg">
            📷 변환 시작하기
          </Link>
          <Link to="/system" className="btn-outline-light text-lg">
            🩺 시스템 점검
          </Link>
          <Link to="/guide" className="btn-outline-light text-lg">
            💡 활용 가이드
          </Link>
        </div>
      </section>

      <PrivacyNotice />

      <section aria-labelledby="features-title">
        <h2 id="features-title" className="mb-4 text-2xl font-bold">
          할 수 있는 일
        </h2>
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {TASKS.map((task) => (
            <li key={task.id} className="rounded-2xl border border-slate-300 bg-white p-4">
              <p className="text-lg font-bold">
                <span aria-hidden="true">{task.emoji} </span>
                {task.name}
              </p>
              <p className="text-slate-700">{task.description}</p>
            </li>
          ))}
        </ul>
        <p className="mt-4 rounded-xl bg-amber-50 p-4 text-amber-950">
          공식 지원 언어는 영어와 중국어예요. 한국어 인식 품질은 보장되지 않으니 결과를 꼭 확인해 주세요.
        </p>
      </section>

      <HistoryList />
    </div>
  );
}
