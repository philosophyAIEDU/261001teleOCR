import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import remarkGfm from "remark-gfm";

const components: Components = {
  // 외부 링크는 새 탭에서 열고, 이 앱의 주소 정보를 넘기지 않습니다.
  a: ({ href, children }) => {
    const external = href?.startsWith("http");
    return (
      <a href={href} target={external ? "_blank" : undefined} rel={external ? "noreferrer noopener" : undefined}>
        {children}
        {external && <span className="sr-only"> (새 창)</span>}
      </a>
    );
  },
};

export default function MarkdownContent({ source }: { source: string }) {
  return (
    <div className="prose-content">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {source}
      </ReactMarkdown>
    </div>
  );
}
