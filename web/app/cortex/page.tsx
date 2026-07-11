"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Brain,
  Play,
  Square,
  RotateCw,
  ShieldAlert,
  ShieldCheck,
  Activity,
  Gauge,
  AlertTriangle,
  Zap,
} from "lucide-react";
import { Card, StatCard } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export default function CortexPage() {
  const [isRunning, setIsRunning] = useState(false);
  const [killSwitch, setKillSwitch] = useState(false);
  const [cycleCount, setCycleCount] = useState(0);
  const [lastCycleResult, setLastCycleResult] = useState<Record<string, unknown> | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const triggerCycle = async () => {
    setIsLoading(true);
    try {
      const res = await fetch("/api/admin/evolution/cycle", {
        method: "POST",
        headers: { "X-API-Key": "odyssey-dev-key" },
      });
      const data = await res.json();
      setLastCycleResult(data);
      setCycleCount((c) => c + 1);
    } catch {
      setLastCycleResult({ error: "Failed to connect to backend" });
    } finally {
      setIsLoading(false);
    }
  };

  const toggleKillSwitch = async () => {
    const endpoint = killSwitch ? "deactivate" : "activate";
    try {
      await fetch(`/api/admin/governor/kill-switch/${endpoint}`, {
        method: "POST",
        headers: { "X-API-Key": "odyssey-dev-key" },
      });
      setKillSwitch(!killSwitch);
    } catch {
      // Handle error
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
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center glow-accent">
            <Brain className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold gradient-text">Cortex</h1>
            <p className="text-white/35">
              Autonomous self-evolution nervous system
            </p>
          </div>
        </div>
      </motion.div>

      {/* Evolution Loop Visualization */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-8"
      >
        <Card glow>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold">Evolution Loop</h2>
            <div className="flex items-center gap-3">
              <Badge variant={isRunning ? "success" : "default"}>
                {isRunning ? "Running" : "Idle"}
              </Badge>
              <Badge variant={killSwitch ? "danger" : "success"}>
                Kill Switch: {killSwitch ? "ON" : "OFF"}
              </Badge>
            </div>
          </div>

          {/* Loop stages */}
          <div className="flex items-center justify-between mb-8 px-4">
            {[
              { stage: "SENSE", icon: Activity, desc: "Collect telemetry", color: "text-blue-400" },
              { stage: "ASSESS", icon: Gauge, desc: "Detect gaps", color: "text-emerald-400" },
              { stage: "PLAN", icon: Brain, desc: "Propose evolution", color: "text-violet-400" },
              { stage: "EVOLVE", icon: Zap, desc: "Execute changes", color: "text-amber-400" },
              { stage: "VALIDATE", icon: ShieldCheck, desc: "Verify quality", color: "text-indigo-400" },
            ].map((step, i) => {
              const Icon = step.icon;
              return (
                <div key={step.stage} className="flex items-center">
                  <div className="text-center">
                    <div className={`w-14 h-14 rounded-2xl glass flex items-center justify-center mb-2 ${isLoading && i === 0 ? "animate-pulse" : ""}`}>
                      <Icon className={`w-6 h-6 ${step.color}`} />
                    </div>
                    <p className="text-xs font-semibold text-white/60">{step.stage}</p>
                    <p className="text-[10px] text-white/25 mt-0.5">{step.desc}</p>
                  </div>
                  {i < 4 && (
                    <div className="w-12 h-[1px] bg-gradient-to-r from-white/10 to-white/5 mx-2 mt-[-20px]" />
                  )}
                </div>
              );
            })}
          </div>

          {/* Controls */}
          <div className="flex gap-3">
            <Button
              onClick={triggerCycle}
              disabled={isLoading || killSwitch}
              icon={<RotateCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />}
            >
              Run Cycle
            </Button>
            <Button
              variant="secondary"
              onClick={() => setIsRunning(!isRunning)}
              disabled={killSwitch}
              icon={isRunning ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            >
              {isRunning ? "Stop Loop" : "Start Loop"}
            </Button>
            <Button
              variant={killSwitch ? "secondary" : "danger"}
              onClick={toggleKillSwitch}
              icon={<ShieldAlert className="w-4 h-4" />}
            >
              {killSwitch ? "Deactivate Kill Switch" : "Kill Switch"}
            </Button>
          </div>
        </Card>
      </motion.div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Evolution Cycles"
          value={cycleCount}
          icon={<RotateCw className="w-5 h-5" />}
          color="indigo"
        />
        <StatCard
          label="Agents Spawned"
          value={0}
          change="This week"
          icon={<Zap className="w-5 h-5" />}
          color="emerald"
        />
        <StatCard
          label="Quality Gate"
          value="15%"
          change="Regression threshold"
          icon={<ShieldCheck className="w-5 h-5" />}
          color="amber"
        />
        <StatCard
          label="Rollbacks"
          value={0}
          change="Last 24h"
          icon={<AlertTriangle className="w-5 h-5" />}
          color="rose"
        />
      </div>

      {/* Governor Limits */}
      <div className="grid grid-cols-2 gap-4 mb-8">
        <Card>
          <h3 className="text-lg font-semibold mb-4">Governor Limits</h3>
          <div className="space-y-3">
            {[
              { label: "Max new agents / week", value: "1" },
              { label: "Max prompt mods / day", value: "3" },
              { label: "Max ontology extensions / day", value: "1" },
              { label: "Max total agents", value: "20" },
              { label: "Canary duration", value: "48h" },
              { label: "Quality regression threshold", value: "15%" },
            ].map((limit) => (
              <div key={limit.label} className="flex justify-between items-center py-1.5 border-b border-white/[0.03] last:border-0">
                <span className="text-sm text-white/40">{limit.label}</span>
                <span className="text-sm font-mono text-white/70">{limit.value}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h3 className="text-lg font-semibold mb-4">Last Cycle Result</h3>
          {lastCycleResult ? (
            <pre className="text-xs text-white/40 font-mono overflow-auto max-h-64 whitespace-pre-wrap">
              {JSON.stringify(lastCycleResult, null, 2)}
            </pre>
          ) : (
            <div className="text-center py-8">
              <p className="text-white/20 text-sm">No cycle run yet</p>
              <p className="text-white/10 text-xs mt-1">Click &quot;Run Cycle&quot; to trigger</p>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
