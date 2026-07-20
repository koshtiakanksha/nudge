"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Receipt,
  Wallet,
  TrendingUp,
  AlertTriangle,
  MessageCircle,
  Settings,
  Repeat,
  ShoppingBag,
  Sliders,
} from "lucide-react";
import { cn } from "@/lib/format";
import { api } from "@/lib/api";
import { AppMode } from "@/types/api";

const NAV_ITEMS = [
  { href: "/", label: "Today", icon: LayoutDashboard },
  { href: "/forecast", label: "Forecast", icon: TrendingUp },
  { href: "/anomalies", label: "Alerts", icon: AlertTriangle },
  { href: "/budget", label: "Budget", icon: Wallet },
  { href: "/scenarios", label: "What If", icon: Sliders },
  { href: "/afford", label: "Can I Afford This?", icon: ShoppingBag },
  { href: "/transactions", label: "Transactions", icon: Receipt },
  { href: "/recurring", label: "Bills", icon: Repeat },
  { href: "/chat", label: "Ask Nudge", icon: MessageCircle },
];

export function Sidebar() {
  const pathname = usePathname();
  const [mode, setMode] = useState<AppMode | null>(null);

  useEffect(() => {
    api.getAppMode().then(setMode).catch(() => setMode(null));
  }, []);

  return (
    <aside className="w-60 shrink-0 border-r border-line bg-paper hidden md:flex flex-col">
      <div className="px-6 pt-8 pb-6">
        <Link href="/" className="flex items-baseline gap-1.5">
          <span className="font-display text-2xl font-semibold text-moss tracking-tight">Nudge</span>
        </Link>
        <p className="text-xs text-slate mt-1">Spend with a second opinion.</p>
        {mode && (
          <div className="mt-3 space-y-1">
            <div className="flex flex-wrap gap-1">
              {mode.badges.map((badge) => (
                <span key={badge} className="text-[10px] bg-gold/10 text-gold px-1.5 py-0.5 rounded-sm">
                  {badge}
                </span>
              ))}
            </div>
            {mode.message && <p className="text-[11px] text-slate leading-snug">{mode.message}</p>}
          </div>
        )}
      </div>

      <nav className="flex-1 px-3 space-y-0.5">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                active ? "bg-moss text-paper font-medium" : "text-ink hover:bg-line/60"
              )}
            >
              <Icon size={17} strokeWidth={2} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="px-3 pb-6">
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
            pathname === "/settings" ? "bg-moss text-paper font-medium" : "text-slate hover:bg-line/60"
          )}
        >
          <Settings size={17} strokeWidth={2} />
          Settings
        </Link>
      </div>
    </aside>
  );
}
