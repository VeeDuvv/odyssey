"use client";

import { motion } from "framer-motion";
import { GitBranch, ArrowRight, CheckCircle2, Clock, HelpCircle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const DECISION_TEMPLATES = [
  {
    slug: "choose-vector-database",
    question: "Which vector database should we use?",
    domain: "AI Patterns",
    altitude: "tactical",
    options: ["Pinecone", "pgvector", "Weaviate", "Qdrant", "Milvus"],
    drivers: ["Scale", "Latency", "Team size", "Cloud provider"],
  },
  {
    slug: "choose-data-platform",
    question: "What should be our core data platform?",
    domain: "Data Platforms",
    altitude: "strategic",
    options: ["Snowflake", "Databricks", "BigQuery"],
    drivers: ["Data volume", "Use case mix", "Budget", "Team skills"],
  },
  {
    slug: "choose-foundation-model",
    question: "Which foundation model should we use?",
    domain: "AI Models",
    altitude: "strategic",
    options: ["Claude", "GPT-4", "Llama", "Gemini", "Mistral"],
    drivers: ["Use case", "Data sensitivity", "Budget", "Latency"],
  },
  {
    slug: "choose-orchestrator",
    question: "Which workflow orchestrator for our pipelines?",
    domain: "Data Platforms",
    altitude: "tactical",
    options: ["Airflow", "Dagster"],
    drivers: ["Pipeline complexity", "Team preference", "Existing tools"],
  },
  {
    slug: "choose-experiment-tracker",
    question: "Which experiment tracking tool?",
    domain: "ML Infrastructure",
    altitude: "tactical",
    options: ["MLflow", "Weights & Biases"],
    drivers: ["Team size", "Budget", "Self-hosted needs"],
  },
];

const altitudeColors = {
  strategic: "accent",
  tactical: "info",
  operational: "default",
} as const;

export default function DecisionsPage() {
  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-indigo-500/5 border border-indigo-500/15 flex items-center justify-center">
            <GitBranch className="w-6 h-6 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold gradient-text">Decision Navigator</h1>
            <p className="text-white/35">Key architecture decisions you need to make</p>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-2 gap-4">
        {DECISION_TEMPLATES.map((dt, i) => (
          <motion.div
            key={dt.slug}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
          >
            <Card hover className="h-full group cursor-pointer" onClick={() => window.location.href = `/chat`}>
              <div className="flex items-start justify-between mb-3">
                <HelpCircle className="w-5 h-5 text-white/20 flex-shrink-0 mt-0.5" />
                <div className="flex gap-2">
                  <Badge variant={altitudeColors[dt.altitude as keyof typeof altitudeColors] || "default"}>
                    {dt.altitude}
                  </Badge>
                  <Badge>{dt.domain}</Badge>
                </div>
              </div>

              <h3 className="text-lg font-semibold mb-4 group-hover:text-indigo-300 transition-colors">
                {dt.question}
              </h3>

              <div className="flex flex-wrap gap-1.5 mb-4">
                {dt.options.map((opt) => (
                  <span key={opt} className="px-2 py-0.5 rounded-md bg-white/[0.03] text-xs text-white/40 border border-white/[0.04]">
                    {opt}
                  </span>
                ))}
              </div>

              <div className="pt-3 border-t border-white/[0.04] flex items-center justify-between">
                <div className="flex gap-1.5">
                  {dt.drivers.slice(0, 3).map((d) => (
                    <span key={d} className="text-[10px] text-white/20 uppercase tracking-wider">{d}</span>
                  ))}
                </div>
                <ArrowRight className="w-4 h-4 text-white/15 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all" />
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
