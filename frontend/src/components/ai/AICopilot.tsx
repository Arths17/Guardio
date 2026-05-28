"use client";

import { useState, useRef, useEffect } from "react";
import { useGuardioStore } from "@/store/useGuardioStore";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";

const API_BASE = "/api";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "devkey";

async function fetchAISuggest(payload: object): Promise<string> {
  const res = await fetch(`${API_BASE}/ai/suggest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Api-Key": API_KEY,
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json() as { suggestion: string };
  return data.suggestion;
}

async function fetchAIGenerate(prompt: string): Promise<string> {
  const res = await fetch(`${API_BASE}/AI/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json() as { text: string };
  return data.text;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  ts: number;
  loading?: boolean;
}

const QUICK_PROMPTS = [
  "Analyze current threat posture",
  "What attack is most likely right now?",
  "How do I contain a ransomware outbreak?",
  "Recommend firewall rules",
  "Explain lateral movement techniques",
];

export default function AICopilot() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Guardio AI is online. I have visibility into your current threat landscape, active simulation state, and IDS detections. Ask me anything about your security posture, or request mitigation recommendations.",
      ts: Date.now(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const { alerts, activeAttack, threatLevel, threatStatus, incidents } = useGuardioStore();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(content: string) {
    if (!content.trim() || loading) return;
    setLoading(true);
    setInput("");

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
      ts: Date.now(),
    };

    const loadingMsg: Message = {
      id: "loading",
      role: "assistant",
      content: "",
      ts: Date.now(),
      loading: true,
    };

    setMessages((prev) => [...prev, userMsg, loadingMsg]);

    try {
      // Build context from current store state
      const context = {
        threat_level: threatLevel,
        threat_status: threatStatus,
        active_attack: activeAttack,
        recent_alerts: alerts.slice(0, 5).map((a) => ({
          level: a.level,
          reason: a.reason,
          protocol: a.protocol,
        })),
        recent_incidents: incidents.slice(0, 5).map((i) => ({
          type: i.type,
          severity: i.severity,
          title: i.title,
        })),
      };

      const fullPrompt = `[Context: ${JSON.stringify(context)}]\n\nUser query: ${content}`;
      const text = await fetchAIGenerate(fullPrompt);

      setMessages((prev) =>
        prev
          .filter((m) => m.id !== "loading")
          .concat({
            id: Date.now().toString(),
            role: "assistant",
            content: text,
            ts: Date.now(),
          })
      );
    } catch {
      setMessages((prev) =>
        prev
          .filter((m) => m.id !== "loading")
          .concat({
            id: Date.now().toString(),
            role: "assistant",
            content: "AI service is unavailable. Ensure the backend is running with a valid Gemini API key.",
            ts: Date.now(),
          })
      );
    } finally {
      setLoading(false);
    }
  }

  async function suggestForLatestAlert() {
    const alert = alerts[0];
    if (!alert) {
      sendMessage("No alerts available to analyze.");
      return;
    }
    setLoading(true);
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: `Suggest defense for: ${alert.reason} (${alert.level}, score ${alert.score})`,
      ts: Date.now(),
    };
    const loadingMsg: Message = { id: "loading", role: "assistant", content: "", ts: Date.now(), loading: true };
    setMessages((prev) => [...prev, userMsg, loadingMsg]);

    try {
      const text = await fetchAISuggest(alert as unknown as object);
      setMessages((prev) =>
        prev.filter((m) => m.id !== "loading").concat({
          id: Date.now().toString(),
          role: "assistant",
          content: text,
          ts: Date.now(),
        })
      );
    } catch {
      setMessages((prev) =>
        prev.filter((m) => m.id !== "loading").concat({
          id: Date.now().toString(),
          role: "assistant",
          content: "Unable to fetch AI suggestion at this time.",
          ts: Date.now(),
        })
      );
    } finally {
      setLoading(false);
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Chat area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-bg-border bg-bg-surface flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse-slow" />
            <span className="text-xs font-mono font-medium text-text-secondary uppercase tracking-widest">
              AI Security Copilot
            </span>
          </div>
          <button
            onClick={suggestForLatestAlert}
            disabled={loading || alerts.length === 0}
            className="flex items-center gap-1.5 px-2.5 py-1 text-2xs font-mono rounded border border-bg-border text-text-muted hover:border-accent-cyan hover:text-accent-cyan disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Analyze latest alert
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                <ChatMessage msg={msg} />
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div className="flex-shrink-0 border-t border-bg-border bg-bg-surface px-4 py-3">
          <div className="flex gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about your security posture…"
              rows={2}
              className="flex-1 bg-bg-elevated border border-bg-border rounded px-3 py-2 text-xs font-sans text-text-primary placeholder-text-dim resize-none focus:outline-none focus:border-accent-cyan/50 transition-colors"
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={loading || !input.trim()}
              className="px-3 py-2 bg-accent-cyan/10 border border-accent-cyan/30 text-accent-cyan rounded text-2xs font-mono disabled:opacity-40 disabled:cursor-not-allowed hover:bg-accent-cyan/15 transition-colors flex-shrink-0"
            >
              SEND
            </button>
          </div>
          <div className="text-2xs font-mono text-text-dim mt-1">Enter to send · Shift+Enter for newline</div>
        </div>
      </div>

      {/* Right panel: quick prompts + context */}
      <aside className="w-60 bg-bg-surface border-l border-bg-border flex flex-col overflow-hidden flex-shrink-0">
        <div className="px-3 py-2.5 border-b border-bg-border flex-shrink-0">
          <span className="text-2xs font-mono font-medium text-text-secondary uppercase tracking-widest">
            Quick Queries
          </span>
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1.5">
          {QUICK_PROMPTS.map((p) => (
            <button
              key={p}
              onClick={() => sendMessage(p)}
              disabled={loading}
              className="w-full text-left px-2.5 py-2 text-2xs font-sans text-text-secondary bg-bg-elevated border border-bg-border rounded hover:border-accent-cyan/30 hover:text-text-primary transition-colors disabled:opacity-40 leading-relaxed"
            >
              {p}
            </button>
          ))}
        </div>

        {/* Situational context */}
        <div className="border-t border-bg-border px-3 py-3 flex-shrink-0">
          <div className="text-2xs font-mono text-text-muted mb-2 uppercase tracking-widest">Context</div>
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-2xs font-mono text-text-muted">Threat</span>
              <span className="text-2xs font-mono text-accent-cyan">{threatStatus}</span>
            </div>
            {activeAttack && (
              <div className="flex justify-between">
                <span className="text-2xs font-mono text-text-muted">Active</span>
                <span className="text-2xs font-mono text-accent-red">{activeAttack}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-2xs font-mono text-text-muted">Alerts</span>
              <span className="text-2xs font-mono text-text-secondary tabular-nums">{alerts.length}</span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}

function ChatMessage({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";

  if (msg.loading) {
    return (
      <div className="flex gap-2.5 items-start">
        <AIAvatar />
        <div className="flex-1">
          <TypingIndicator />
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div className="flex gap-2.5 items-start justify-end">
        <div className="max-w-[75%] bg-bg-elevated border border-bg-border rounded-lg rounded-tr-sm px-3 py-2">
          <p className="text-xs text-text-primary leading-relaxed whitespace-pre-wrap">{msg.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-2.5 items-start">
      <AIAvatar />
      <div className="flex-1 max-w-[85%]">
        <div className="bg-bg-surface border border-bg-border rounded-lg rounded-tl-sm px-3 py-2.5">
          <p className="text-xs text-text-primary leading-relaxed whitespace-pre-wrap">{msg.content}</p>
        </div>
        <div className="mt-1 ml-1 text-2xs font-mono text-text-dim">
          {new Date(msg.ts).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}

function AIAvatar() {
  return (
    <div className="w-6 h-6 rounded bg-accent-cyan/10 border border-accent-cyan/20 flex items-center justify-center flex-shrink-0 mt-0.5">
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
        <path
          d="M6 1L1 3.5V6.5C1 9 3.1 11.2 6 12 8.9 11.2 11 9 11 6.5V3.5L6 1z"
          fill="#00C2FF"
          fillOpacity={0.2}
          stroke="#00C2FF"
          strokeWidth={0.8}
        />
        <path d="M4 6l1.5 1.5L8 4" stroke="#00C2FF" strokeWidth={0.9} strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="bg-bg-surface border border-bg-border rounded-lg rounded-tl-sm px-3 py-2.5 inline-flex items-center gap-1">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="w-1 h-1 rounded-full bg-text-muted"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            delay: i * 0.2,
          }}
        />
      ))}
    </div>
  );
}
