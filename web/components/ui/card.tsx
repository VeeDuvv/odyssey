"use client";

import { clsx } from "clsx";
import { motion } from "framer-motion";
import { type ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  glow?: boolean;
  onClick?: () => void;
}

export function Card({ children, className, hover = false, glow = false, onClick }: CardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
      className={clsx(
        "rounded-2xl p-6",
        "glass",
        hover && "glass-hover cursor-pointer transition-all duration-300",
        glow && "glow-subtle",
        className
      )}
      onClick={onClick}
    >
      {children}
    </motion.div>
  );
}

export function StatCard({
  label,
  value,
  change,
  icon,
  color = "indigo",
}: {
  label: string;
  value: string | number;
  change?: string;
  icon?: ReactNode;
  color?: "indigo" | "emerald" | "amber" | "rose";
}) {
  const colorMap = {
    indigo: "from-indigo-500/20 to-indigo-500/5 text-indigo-400",
    emerald: "from-emerald-500/20 to-emerald-500/5 text-emerald-400",
    amber: "from-amber-500/20 to-amber-500/5 text-amber-400",
    rose: "from-rose-500/20 to-rose-500/5 text-rose-400",
  };

  return (
    <Card>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-white/40 font-medium">{label}</p>
          <p className="text-3xl font-semibold tracking-tight mt-1 gradient-text">
            {value}
          </p>
          {change && (
            <p className={clsx("text-xs mt-2 font-medium", colorMap[color].split(" ").pop())}>
              {change}
            </p>
          )}
        </div>
        {icon && (
          <div className={clsx("w-10 h-10 rounded-xl bg-gradient-to-br flex items-center justify-center", colorMap[color])}>
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}
