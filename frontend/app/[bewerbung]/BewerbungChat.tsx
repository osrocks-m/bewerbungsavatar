"use client";

import { useState, useRef, useEffect } from "react";
import { useParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
  waiting?: boolean;
}

function getOrCreateClientId(): string {
  let id = sessionStorage.getItem("client_id");
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem("client_id", id);
  }
  return id;
}

function resetClientId(): string {
  const id = crypto.randomUUID();
  sessionStorage.setItem("client_id", id);
  return id;
}

async function getOrCreateConversation(bewerbungId: string, clientId: string): Promise<string> {
  const list: { id: string }[] = await fetch(
    `${API_URL}/api/conversations?bewerbung_id=${encodeURIComponent(bewerbungId)}`,
    { headers: { "X-Client-Id": clientId } },
  ).then((r) => r.json());
  if (list.length > 0) return list[0].id;
  const created = await fetch(`${API_URL}/api/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bewerbung_id: bewerbungId, client_id: clientId }),
  }).then((r) => r.json());
  return created.id;
}

async function fetchMessages(conversationId: string): Promise<Message[]> {
  return fetch(`${API_URL}/api/conversations/${conversationId}/messages`).then((r) => r.json());
}

export default function BewerbungChat({ exampleQuestions }: { exampleQuestions: string[] }) {
  const { bewerbung } = useParams<{ bewerbung: string }>();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [pendingUserMessage, setPendingUserMessage] = useState<string | null>(null);
  const [waiting, setWaiting] = useState(false);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const clientId = getOrCreateClientId();
    getOrCreateConversation(bewerbung, clientId).then((id) => setConversationId(id));
  }, [bewerbung]);

  useEffect(() => {
    if (!conversationId) return;
    fetchMessages(conversationId).then(setMessages);
  }, [conversationId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent, waiting]);

  async function handleReset() {
    if (sending) return;
    const newClientId = resetClientId();
    setMessages([]);
    setStreamingContent("");
    setPendingUserMessage(null);
    setWaiting(false);
    setConversationId(null);
    const id = await getOrCreateConversation(bewerbung, newClientId);
    setConversationId(id);
  }

  async function handleSubmit(content: string) {
    if (!conversationId || sending) return;
    setSending(true);
    setInput("");
    setPendingUserMessage(content);
    setWaiting(true);

    const response = await fetch(
      `${API_URL}/api/conversations/${conversationId}/messages`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      }
    );

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const event = JSON.parse(line.slice(6));
        if (event.type === "token") {
          setWaiting(false);
          setStreamingContent((prev) => prev + event.content);
        } else if (event.type === "done") {
          setStreamingContent("");
          setPendingUserMessage(null);
          setWaiting(false);
          setMessages(await fetchMessages(conversationId));
        }
      }
    }

    setSending(false);
  }

  const allMessages: Message[] = [
    ...messages,
    ...(pendingUserMessage ? [{ id: "pending-user", role: "user" as const, content: pendingUserMessage, pending: true }] : []),
    ...(waiting ? [{ id: "waiting", role: "assistant" as const, content: "", waiting: true }] : []),
    ...(streamingContent ? [{ id: "streaming", role: "assistant" as const, content: streamingContent }] : []),
  ];

  const showExamples = exampleQuestions.length > 0 && allMessages.length === 0;

  return (
    <div className="flex flex-col flex-1 bg-zinc-50 dark:bg-zinc-950">
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 max-w-3xl w-full mx-auto">
        {showExamples ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 pt-16">
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-2">Den Bewerbungsavatar können Sie zum Beispiel solche Fragen stellen:</p>
            {exampleQuestions.map((q) => (
              <button
                suppressHydrationWarning
                key={q}
                onClick={() => handleSubmit(q)}
                disabled={!conversationId || sending}
                className="rounded-2xl border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 px-5 py-3 text-sm text-zinc-700 dark:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-700 transition-colors text-left max-w-md w-full disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {q}
              </button>
            ))}
          </div>
        ) : (
          allMessages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.pending
                    ? "bg-zinc-700 text-zinc-300 italic dark:bg-zinc-300 dark:text-zinc-600"
                    : msg.role === "user"
                    ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                    : "bg-white text-zinc-800 border border-zinc-200 dark:bg-zinc-800 dark:text-zinc-100 dark:border-zinc-700"
                }`}
              >
                {msg.waiting ? (
                  <div className="flex gap-1 items-center h-4">
                    <span className="w-2 h-2 rounded-full bg-zinc-400 dark:bg-zinc-500 animate-bounce [animation-delay:-0.3s]" />
                    <span className="w-2 h-2 rounded-full bg-zinc-400 dark:bg-zinc-500 animate-bounce [animation-delay:-0.15s]" />
                    <span className="w-2 h-2 rounded-full bg-zinc-400 dark:bg-zinc-500 animate-bounce" />
                  </div>
                ) : (
                  msg.content
                )}
              </div>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-4 py-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const trimmed = input.trim();
            if (trimmed) handleSubmit(trimmed);
          }}
          className="flex gap-3 max-w-3xl mx-auto"
        >
          <button
            suppressHydrationWarning
            type="button"
            onClick={handleReset}
            disabled={sending}
            title="Reset session"
            className="rounded-full border border-zinc-300 dark:border-zinc-700 px-4 py-3 text-sm text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Reset
          </button>
          <input
            suppressHydrationWarning
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={conversationId ? "Type a message…" : "Connecting…"}
            disabled={!conversationId || sending}
            className="flex-1 rounded-full border border-zinc-300 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 px-5 py-3 text-sm text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400 dark:focus:ring-zinc-500 disabled:opacity-50"
          />
          <button
            suppressHydrationWarning
            type="submit"
            disabled={!input.trim() || !conversationId || sending}
            className="rounded-full bg-zinc-900 dark:bg-zinc-100 px-5 py-3 text-sm font-medium text-white dark:text-zinc-900 transition-colors hover:bg-zinc-700 dark:hover:bg-zinc-300 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
