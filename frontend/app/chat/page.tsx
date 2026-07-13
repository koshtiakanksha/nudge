"use client";

import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { api } from "@/lib/api";
import { ChatMessage } from "@/types/api";
import { cn } from "@/lib/format";
import { PageHeader } from "@/components/page-header";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getChatHistory().then(setMessages);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    const userMsg: ChatMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true);
    try {
      const { reply } = await api.sendChatMessage(userMsg.content);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I couldn't process that. Try again in a moment." },
      ]);
    } finally {
      setSending(false);
    }
  };

  const SUGGESTIONS = [
    "How much have I spent on dining this month?",
    "Am I on track with my savings buffer?",
    "What's my biggest spending category?",
  ];

  return (
    <div className="flex flex-col h-screen">
      <PageHeader title="Ask Nudge" subtitle="A grounded second opinion on your money" />

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 py-6 space-y-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="space-y-2">
            <p className="text-sm text-slate mb-3">Try asking:</p>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => setInput(s)}
                className="block text-left text-sm px-3 py-2 border border-line rounded-md hover:bg-line/30 transition-colors w-full max-w-md"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
            <div
              className={cn(
                "max-w-md px-4 py-2.5 rounded-lg text-sm leading-relaxed",
                m.role === "user" ? "bg-moss text-paper" : "bg-white/70 border border-line text-ink"
              )}
            >
              {m.content}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="px-4 py-2.5 rounded-lg text-sm bg-white/70 border border-line text-slate">thinking…</div>
          </div>
        )}
      </div>

      <div className="px-8 py-5 border-t border-line">
        <div className="flex gap-2 max-w-2xl">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about your spending, savings, or budget…"
            className="flex-1 border border-line rounded-md px-4 py-2.5 text-sm"
          />
          <button
            onClick={handleSend}
            disabled={sending || !input.trim()}
            className="px-4 py-2.5 bg-moss text-paper rounded-md hover:bg-moss2 transition-colors disabled:opacity-60"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
