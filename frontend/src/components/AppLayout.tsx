import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import PrivacyNotice from "./PrivacyNotice";

const NAV_ITEMS = [
  { to: "/", label: "처음 화면", end: true },
  { to: "/convert", label: "변환하기", end: false },
  { to: "/system", label: "시스템 점검", end: false },
  { to: "/guide", label: "활용 가이드", end: false },
  { to: "/about", label: "모델 소개", end: false },
];

export default function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
      <a href="#main" className="skip-link">
        본문으로 바로 가기
      </a>
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <NavLink to="/" className="flex items-center gap-2 text-xl font-bold text-brand-700">
            <span aria-hidden="true">📄</span> TeleOCR 교실
          </NavLink>
          <nav aria-label="주 메뉴" className="flex flex-wrap gap-1">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-2 font-medium ${
                    isActive ? "bg-brand-600 text-white" : "text-slate-700 hover:bg-slate-100"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
        <PrivacyNotice compact />
      </header>
      <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-6" tabIndex={-1}>
        {children}
      </main>
      <footer className="border-t border-slate-200 bg-white py-4 text-center text-slate-600">
        TeleOCR 교실 · 오픈소스 모델 TeleOCR(Apache-2.0)을 이 컴퓨터에서 실행합니다.
      </footer>
    </div>
  );
}
