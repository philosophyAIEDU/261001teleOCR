/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // 가독성을 위해 가장 작은 글자도 16px 이상이 되도록 xs/sm 크기를 16px 로 고정합니다.
      fontSize: {
        xs: ["1rem", { lineHeight: "1.5rem" }],
        sm: ["1rem", { lineHeight: "1.5rem" }],
      },
      // 외부 글꼴 CDN 을 쓰지 않고, 운영체제에 이미 설치된 한글 글꼴을 사용합니다.
      fontFamily: {
        sans: [
          '"Malgun Gothic"',
          '"맑은 고딕"',
          '"Apple SD Gothic Neo"',
          '"Noto Sans KR"',
          '"Noto Sans CJK KR"',
          "system-ui",
          "sans-serif",
        ],
        mono: ["Consolas", '"D2Coding"', "Menlo", "Monaco", '"Courier New"', "monospace"],
      },
      colors: {
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          600: "#1d4ed8",
          700: "#1e40af",
          800: "#1e3a8a",
        },
      },
    },
  },
  plugins: [],
};
