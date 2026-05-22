"use client";

import { useEffect, useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from "recharts";
import { TrendingUp, DollarSign, Zap, AlertTriangle, Lightbulb, CreditCard } from "lucide-react";
import { api, DashboardOverview, SpendPoint, DepartmentStat } from "@/lib/api";
import { StatCard } from "@/components/cards/StatCard";
import { fmt$$, fmtNum } from "@/lib/utils";

const DEPT_COLORS = ["#f97316","#fb923c","#fdba74","#fed7aa","#fff7ed","#fef3c7","#fde68a","#fbbf24"];

export default function DashboardPage() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [spendData, setSpendData] = useState<SpendPoint[]>([]);
  const [deptData, setDeptData] = useState<DepartmentStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.overview(), api.spendOverTime(), api.departments()])
      .then(([o, s, d]) => { setOverview(o); setSpendData(s); setDeptData(d); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingState />;
  if (error)   return <ErrorState message={error} />;
  if (!overview) return null;

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Executive Overview</h1>
        <p className="text-sm text-zinc-500 mt-1">
          {overview.period_start} → {overview.period_end} · synthetic enterprise AI telemetry
        </p>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-2 xl:grid-cols-3 gap-4">
        <StatCard label="Total AI Spend" value={fmt$$(overview.total_spend)} sub={`${overview.period_start} – ${overview.period_end}`} accent />
        <StatCard label="Projected Monthly" value={fmt$$(overview.monthly_projected_spend)} sub="30-day extrapolation" />
        <StatCard label="Total Requests" value={fmtNum(overview.total_requests)} sub={`${fmtNum(overview.total_tokens)} tokens`} />
        <StatCard label="Avg Cost / Request" value={`$${overview.avg_cost_per_request.toFixed(4)}`} />
        <StatCard label="Estimated Savings" value={fmt$$(overview.estimated_monthly_savings)} sub="if recs actioned" accent />
        <StatCard label="High-Risk Events" value={fmtNum(overview.high_risk_events)} sub={`${overview.inactive_licenses} inactive licenses`} />
      </div>

      {/* Spend chart */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6">
        <h2 className="text-sm font-semibold text-zinc-300 mb-4">Daily AI Spend</h2>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={spendData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#f97316" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              tick={{ fill: "#71717a", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={v => v.slice(5)}
              interval={13}
            />
            <YAxis tick={{ fill: "#71717a", fontSize: 11 }} tickLine={false} axisLine={false}
              tickFormatter={v => `$${v}`} width={42} />
            <Tooltip
              contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8 }}
              labelStyle={{ color: "#a1a1aa" }}
              formatter={(v) => [fmt$$(Number(v ?? 0)), "Spend"]}
            />
            <Area type="monotone" dataKey="cost_usd" stroke="#f97316" fill="url(#spendGrad)" strokeWidth={2} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Department spend bar */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6">
        <h2 className="text-sm font-semibold text-zinc-300 mb-4">Spend by Department</h2>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={deptData} layout="vertical" margin={{ top: 0, right: 16, left: 80, bottom: 0 }}>
            <XAxis type="number" tick={{ fill: "#71717a", fontSize: 11 }} tickLine={false} axisLine={false}
              tickFormatter={v => `$${v}`} />
            <YAxis type="category" dataKey="department" tick={{ fill: "#a1a1aa", fontSize: 12 }} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8 }}
              formatter={(v) => [fmt$$(Number(v ?? 0)), "Spend"]}
            />
            <Bar dataKey="total_cost" radius={[0, 4, 4, 0]}>
              {deptData.map((_, i) => <Cell key={i} fill={DEPT_COLORS[i % DEPT_COLORS.length]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top department callout */}
      <div className="rounded-xl border border-orange-500/20 bg-orange-500/5 px-5 py-4 flex items-center gap-3">
        <TrendingUp className="h-5 w-5 text-orange-400 shrink-0" />
        <p className="text-sm text-zinc-300">
          <span className="font-semibold text-orange-400">{overview.top_spending_department}</span> is the
          top-spending department. Navigate to <span className="text-zinc-100">Departments</span> for a
          full breakdown or <span className="text-zinc-100">Recommendations</span> for savings opportunities.
        </p>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="p-8 space-y-4 animate-pulse">
      <div className="h-7 w-48 rounded bg-zinc-800" />
      <div className="grid grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-zinc-800/60" />
        ))}
      </div>
      <div className="h-64 rounded-xl bg-zinc-800/60" />
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="p-8 flex flex-col items-center justify-center gap-4 text-center min-h-[50vh]">
      <AlertTriangle className="h-10 w-10 text-orange-400" />
      <p className="text-zinc-300 font-medium">Could not load dashboard data</p>
      <p className="text-sm text-zinc-500 max-w-md">{message}</p>
      <p className="text-xs text-zinc-600">Make sure the backend is running on port 8000 and data has been synced.</p>
    </div>
  );
}
