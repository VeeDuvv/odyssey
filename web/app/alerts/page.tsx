"use client";

import { motion } from "framer-motion";
import { Bell, AlertTriangle, Info, ShieldAlert } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const SAMPLE_ALERTS = [
  {
    id: "1",
    severity: "action_required",
    title: "pgvector 0.8 released with major performance improvements",
    body: "pgvector 0.8 introduces parallel index builds and improved HNSW performance. If you're using pgvector, this could reduce query latency by 40%.",
    affected: ["pgvector"],
    time: "2 hours ago",
  },
  {
    id: "2",
    severity: "warning",
    title: "EU AI Act enforcement begins Q1 2026",
    body: "New compliance requirements for high-risk AI systems. Review your model governance and documentation practices.",
    affected: ["governance"],
    time: "1 day ago",
  },
  {
    id: "3",
    severity: "info",
    title: "Databricks acquires new MLOps startup",
    body: "Databricks continues expanding its ML platform capabilities. Consider implications for your lakehouse strategy.",
    affected: ["databricks", "mlflow"],
    time: "3 days ago",
  },
];

const severityConfig = {
  action_required: { icon: ShieldAlert, color: "text-rose-400", badge: "danger" as const, bg: "from-rose-500/20 to-rose-500/5" },
  warning: { icon: AlertTriangle, color: "text-amber-400", badge: "warning" as const, bg: "from-amber-500/20 to-amber-500/5" },
  info: { icon: Info, color: "text-blue-400", badge: "info" as const, bg: "from-blue-500/20 to-blue-500/5" },
};

export default function AlertsPage() {
  return (
    <div className="p-8 max-w-[1000px] mx-auto">
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-amber-500/20 to-amber-500/5 border border-amber-500/15 flex items-center justify-center">
            <Bell className="w-6 h-6 text-amber-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold gradient-text">Alerts</h1>
            <p className="text-white/35">Proactive landscape changes that affect you</p>
          </div>
        </div>
      </motion.div>

      <div className="space-y-4">
        {SAMPLE_ALERTS.map((alert, i) => {
          const config = severityConfig[alert.severity as keyof typeof severityConfig] || severityConfig.info;
          const Icon = config.icon;
          return (
            <motion.div
              key={alert.id}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
            >
              <Card hover>
                <div className="flex gap-4">
                  <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${config.bg} flex items-center justify-center flex-shrink-0`}>
                    <Icon className={`w-5 h-5 ${config.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4 mb-1">
                      <h3 className="font-semibold text-[15px]">{alert.title}</h3>
                      <Badge variant={config.badge}>{alert.severity.replace("_", " ")}</Badge>
                    </div>
                    <p className="text-sm text-white/40 leading-relaxed">{alert.body}</p>
                    <div className="flex items-center gap-3 mt-3">
                      <div className="flex gap-1.5">
                        {alert.affected.map((tech) => (
                          <Badge key={tech}>{tech}</Badge>
                        ))}
                      </div>
                      <span className="text-xs text-white/20">{alert.time}</span>
                    </div>
                  </div>
                </div>
              </Card>
            </motion.div>
          );
        })}
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="text-center py-12"
      >
        <p className="text-white/15 text-sm">
          Alerts are generated automatically when the landscape changes affect your enterprise.
        </p>
      </motion.div>
    </div>
  );
}
