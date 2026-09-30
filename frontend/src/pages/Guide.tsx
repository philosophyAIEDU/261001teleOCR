import MarkdownContent from "../components/MarkdownContent";
import guide from "../content/guide.md?raw";

/** guide.md 를 "## " 제목마다 나눠 카드 하나씩으로 보여 줍니다. 첫 부분(# 제목과 소개)은 머리말입니다. */
export function splitSections(markdown: string): { intro: string; sections: string[] } {
  const parts = markdown.split(/^(?=## )/m);
  const [intro, ...sections] = parts[0].startsWith("## ") ? ["", ...parts] : parts;
  return { intro: intro.trim(), sections: sections.map((s) => s.trim()).filter(Boolean) };
}

export default function Guide() {
  const { intro, sections } = splitSections(guide);
  return (
    <div className="flex flex-col gap-6">
      {intro && (
        <div className="card">
          <MarkdownContent source={intro} />
        </div>
      )}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {sections.map((section, index) => (
          <article key={index} className="card">
            <MarkdownContent source={section} />
          </article>
        ))}
      </div>
    </div>
  );
}
