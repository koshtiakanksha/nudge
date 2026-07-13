import { cn } from "@/lib/format";

export function Card({
  children,
  className,
  padded = true,
}: {
  children: React.ReactNode;
  className?: string;
  padded?: boolean;
}) {
  return (
    <div className={cn("bg-white/60 border border-line rounded-lg", padded && "p-5", className)}>{children}</div>
  );
}

export function CardLabel({ children }: { children: React.ReactNode }) {
  return <p className="text-xs uppercase tracking-wide text-slate mb-1.5">{children}</p>;
}
