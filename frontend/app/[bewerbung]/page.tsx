import { readFile } from "fs/promises";
import { join } from "path";
import BewerbungChat from "./BewerbungChat";

async function loadExampleQuestions(bewerbung: string): Promise<string[]> {
  try {
    const filePath = join(process.cwd(), "bewerbungen", bewerbung, "example-questions.yaml");
    const content = await readFile(filePath, "utf-8");
    return content
      .split("\n")
      .filter((line) => line.trim().startsWith("- "))
      .map((line) => line.trim().slice(2).trim());
  } catch {
    return [];
  }
}

export default async function BewerbungPage({
  params,
}: {
  params: Promise<{ bewerbung: string }>;
}) {
  const { bewerbung } = await params;
  const exampleQuestions = await loadExampleQuestions(bewerbung);

  return <BewerbungChat exampleQuestions={exampleQuestions} />;
}
