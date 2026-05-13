"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [bewerbungen, setBewerbungen] = useState<string[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/api/bewerbungen`)
      .then((r) => r.json())
      .then(setBewerbungen);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center flex-1 gap-6 px-4">
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">Bewerbungen</h1>
      <ul className="flex flex-col gap-3 w-full max-w-sm">
        {bewerbungen.map((b) => (
          <li key={b}>
            <Link
              href={`/${b}`}
              className="block w-full rounded-2xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800 px-5 py-4 text-sm font-medium text-zinc-900 dark:text-zinc-100 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors"
            >
              {b}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
