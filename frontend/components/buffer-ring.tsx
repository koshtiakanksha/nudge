"use client";

import { formatPercent } from "@/lib/format";

interface BufferRingProps {
  status: number; // 0-1
  size?: number;
}

/**
 * The signature visual element of Nudge: a hand-drawn-feeling ring gauge
 * showing how much of the monthly "safety buffer" remains. Modeled after
 * a notebook ledger annotation rather than a generic progress donut —
 * intentionally a little imperfect, with a tick mark and label like a
 * margin note.
 */
export function BufferRing({ status, size = 140 }: BufferRingProps) {
  const clamped = Math.max(0, Math.min(1, status));
  const radius = size / 2 - 10;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped);

  const color = clamped > 0.5 ? "#2F5D50" : clamped > 0.2 ? "#C9A24B" : "#C1622D";

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#DDD6C5"
          strokeWidth={9}
          strokeLinecap="round"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={9}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.6s ease, stroke 0.3s ease" }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-display text-3xl font-semibold leading-none" style={{ color }}>
          {formatPercent(clamped)}
        </span>
        <span className="text-[11px] text-slate mt-1 tracking-wide uppercase">buffer left</span>
      </div>
    </div>
  );
}
