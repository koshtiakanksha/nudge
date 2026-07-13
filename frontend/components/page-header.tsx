export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="px-8 pt-8 pb-6 border-b border-line">
      <h1 className="font-display text-3xl font-semibold text-ink">{title}</h1>
      {subtitle && <p className="text-slate mt-1.5 text-sm">{subtitle}</p>}
    </div>
  );
}
