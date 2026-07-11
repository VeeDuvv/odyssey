"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import {
  Compass,
  MessageCircle,
  Globe,
  Building2,
  GitBranch,
  Bell,
  Brain,
  Sparkles,
} from "lucide-react";

const navigation = [
  { name: "Dashboard", href: "/", icon: Compass },
  { name: "Chat", href: "/chat", icon: MessageCircle },
  { name: "Knowledge", href: "/knowledge", icon: Globe },
  { name: "Enterprise", href: "/enterprise", icon: Building2 },
  { name: "Decisions", href: "/decisions", icon: GitBranch },
  { name: "Alerts", href: "/alerts", icon: Bell },
  { name: "Cortex", href: "/cortex", icon: Brain },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-[72px] flex flex-col items-center py-6 z-50 glass-strong">
      {/* Logo */}
      <Link href="/" className="mb-8 group">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center glow-accent transition-transform duration-300 group-hover:scale-110">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
      </Link>

      {/* Navigation */}
      <nav className="flex flex-col items-center gap-1 flex-1">
        {navigation.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              href={item.href}
              className={clsx(
                "w-11 h-11 rounded-xl flex items-center justify-center transition-all duration-200 group relative",
                isActive
                  ? "bg-white/10 text-white"
                  : "text-white/35 hover:text-white/70 hover:bg-white/5"
              )}
            >
              <Icon className="w-[18px] h-[18px]" strokeWidth={isActive ? 2 : 1.5} />

              {/* Active indicator */}
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-[2px] w-1 h-5 rounded-full bg-indigo-500" />
              )}

              {/* Tooltip */}
              <div className="absolute left-full ml-3 px-2.5 py-1 rounded-lg bg-white/10 backdrop-blur-xl text-xs font-medium text-white whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity duration-200">
                {item.name}
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Status dot */}
      <div className="relative">
        <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 pulse-ring" />
      </div>
    </aside>
  );
}
