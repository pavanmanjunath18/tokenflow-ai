"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Plug2, Building2, Cpu, CreditCard,
  ShieldAlert, Lightbulb, Users, Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard",        label: "Overview",         icon: LayoutDashboard },
  { href: "/integrations",     label: "Integrations",     icon: Plug2 },
  { href: "/departments",      label: "Departments",      icon: Building2 },
  { href: "/models",           label: "Model Usage",      icon: Cpu },
  { href: "/licenses",         label: "License Waste",    icon: CreditCard },
  { href: "/alerts",           label: "Governance",       icon: ShieldAlert },
  { href: "/recommendations",  label: "Recommendations",  icon: Lightbulb },
  { href: "/employees",        label: "Employee Review",  icon: Users },
  { href: "/infrastructure",   label: "Infrastructure",   icon: Activity },
];

export function Sidebar() {
  const path = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-full w-60 bg-zinc-950 border-r border-zinc-800 flex flex-col z-40">
      <div className="px-5 py-5 border-b border-zinc-800">
        <span className="text-lg font-bold text-white tracking-tight">TokenFlow</span>
        <span className="text-lg font-bold text-orange-400 tracking-tight"> AI</span>
        <p className="text-xs text-zinc-500 mt-0.5">Enterprise AI FinOps</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = path === href || path.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                active
                  ? "bg-orange-500/10 text-orange-400 font-medium"
                  : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/60"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="px-5 py-4 border-t border-zinc-800 text-xs text-zinc-600">
        MVP v0.1 · Privacy-aware
      </div>
    </aside>
  );
}
