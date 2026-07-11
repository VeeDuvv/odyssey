"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Brain,
  Globe,
  Users,
  Zap,
  Activity,
  Network,
  Shield,
  TrendingUp,
} from "lucide-react";
import { Card, StatCard } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

const stagger = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
} as const;

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
} as const;

export default function Dashboard() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      {/* Hero */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="mb-12"
      >
        <div className="flex items-center gap-3 mb-2">
          <div className="relative">
            <div className="w-2 h-2 rounded-full bg-emerald-400" />
            <div className="absolute inset-0 w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          </div>
          <span className="text-sm text-white/40 font-medium tracking-wide uppercase">
            System Active
          </span>
          <span className="text-sm text-white/20 font-mono">
            {time.toLocaleTimeString()}
          </span>
        </div>
        <h1 className="text-5xl font-bold tracking-tight gradient-text">
          Odyssey
        </h1>
        <p className="text-lg text-white/40 mt-2 max-w-2xl">
          Your AI-native architecture navigator. Self-evolving, always current,
          guiding enterprises through the AI & Data landscape.
        </p>
      </motion.div>

      {/* Stats Grid */}
      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="grid grid-cols-4 gap-4 mb-8"
      >
        <motion.div variants={fadeUp}>
          <StatCard
            label="Knowledge Nodes"
            value="35+"
            change="Across 7 domains"
            icon={<Globe className="w-5 h-5" />}
            color="indigo"
          />
        </motion.div>
        <motion.div variants={fadeUp}>
          <StatCard
            label="Active Agents"
            value="5"
            change="Navigator, Architect, +3"
            icon={<Brain className="w-5 h-5" />}
            color="emerald"
          />
        </motion.div>
        <motion.div variants={fadeUp}>
          <StatCard
            label="Relationships"
            value="65+"
            change="COMPETES, INTEGRATES, HOSTED"
            icon={<Network className="w-5 h-5" />}
            color="amber"
          />
        </motion.div>
        <motion.div variants={fadeUp}>
          <StatCard
            label="Evolution Engine"
            value="Ready"
            change="Autonomous mode"
            icon={<Zap className="w-5 h-5" />}
            color="rose"
          />
        </motion.div>
      </motion.div>

      {/* Main Grid */}
      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        className="grid grid-cols-3 gap-4"
      >
        {/* Quick Chat */}
        <motion.div variants={fadeUp} className="col-span-2">
          <Link href="/chat">
            <Card hover glow className="h-full group cursor-pointer">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500/20 to-indigo-500/5 flex items-center justify-center">
                  <Zap className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold">Ask Odyssey</h2>
                  <p className="text-sm text-white/35">Architecture decisions, technology comparisons, roadmaps</p>
                </div>
              </div>
              <div className="glass rounded-xl px-4 py-3 text-white/25 text-sm group-hover:text-white/35 transition-colors">
                &quot;What vector database should we use on AWS with 10M embeddings?&quot;
              </div>
              <div className="flex gap-2 mt-4">
                <Badge variant="accent">Recommendations</Badge>
                <Badge variant="accent">Comparisons</Badge>
                <Badge variant="accent">Roadmaps</Badge>
              </div>
            </Card>
          </Link>
        </motion.div>

        {/* Cortex Status */}
        <motion.div variants={fadeUp}>
          <Link href="/cortex">
            <Card hover className="h-full">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/20 to-violet-500/5 flex items-center justify-center">
                  <Brain className="w-5 h-5 text-violet-400" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold">Cortex</h2>
                  <p className="text-sm text-white/35">Self-evolution engine</p>
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-white/40">Evolution Loop</span>
                  <Badge variant="success">Active</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-white/40">Governor</span>
                  <Badge variant="info">Guarding</Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-white/40">Kill Switch</span>
                  <Badge variant="default">Off</Badge>
                </div>
              </div>
            </Card>
          </Link>
        </motion.div>

        {/* Agent Fleet */}
        <motion.div variants={fadeUp} className="col-span-2">
          <Card>
            <div className="flex items-center gap-3 mb-5">
              <Shield className="w-5 h-5 text-white/40" />
              <h2 className="text-lg font-semibold">Agent Fleet</h2>
            </div>
            <div className="grid grid-cols-5 gap-3">
              {[
                { name: "Navigator", role: "Query Orchestrator", icon: "🧭", color: "indigo" },
                { name: "Architect", role: "Recommendations", icon: "🏛️", color: "violet" },
                { name: "Cartographer", role: "Knowledge Builder", icon: "🗺️", color: "emerald" },
                { name: "Sentinel", role: "Landscape Monitor", icon: "👁️", color: "amber" },
                { name: "Chronicler", role: "Temporal Awareness", icon: "📜", color: "cyan" },
              ].map((agent) => (
                <div
                  key={agent.name}
                  className="glass rounded-xl p-4 text-center hover:bg-white/[0.04] transition-colors"
                >
                  <div className="text-2xl mb-2">{agent.icon}</div>
                  <p className="text-sm font-medium">{agent.name}</p>
                  <p className="text-xs text-white/30 mt-0.5">{agent.role}</p>
                  <Badge variant="success" className="mt-2">active</Badge>
                </div>
              ))}
            </div>
          </Card>
        </motion.div>

        {/* Knowledge Domains */}
        <motion.div variants={fadeUp}>
          <Link href="/knowledge">
            <Card hover className="h-full">
              <div className="flex items-center gap-3 mb-4">
                <TrendingUp className="w-5 h-5 text-white/40" />
                <h2 className="text-lg font-semibold">Knowledge</h2>
              </div>
              <div className="space-y-2.5">
                {[
                  { domain: "Data Platforms", count: 8, color: "bg-blue-400" },
                  { domain: "AI Models", count: 6, color: "bg-violet-400" },
                  { domain: "AI Patterns", count: 9, color: "bg-indigo-400" },
                  { domain: "ML Infrastructure", count: 6, color: "bg-emerald-400" },
                  { domain: "Governance", count: 3, color: "bg-amber-400" },
                  { domain: "Cloud", count: 3, color: "bg-cyan-400" },
                ].map((d) => (
                  <div key={d.domain} className="flex items-center gap-3">
                    <div className={`w-1.5 h-1.5 rounded-full ${d.color}`} />
                    <span className="text-sm text-white/50 flex-1">{d.domain}</span>
                    <span className="text-sm font-mono text-white/30">{d.count}</span>
                  </div>
                ))}
              </div>
            </Card>
          </Link>
        </motion.div>
      </motion.div>
    </div>
  );
}
