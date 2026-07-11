"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Sparkles, User, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { sendChat, type ChatResponse } from "@/lib/api";
import type { Message, Altitude } from "@/lib/types";

const ALTITUDE_OPTIONS: { value: Altitude; label: string; desc: string }[] = [
  { value: "strategic", label: "Strategic", desc: "CTO / VP level" },
  { value: "tactical", label: "Tactical", desc: "Architecture team" },
  { value: "operational", label: "Operational", desc: "Engineering" },
];

const EXAMPLE_QUERIES = [
  "What vector database should we use on AWS with 10M embeddings?",
  "Compare Snowflake vs Databricks for a healthcare company",
  "Build us a 6-month AI platform roadmap",
  "Should we use RAG or fine-tuning for our customer support bot?",
  "What changed in the ML infrastructure landscape recently?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [altitude, setAltitude] = useState<Altitude>("tactical");
  const [showAltitude, setShowAltitude] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response: ChatResponse = await sendChat(input.trim(), undefined, altitude);
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.content,
        agent: response.agent,
        confidence: response.confidence,
        follow_up_questions: response.follow_up_questions,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      const errorMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "I couldn't connect to the Odyssey backend. Make sure the API server is running on localhost:8000.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="h-screen flex flex-col">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        {isEmpty ? (
          /* Empty state */
          <div className="h-full flex flex-col items-center justify-center px-8">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5 }}
              className="text-center max-w-2xl"
            >
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center mx-auto mb-6 glow-accent">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <h1 className="text-3xl font-bold gradient-text mb-3">
                Ask Odyssey anything
              </h1>
              <p className="text-white/35 mb-10">
                Architecture recommendations, technology comparisons, migration roadmaps, or just explore the landscape.
              </p>

              <div className="grid grid-cols-1 gap-2">
                {EXAMPLE_QUERIES.map((query, i) => (
                  <motion.button
                    key={i}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    onClick={() => setInput(query)}
                    className="text-left px-4 py-3 rounded-xl glass glass-hover text-sm text-white/50 hover:text-white/70 transition-colors"
                  >
                    {query}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          </div>
        ) : (
          /* Messages */
          <div className="max-w-3xl mx-auto px-8 py-8 space-y-6">
            <AnimatePresence>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className={`flex gap-4 ${msg.role === "user" ? "justify-end" : ""}`}
                >
                  {msg.role === "assistant" && (
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center flex-shrink-0 mt-1">
                      <Sparkles className="w-4 h-4 text-white" />
                    </div>
                  )}
                  <div
                    className={`max-w-[85%] ${
                      msg.role === "user"
                        ? "bg-indigo-500/15 border border-indigo-500/20 rounded-2xl rounded-tr-md px-5 py-3"
                        : ""
                    }`}
                  >
                    {msg.role === "assistant" && msg.agent && (
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="accent">{msg.agent}</Badge>
                        {msg.confidence !== undefined && (
                          <span className="text-xs text-white/25">
                            {Math.round(msg.confidence * 100)}% confidence
                          </span>
                        )}
                      </div>
                    )}
                    <div className="text-[15px] leading-relaxed text-white/80 whitespace-pre-wrap">
                      {msg.content}
                    </div>
                    {msg.follow_up_questions && msg.follow_up_questions.length > 0 && (
                      <div className="mt-4 space-y-1.5">
                        <p className="text-xs text-white/25 uppercase tracking-wider font-medium">Follow up</p>
                        {msg.follow_up_questions.map((q, i) => (
                          <button
                            key={i}
                            onClick={() => setInput(q)}
                            className="block text-sm text-indigo-400/70 hover:text-indigo-400 transition-colors text-left"
                          >
                            → {q}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  {msg.role === "user" && (
                    <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0 mt-1">
                      <User className="w-4 h-4 text-white/40" />
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>

            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex gap-4"
              >
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-4 h-4 text-white animate-pulse" />
                </div>
                <div className="flex items-center gap-1.5 py-3">
                  <div className="w-1.5 h-1.5 rounded-full bg-white/20 animate-bounce" style={{ animationDelay: "0ms" }} />
                  <div className="w-1.5 h-1.5 rounded-full bg-white/20 animate-bounce" style={{ animationDelay: "150ms" }} />
                  <div className="w-1.5 h-1.5 rounded-full bg-white/20 animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-white/[0.04] bg-[var(--color-bg)]/80 backdrop-blur-xl">
        <div className="max-w-3xl mx-auto px-8 py-4">
          {/* Altitude selector */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs text-white/25 uppercase tracking-wider">Altitude</span>
            <div className="flex gap-1">
              {ALTITUDE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setAltitude(opt.value)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                    altitude === opt.value
                      ? "bg-indigo-500/15 text-indigo-400 border border-indigo-500/25"
                      : "text-white/30 hover:text-white/50 hover:bg-white/5"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Input */}
          <div className="relative glass rounded-2xl focus-within:border-indigo-500/30 transition-colors">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about architecture, compare technologies, generate roadmaps..."
              rows={1}
              className="w-full bg-transparent px-5 py-4 pr-14 text-[15px] text-white placeholder:text-white/20 resize-none focus:outline-none"
              style={{ minHeight: "56px", maxHeight: "200px" }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = "56px";
                target.style.height = Math.min(target.scrollHeight, 200) + "px";
              }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="absolute right-3 bottom-3 w-9 h-9 rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:bg-white/5 disabled:text-white/15 flex items-center justify-center text-white transition-all active:scale-95"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
