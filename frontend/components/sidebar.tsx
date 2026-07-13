"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Receipt,
  Wallet,
  TrendingUp,
  Tag,
  MapPin,
  MessageCircle,
  Settings,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/format";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/transactions", label: "Transactions", icon: Receipt },
  { href: "/budget", label: "Budget", icon: Wallet },
  { href: "/forecast", label: "Forecast", icon: TrendingUp },
  { href: "/anomalies", label: "Unusual Activity", icon: AlertTriangle },
  { href: "/price-watch", label: "Price Watch", icon: Tag },
  { href: "/deals", label: "Local Deals", icon: MapPin },
  { href: "/chat", label: "Ask Nudge", icon: MessageCircle },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 shrink-0 border-r border-line bg-paper hidden md:flex flex-col">
      <div className="px-6 pt-8 pb-6">
        <Link href="/" className="flex items-baseline gap-1.5">
          <span className="font-display text-2xl font-semibold text-moss tracking-tight">Nudge</span>
        </Link>
        <p className="text-xs text-slate mt-1">Your money, gently managed.</p>
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
