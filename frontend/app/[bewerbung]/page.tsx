import { readFile } from "fs/promises";
import { join } from "path";
import BewerbungChat from "./BewerbungChat";

async function loadExampleQuestions(bewerbung: string): Promise<string[]> {
  const filePath = join(process.cwd(), "bewerbungen", bewerbung, "example-questions.yaml");
  try {
    const content = await readFile(filePath, "utf-8");
    const questions = content
      .split("\n")
      .filter((line) => line.trim().startsWith("- "))
      .map((line) => line.trim().slice(2).trim());
    console.log(`[${bewerbung}] Loaded ${questions.length} example question(s) from ${filePath}`);
    return questions;
  } catch (err) {
    console.log(`[${bewerbung}] No example questions loaded (${filePath} not found or unreadable): ${err}`);
    return [];
  }
}

async function loadAvatar(): Promise<string> {
  try {
    const buf = await readFile(join(process.cwd(), "bewerbungen", "avatar.jpg"));
    return `data:image/jpeg;base64,${buf.toString("base64")}`;
  } catch {
    return "";
  }
}

async function loadAbout(): Promise<string> {
  try {
    return await readFile(join(process.cwd(), "bewerbungen", "about.md"), "utf-8");
  } catch {
    return "";
  }
}

function renderAbout(markdown: string) {
  const urlPattern = /(https?:\/\/\S+)/g;

  function renderInline(text: string) {
    const parts = text.split(urlPattern);
    return parts.map((part, i) =>
      /^https?:\/\//.test(part) ? (
        <a key={i} href={part} target="_blank" rel="noopener noreferrer"
          className="underline text-zinc-600 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white">
          {part}
        </a>
      ) : part
    );
  }

  return markdown.split("\n").filter((l) => l.trim()).map((line, i) => {
    if (line.startsWith("# "))
      return <h2 key={i} className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">{line.slice(2)}</h2>;
    return <p key={i} className="text-sm text-zinc-600 dark:text-zinc-300 leading-relaxed">{renderInline(line)}</p>;
  });
}

export default async function BewerbungPage({
  params,
}: {
  params: Promise<{ bewerbung: string }>;
}) {
  const { bewerbung } = await params;
  const [exampleQuestions, avatarSrc, aboutContent] = await Promise.all([
    loadExampleQuestions(bewerbung),
    loadAvatar(),
    loadAbout(),
  ]);

  return (
    <>
      <div className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-6 py-6">
        <div className="flex items-center justify-center gap-8 max-w-3xl mx-auto">
          {avatarSrc && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={avatarSrc} alt="Bewerbungsavatar" className="max-h-[200px] w-auto object-contain rounded-xl shrink-0" />
          )}
          <div className="flex flex-col gap-2">{renderAbout(aboutContent)}</div>
        </div>
      </div>
      <BewerbungChat exampleQuestions={exampleQuestions} />
    </>
  );
}
