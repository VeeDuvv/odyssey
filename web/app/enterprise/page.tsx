"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Building2, Plus, ArrowRight, Settings, Check } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { createEnterprise } from "@/lib/api";
import { useEnterprise } from "@/lib/enterprise-context";

const INDUSTRIES = [
  { value: "technology", label: "Technology" },
  { value: "financial_services", label: "Financial Services" },
  { value: "healthcare", label: "Healthcare" },
  { value: "retail", label: "Retail" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "media", label: "Media" },
  { value: "energy", label: "Energy" },
  { value: "government", label: "Government" },
  { value: "education", label: "Education" },
  { value: "other", label: "Other" },
];

const SCALE_TIERS = [
  {
    value: "startup",
    label: "Startup",
    desc: "< 50 engineers, early data infra",
    scale: { data_volume_gb: 100, daily_ingest_gb: 1, query_volume_per_day: 1000, ml_models_in_production: 0, embedding_count: 100000, concurrent_users: 50, regions: ["us-east-1"] },
  },
  {
    value: "growth",
    label: "Growth",
    desc: "50-200 engineers, scaling systems",
    scale: { data_volume_gb: 5000, daily_ingest_gb: 50, query_volume_per_day: 50000, ml_models_in_production: 5, embedding_count: 5000000, concurrent_users: 500, regions: ["us-east-1", "eu-west-1"] },
  },
  {
    value: "enterprise",
    label: "Enterprise",
    desc: "200+ engineers, mature platform",
    scale: { data_volume_gb: 100000, daily_ingest_gb: 500, query_volume_per_day: 500000, ml_models_in_production: 20, embedding_count: 50000000, concurrent_users: 5000, regions: ["us-east-1", "eu-west-1", "ap-southeast-1"] },
  },
  {
    value: "hyperscale",
    label: "Hyperscale",
    desc: "1000+ engineers, global scale",
    scale: { data_volume_gb: 1000000, daily_ingest_gb: 5000, query_volume_per_day: 5000000, ml_models_in_production: 100, embedding_count: 500000000, concurrent_users: 50000, regions: ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-northeast-1"] },
  },
];

const MATURITY_DIMENSIONS = [
  { key: "data_engineering", label: "Data Engineering" },
  { key: "ml_ops", label: "ML Ops" },
  { key: "gen_ai", label: "Generative AI" },
  { key: "governance", label: "Data Governance" },
  { key: "cloud_native", label: "Cloud Native" },
];

const MATURITY_LABELS = ["", "Exploring", "Experimenting", "Scaling", "Optimizing", "Leading"];
const MATURITY_DESCRIPTIONS = [
  "",
  "Just starting to explore",
  "Running experiments and POCs",
  "Moving to production at scale",
  "Optimizing and automating",
  "Industry-leading practices",
];

const GOAL_PRIORITIES = [
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

const TIME_HORIZONS = [
  { value: "now", label: "Now" },
  { value: "next_quarter", label: "Next Quarter" },
  { value: "next_year", label: "Next Year" },
  { value: "long_term", label: "Long Term" },
];

export default function EnterprisePage() {
  const router = useRouter();
  const { enterpriseId, enterpriseName, setEnterprise, clearEnterprise } = useEnterprise();

  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("technology");
  const [scaleTier, setScaleTier] = useState("startup");
  const [maturity, setMaturity] = useState<Record<string, number>>({
    data_engineering: 1,
    ml_ops: 1,
    gen_ai: 1,
    governance: 1,
    cloud_native: 1,
  });
  const [goalDescription, setGoalDescription] = useState("");
  const [goalPriority, setGoalPriority] = useState("high");
  const [goalHorizon, setGoalHorizon] = useState("next_quarter");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleCreate = async () => {
    if (!name.trim()) return;
    setIsSubmitting(true);
    setError("");

    const selectedScale = SCALE_TIERS.find((t) => t.value === scaleTier)!;
    const overallMaturity = Math.round(
      Object.values(maturity).reduce((a, b) => a + b, 0) / Object.values(maturity).length
    );

    const payload: Record<string, unknown> = {
      name: name.trim(),
      industry,
      scale: selectedScale.scale,
      maturity: {
        overall: overallMaturity,
        ...maturity,
      },
      goals: goalDescription.trim()
        ? [
            {
              id: `goal-${Date.now()}`,
              description: goalDescription.trim(),
              priority: goalPriority,
              time_horizon: goalHorizon,
              measurable_outcome: "",
              related_domains: [],
            },
          ]
        : [],
    };

    try {
      const result = await createEnterprise(payload);
      setEnterprise(result.id, name.trim());
      router.push("/chat");
    } catch {
      setError("Failed to create enterprise profile. Is the API server running?");
    } finally {
      setIsSubmitting(false);
    }
  };

  // If enterprise is already connected, show profile summary
  if (enterpriseId) {
    return (
      <div className="p-8 max-w-[1400px] mx-auto">
        <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl font-bold gradient-text">Enterprise</h1>
          <p className="text-white/35 mt-1">Your organization is connected to Odyssey</p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-2xl mx-auto">
          <Card glow>
            <div className="text-center py-4">
              <div className="w-16 h-16 rounded-2xl bg-emerald-500/15 flex items-center justify-center mx-auto mb-4">
                <Building2 className="w-8 h-8 text-emerald-400" />
              </div>
              <h2 className="text-2xl font-bold mb-2">{enterpriseName}</h2>
              <Badge variant="success">Connected</Badge>
              <p className="text-white/30 text-sm mt-6 max-w-md mx-auto">
                Your enterprise context is active. All chat responses are personalized to your organization.
              </p>
              <div className="flex gap-3 justify-center mt-6">
                <Button onClick={() => router.push("/chat")} icon={<ArrowRight className="w-4 h-4" />}>
                  Go to Chat
                </Button>
                <Button variant="secondary" onClick={() => { clearEnterprise(); }}>
                  Disconnect
                </Button>
              </div>
            </div>
          </Card>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-[900px] mx-auto">
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="text-3xl font-bold gradient-text">Set Up Your Enterprise</h1>
        <p className="text-white/35 mt-1">Tell Odyssey about your organization for personalized recommendations</p>
      </motion.div>

      <div className="space-y-6">
        {/* Section 1: Organization Basics */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <Card>
            <h2 className="text-lg font-semibold mb-5 flex items-center gap-2">
              <Building2 className="w-5 h-5 text-indigo-400" />
              Organization
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-sm text-white/40 mb-2">Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Acme Corp"
                  className="w-full glass rounded-xl px-4 py-3 text-white placeholder:text-white/20 focus:outline-none focus:border-indigo-500/30"
                />
              </div>
              <div>
                <label className="block text-sm text-white/40 mb-2">Industry</label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="w-full glass rounded-xl px-4 py-3 text-white bg-transparent focus:outline-none focus:border-indigo-500/30"
                >
                  {INDUSTRIES.map((ind) => (
                    <option key={ind.value} value={ind.value}>
                      {ind.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Section 2: Scale */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card>
            <h2 className="text-lg font-semibold mb-5">Scale</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {SCALE_TIERS.map((tier) => (
                <button
                  key={tier.value}
                  onClick={() => setScaleTier(tier.value)}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    scaleTier === tier.value
                      ? "bg-indigo-500/15 border-indigo-500/30 text-white"
                      : "glass border-white/[0.06] text-white/50 hover:text-white/70 hover:border-white/10"
                  }`}
                >
                  <div className="font-medium text-sm mb-1">{tier.label}</div>
                  <div className="text-xs text-white/30">{tier.desc}</div>
                  {scaleTier === tier.value && (
                    <Check className="w-4 h-4 text-indigo-400 mt-2" />
                  )}
                </button>
              ))}
            </div>
          </Card>
        </motion.div>

        {/* Section 3: Maturity Assessment */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <Card>
            <h2 className="text-lg font-semibold mb-1">Maturity Assessment</h2>
            <p className="text-sm text-white/25 mb-5">Rate your organization across key dimensions</p>
            <div className="space-y-5">
              {MATURITY_DIMENSIONS.map((dim) => (
                <div key={dim.key}>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-sm text-white/60">{dim.label}</label>
                    <span className="text-xs font-medium text-indigo-400">
                      L{maturity[dim.key]} &mdash; {MATURITY_LABELS[maturity[dim.key]]}
                    </span>
                  </div>
                  <div className="relative">
                    <input
                      type="range"
                      min={1}
                      max={5}
                      step={1}
                      value={maturity[dim.key]}
                      onChange={(e) =>
                        setMaturity((prev) => ({ ...prev, [dim.key]: parseInt(e.target.value) }))
                      }
                      className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-white/10
                        [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-indigo-500 [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:shadow-indigo-500/30 [&::-webkit-slider-thumb]:cursor-pointer
                        [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-indigo-500 [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:cursor-pointer"
                    />
                    {/* Step markers */}
                    <div className="flex justify-between mt-1 px-0.5">
                      {[1, 2, 3, 4, 5].map((level) => (
                        <span
                          key={level}
                          className={`text-[10px] ${
                            maturity[dim.key] >= level ? "text-indigo-400/60" : "text-white/15"
                          }`}
                        >
                          L{level}
                        </span>
                      ))}
                    </div>
                  </div>
                  <p className="text-[11px] text-white/20 mt-1">{MATURITY_DESCRIPTIONS[maturity[dim.key]]}</p>
                </div>
              ))}
            </div>
          </Card>
        </motion.div>

        {/* Section 4: Primary Goal */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Card>
            <h2 className="text-lg font-semibold mb-1">Primary Goal</h2>
            <p className="text-sm text-white/25 mb-5">What&apos;s the most important thing you&apos;re trying to achieve? (optional)</p>
            <div className="space-y-4">
              <input
                type="text"
                value={goalDescription}
                onChange={(e) => setGoalDescription(e.target.value)}
                placeholder="e.g., Implement RAG for customer support, Migrate to real-time ML pipeline"
                className="w-full glass rounded-xl px-4 py-3 text-white placeholder:text-white/20 focus:outline-none focus:border-indigo-500/30"
              />
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-white/40 mb-2">Priority</label>
                  <select
                    value={goalPriority}
                    onChange={(e) => setGoalPriority(e.target.value)}
                    className="w-full glass rounded-xl px-4 py-3 text-white bg-transparent focus:outline-none focus:border-indigo-500/30"
                  >
                    {GOAL_PRIORITIES.map((p) => (
                      <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-white/40 mb-2">Time Horizon</label>
                  <select
                    value={goalHorizon}
                    onChange={(e) => setGoalHorizon(e.target.value)}
                    className="w-full glass rounded-xl px-4 py-3 text-white bg-transparent focus:outline-none focus:border-indigo-500/30"
                  >
                    {TIME_HORIZONS.map((h) => (
                      <option key={h.value} value={h.value}>{h.label}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Submit */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
          {error && (
            <p className="text-sm text-red-400 mb-4">{error}</p>
          )}
          <Button
            onClick={handleCreate}
            disabled={!name.trim() || isSubmitting}
            size="lg"
            icon={<ArrowRight className="w-4 h-4" />}
          >
            {isSubmitting ? "Creating..." : "Start Chatting"}
          </Button>
        </motion.div>
      </div>
    </div>
  );
}
