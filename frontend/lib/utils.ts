import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function fmt$$(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(n);
}

export function fmtNum(n: number) {
  return new Intl.NumberFormat("en-US").format(n);
}

export const SEVERITY_COLOR: Record<string, string> = {
  critical: "bg-red-500/15 text-red-400 border-red-500/30",
  high:     "bg-orange-500/15 text-orange-400 border-orange-500/30",
  medium:   "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  low:      "bg-blue-500/15 text-blue-400 border-blue-500/30",
};

export const STATUS_COLOR: Record<string, string> = {
  pending:       "bg-slate-500/15 text-slate-400 border-slate-500/30",
  accepted:      "bg-green-500/15 text-green-400 border-green-500/30",
  rejected:      "bg-red-500/15 text-red-400 border-red-500/30",
  investigating: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  resolved:      "bg-teal-500/15 text-teal-400 border-teal-500/30",
};
