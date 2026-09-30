import MarkdownContent from "../components/MarkdownContent";
import about from "../content/about.md?raw";

export default function About() {
  return (
    <article className="card mx-auto max-w-4xl">
      <MarkdownContent source={about} />
    </article>
  );
}
