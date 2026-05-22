"use client";

import { useEffect, useState, useCallback } from "react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from "recharts";
import { TrendingUp, AlertTriangle, Filter, X } from "lucide-react";
import { api, DashboardOverview, SpendPoint, DepartmentStat, DashboardParams } from "@/lib/api";
import { StatCard } from "@/components/cards/StatCard";
import { fmt$$, fmtNum } from "@/lib/utils";

const DEPT_COLORS = ["#f97316","#fb923c","#fdba74","#fed7aa","#fff7ed","#fef3c7","#fde68a","#fbbf24"];

export default function DashboardPage() {
  const [overview, setOverview]   = useState<DashboardOverview | null>(null);
  const [spendData, setSpendData] = useState<SpendPoint[]>([]);
  const [deptData, setDeptData]   = useState<DepartmentStat[]>([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);

  // Filter state
  const [departments, setDepartments] = useState<string[]>([]);
  const [providers, setProviders]     = useState<string[]>([]);
  const [filters, setFilters] = useState<DashboardParams>({});
  const [showFilters, setShowFilters] = useState(false);

  const load = useCallback((f: DashboardParams) => {
    setLoading(true);
    setError(null);
    Promise.all([api.overview(f), api.spendOverTime(f), api.departments(f)])
      .then(([o, s, d]) => { setOverview(o); setSpendData(s); setDeptData(d); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load({});
    api.filterOptions().then(o => {
      setDepartments(o.departments);
      setProviders(o.providers);
    }).catch(() => {});
  }, [load]);

  const applyFilter = (key: keyof DashboardParams, value: string) => {
    const next = { ...filters, [key]: value || undefined };
    if (!value) delete next[key];
    setFilters(next);
    load(next);
  };

  const clearFilters = () => {
    setFilters({});
    load({});
  };

  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  if (error) return <ErrorState message={error} />;

  return (
    <div className="p-8 space-y-6">
      {/* Header + filter toggle */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Executive Overview</h1>
          {overview && !loading && (
            <p className="text-sm text-zinc-500 mt-1">
              {overview.period_start} → {overview.period_end}
              {activeFilterCount > 0 && <span className="ml-2 text-orange-400">· {activeFilterCount} filter{activeFilterCount > 1 ? "s" : ""} active</span>}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {activeFilterCount > 0 && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-zinc-400 border border-zinc-700 hover:border-zinc-500 hover:text-zinc-200 transition-colors"
            >
              <X className="h-3 w-3" /> Clear filters
            </button>
          )}
          <button
            onClick={() => setShowFilters(v => !v)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm border transition-colors ${
              showFilters || activeFilterCount > 0
                ? "bg-orange-500/10 border-orange-500/40 text-orange-400"
                : "border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200"
            }`}
          >
            <Filter className="h-3.5 w-3.5" />
            Filters
            {activeFilterCount > 0 && (
              <span className="ml-0.5 bg-orange-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Filter bar */}
      {showFilters && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <FilterSelect
              label="Department"
              value={filters.department ?? ""}
              options={departments}
              onChange={v => applyFilter("department", v)}
            />
            <FilterSelect
              label="Provider"
              value={filters.provider ?? ""}
              options={providers}
              onChange={v => applyFilter("provider", v)}
            />
            <FilterInput
              label="Start date"
              type="date"
              value={filters.start_date ?? ""}
              onChange={v => applyFilter("start_date", v)}
            />
            <FilterInput
              label="End date"
              type="date"
              value={filters.end_date ?? ""}
              onChange={v => applyFilter("end_date", v)}
            />
          </div>
        </div>
      )}

      {loading ? (
        <LoadingState />
      ) : overview ? (
        <>
          {/* KPI grid */}
          <div className="grid grid-cols-2 xl:grid-cols-3 gap-4">
            <StatCard label="Total AI Spend"      value={fmt$$(overview.total_spend)} sub={`${overview.period_start} – ${overview.period_end}`} accent />
            <StatCard label="Projected Monthly"   value={fmt$$(overview.monthly_projected_spend)} sub="30-day extrapolation" />
            <StatCard label="Total Requests"      value={fmtNum(overview.total_requests)} sub={`${fmtNum(overview.total_tokens)} tokens`} />
            <StatCard label="Avg Cost / Request"  value={`$${overview.avg_cost_per_request.toFixed(4)}`} />
            <StatCard label="Estimated Savings"   value={fmt$$(overview.estimated_monthly_savings)} sub="if recs actioned" accent />
            <StatCard label="High-Risk Events"    value={fmtNum(overview.high_risk_events)} sub={`${overview.inactive_licenses} inactive licenses`} />
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
                <XAxis dataKey="date" tick={{ fill: "#71717a", fontSize: 11 }}
                  tickLine={false} axisLine={false} tickFormatter={v => v.slice(5)} interval={13} />
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

          {/* Department bar */}
          {deptData.length > 0 && (
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
          )}

          {/* Top dept callout */}
          <div className="rounded-xl border border-orange-500/20 bg-orange-500/5 px-5 py-4 flex items-center gap-3">
            <TrendingUp className="h-5 w-5 text-orange-400 shrink-0" />
            <p className="text-sm text-zinc-300">
              <span className="font-semibold text-orange-400">{overview.top_spending_department}</span> is the
              top-spending department. Navigate to <span className="text-zinc-100">Departments</span> for a
              full breakdown or <span className="text-zinc-100">Recommendations</span> for savings opportunities.
            </p>
          </div>
        </>
      ) : null}
    </div>
  );
}

function FilterSelect({ label, value, options, onChange }: {
  label: string; value: string; options: string[]; onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs text-zinc-500">{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-200 outline-none focus:border-orange-500/60 transition-colors"
      >
        <option value="">All</option>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}

function FilterInput({ label, type, value, onChange }: {
  label: string; type: string; value: string; onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1">
      <label className="text-xs text-zinc-500">{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-200 outline-none focus:border-orange-500/60 transition-colors"
      />
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-4 animate-pulse">
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
      <p className="text-xs text-zinc-600">Make sure the backend is running and data has been synced.</p>
    </div>
  );
}
