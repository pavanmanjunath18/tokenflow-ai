import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
  className?: string;
}

export function StatCard({ label, value, sub, accent, className }: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-zinc-800 bg-zinc-900/60 px-5 py-4 flex flex-col gap-1",
        className
      )}
    >
      <p className="text-xs text-zinc-500 uppercase tracking-wider">{label}</p>
      <p className={cn("text-2xl font-bold", accent ? "text-orange-400" : "text-white")}>
        {value}
      </p>
      {sub && <p className="text-xs text-zinc-500">{sub}</p>}
    </div>
  );
}
