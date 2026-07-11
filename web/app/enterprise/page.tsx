"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Building2, Plus, ArrowRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const MATURITY_LABELS = ["", "Exploring", "Experimenting", "Scaling", "Optimizing", "Leading"];

export default function EnterprisePage() {
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("technology");
  const [created, setCreated] = useState<{ id: string; name: string } | null>(null);

  const handleCreate = async () => {
    if (!name.trim()) return;
    try {
      const res = await fetch("/api/enterprise", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": "odyssey-dev-key" },
        body: JSON.stringify({ name, industry }),
      });
      const data = await res.json();
      setCreated(data);
      setShowCreate(false);
    } catch {
      // Handle error
    }
  };

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="text-3xl font-bold gradient-text">Enterprise</h1>
        <p className="text-white/35 mt-1">Connect your organization to Odyssey</p>
      </motion.div>

      {!created && !showCreate ? (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-lg mx-auto text-center py-20">
          <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-indigo-500/20 to-violet-500/10 border border-indigo-500/15 flex items-center justify-center mx-auto mb-6">
            <Building2 className="w-10 h-10 text-indigo-400/60" />
          </div>
          <h2 className="text-2xl font-bold mb-3">Connect your enterprise</h2>
          <p className="text-white/35 mb-8 leading-relaxed">
            Tell Odyssey about your organization — tech stack, maturity level, constraints, and goals.
            Get personalized architecture recommendations.
          </p>
          <Button onClick={() => setShowCreate(true)} icon={<Plus className="w-4 h-4" />} size="lg">
            Create Enterprise Profile
          </Button>
        </motion.div>
      ) : showCreate ? (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-lg mx-auto">
          <Card glow>
            <h2 className="text-xl font-semibold mb-6">New Enterprise Profile</h2>
            <div className="space-y-5">
              <div>
                <label className="block text-sm text-white/40 mb-2">Organization Name</label>
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
                  <option value="technology">Technology</option>
                  <option value="financial_services">Financial Services</option>
                  <option value="healthcare">Healthcare</option>
                  <option value="retail">Retail</option>
                  <option value="manufacturing">Manufacturing</option>
                  <option value="media">Media</option>
                  <option value="energy">Energy</option>
                  <option value="government">Government</option>
                  <option value="education">Education</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="flex gap-3 pt-2">
                <Button onClick={handleCreate} disabled={!name.trim()}>Create Profile</Button>
                <Button variant="ghost" onClick={() => setShowCreate(false)}>Cancel</Button>
              </div>
            </div>
          </Card>
        </motion.div>
      ) : (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-2xl mx-auto">
          <Card glow>
            <div className="text-center py-4">
              <div className="w-16 h-16 rounded-2xl bg-emerald-500/15 flex items-center justify-center mx-auto mb-4">
                <Building2 className="w-8 h-8 text-emerald-400" />
              </div>
              <h2 className="text-2xl font-bold mb-2">Enterprise Connected</h2>
              <p className="text-white/40 mb-2">{created?.name}</p>
              <Badge variant="success">ID: {created?.id}</Badge>
              <p className="text-white/30 text-sm mt-6 max-w-md mx-auto">
                Your enterprise profile is live. Go to Chat and Odyssey will tailor recommendations
                to your organization&apos;s context.
              </p>
              <div className="flex gap-3 justify-center mt-6">
                <Button onClick={() => window.location.href = "/chat"} icon={<ArrowRight className="w-4 h-4" />}>
                  Start Chatting
                </Button>
                <Button variant="secondary" onClick={() => { setCreated(null); setShowCreate(false); }}>
                  Create Another
                </Button>
              </div>
            </div>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
