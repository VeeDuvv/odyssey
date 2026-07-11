"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Search, ExternalLink, ArrowRight, Database, Cpu, Bot, Shield, Cloud, Users } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { searchKnowledge } from "@/lib/api";

const DOMAINS = [
  { id: "data_platforms", label: "Data Platforms", icon: Database, color: "text-blue-400", bg: "from-blue-500/20 to-blue-500/5" },
  { id: "ml_infrastructure", label: "ML Infrastructure", icon: Cpu, color: "text-emerald-400", bg: "from-emerald-500/20 to-emerald-500/5" },
  { id: "ai_models", label: "AI Models", icon: Bot, color: "text-violet-400", bg: "from-violet-500/20 to-violet-500/5" },
  { id: "ai_patterns", label: "AI Patterns", icon: ArrowRight, color: "text-indigo-400", bg: "from-indigo-500/20 to-indigo-500/5" },
  { id: "data_governance", label: "Governance", icon: Shield, color: "text-amber-400", bg: "from-amber-500/20 to-amber-500/5" },
  { id: "cloud_deployment", label: "Cloud", icon: Cloud, color: "text-cyan-400", bg: "from-cyan-500/20 to-cyan-500/5" },
];

const STATUS_BADGES: Record<string, "success" | "info" | "warning" | "danger" | "default"> = {
  emerging: "info",
  growing: "success",
  mature: "default",
  declining: "warning",
  deprecated: "danger",
};

interface TechResult {
  id: string;
  name: string;
  category: string;
  domain: string;
  status: string;
  description: string;
  vendor: string;
  confidence: number;
}

export default function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<TechResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);

  const handleSearch = async (searchQuery?: string, domain?: string) => {
    const q = searchQuery || query;
    if (!q.trim()) return;

    setIsSearching(true);
    try {
      const data = await searchKnowledge(q + (domain ? ` ${domain}` : ""));
      setResults(data.results as unknown as TechResult[]);
    } catch {
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold gradient-text">Knowledge Graph</h1>
        <p className="text-white/35 mt-1">
          Explore the continuously-updated AI & Data technology landscape
        </p>
      </motion.div>

      {/* Search */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-8"
      >
        <div className="relative">
          <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-white/20" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Search technologies, patterns, capabilities..."
            className="w-full glass rounded-2xl px-14 py-4 text-[15px] text-white placeholder:text-white/20 focus:outline-none focus:border-indigo-500/30 transition-colors"
          />
          {isSearching && (
            <div className="absolute right-5 top-1/2 -translate-y-1/2">
              <div className="w-5 h-5 border-2 border-indigo-400/30 border-t-indigo-400 rounded-full animate-spin" />
            </div>
          )}
        </div>
      </motion.div>

      {/* Domain filters */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="flex gap-2 mb-8 flex-wrap"
      >
        {DOMAINS.map((domain) => {
          const Icon = domain.icon;
          const isActive = selectedDomain === domain.id;
          return (
            <button
              key={domain.id}
              onClick={() => {
                setSelectedDomain(isActive ? null : domain.id);
                setQuery(domain.label);
                handleSearch(domain.label, domain.id);
              }}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                isActive
                  ? "bg-white/10 text-white border border-white/15"
                  : "glass text-white/40 hover:text-white/60 hover:bg-white/[0.04]"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? domain.color : ""}`} />
              {domain.label}
            </button>
          );
        })}
      </motion.div>

      {/* Results */}
      {results.length > 0 ? (
        <div className="grid grid-cols-2 gap-4">
          {results.map((tech, i) => (
            <motion.div
              key={tech.id || i}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
            >
              <Card hover className="h-full">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-lg font-semibold">{tech.name}</h3>
                    <p className="text-xs text-white/30 mt-0.5">
                      {tech.category?.replace(/_/g, " ")} · {tech.vendor}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Badge variant={STATUS_BADGES[tech.status] || "default"}>
                      {tech.status}
                    </Badge>
                  </div>
                </div>
                <p className="text-sm text-white/45 leading-relaxed">
                  {tech.description}
                </p>
                <div className="flex items-center justify-between mt-4 pt-3 border-t border-white/[0.04]">
                  <div className="flex gap-2">
                    <Badge>{tech.domain?.replace(/_/g, " ")}</Badge>
                  </div>
                  {tech.confidence !== undefined && (
                    <div className="flex items-center gap-1.5">
                      <div className="w-16 h-1.5 rounded-full bg-white/5 overflow-hidden">
                        <div
                          className="h-full rounded-full bg-indigo-400/50"
                          style={{ width: `${(tech.confidence || 0) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-white/20 font-mono">
                        {Math.round((tech.confidence || 0) * 100)}%
                      </span>
                    </div>
                  )}
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      ) : (
        !isSearching && (
          <div className="text-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mx-auto mb-4">
              <Search className="w-7 h-7 text-white/15" />
            </div>
            <p className="text-white/25 text-lg">
              Search or select a domain to explore
            </p>
            <p className="text-white/15 text-sm mt-1">
              35+ technologies across 7 domains with 65+ relationships
            </p>
          </div>
        )
      )}
    </div>
  );
}
