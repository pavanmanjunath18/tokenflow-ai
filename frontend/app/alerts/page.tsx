"use client";

import { useEffect, useState } from "react";
import { ShieldAlert, AlertTriangle, Eye, Ban } from "lucide-react";
import { api } from "@/lib/api";
import { StatCard } from "@/components/cards/StatCard";
import { fmtNum } from "@/lib/utils";

type Summary = {
  total_shadow_events: number; unique_shadow_domains: number;
  blocked_events: number; pii_flag_events: number; high_risk_events: number;
};
type Domain = { domain: string; event_count: number; employee_count: number; pii_count: number; departments: string };
type Alert = {
  timestamp: string; employee_id: string; department: string; domain: string;
  policy_action: string; contains_pii: boolean; pii_types: string; risk_score: number; shadow_ai_flag: boolean;
};

const POLICY_COLOR: Record<string, string> = {
  allow:  "bg-green-500/15 text-green-400 border-green-500/30",
  warn:   "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  block:  "bg-red-500/15 text-red-400 border-red-500/30",
  redact: "bg-purple-500/15 text-purple-400 border-purple-500/30",
};

export default function AlertsPage() {
  const [summary, setSummary]   = useState<Summary | null>(null);
  const [domains, setDomains]   = useState<Domain[]>([]);
  const [alerts, setAlerts]     = useState<Alert[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.governanceSummary(), api.shadowAIDomains(), api.governanceAlerts()])
      .then(([s, d, a]) => { setSummary(s); setDomains(d); setAlerts(a); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="p-8 space-y-4 animate-pulse">
      <div className="h-7 w-56 rounded bg-zinc-800" />
      <div className="grid grid-cols-3 gap-4">{Array.from({length:5}).map((_,i)=><div key={i} className="h-24 rounded-xl bg-zinc-800/60"/>)}</div>
    </div>
  );

  if (error) return (
    <div className="p-8 flex flex-col items-center gap-3 min-h-[50vh] justify-center text-center">
      <AlertTriangle className="h-10 w-10 text-orange-400" />
      <p className="text-zinc-300">{error}</p>
      <p className="text-xs text-zinc-600">Sync the browser connector first: POST /api/integrations/sync/browser</p>
    </div>
  );

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Governance Alerts</h1>
        <p className="text-sm text-zinc-500 mt-1">Shadow AI usage, PII risk flags, and policy violations from browser telemetry</p>
      </div>

      {/* KPIs */}
      {summary && (
        <div className="grid grid-cols-2 xl:grid-cols-5 gap-4">
          <StatCard label="Shadow AI Events"    value={fmtNum(summary.total_shadow_events)} accent />
          <StatCard label="Shadow AI Domains"   value={fmtNum(summary.unique_shadow_domains)} />
          <StatCard label="Blocked Requests"    value={fmtNum(summary.blocked_events)} />
          <StatCard label="PII Flags"           value={fmtNum(summary.pii_flag_events)} accent />
          <StatCard label="High-Risk Events"    value={fmtNum(summary.high_risk_events)} />
        </div>
      )}

      {/* Shadow AI domains table */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Top Shadow AI Domains</h2>
        <div className="rounded-xl border border-zinc-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900/80">
                {["Domain","Events","Employees","PII Flags","Departments"].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {domains.map(d => (
                <tr key={d.domain} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-orange-400">{d.domain}</td>
                  <td className="px-4 py-3 text-zinc-300">{fmtNum(d.event_count)}</td>
                  <td className="px-4 py-3 text-zinc-300">{d.employee_count}</td>
                  <td className="px-4 py-3">
                    {d.pii_count > 0 ? (
                      <span className="text-xs bg-red-500/15 text-red-400 border border-red-500/30 px-2 py-0.5 rounded-full">{d.pii_count}</span>
                    ) : <span className="text-zinc-600">—</span>}
                  </td>
                  <td className="px-4 py-3 text-xs text-zinc-500">{d.departments || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent alerts feed */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">
          Recent Alerts ({alerts.length})
        </h2>
        <div className="space-y-2">
          {alerts.slice(0, 30).map((a, i) => (
            <div key={i} className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-4 py-3 flex items-center gap-4 text-sm flex-wrap">
              <span className="text-zinc-600 text-xs w-36 shrink-0">{new Date(a.timestamp).toLocaleString()}</span>
              <span className="font-mono text-xs text-zinc-400 w-24 shrink-0">{a.employee_id}</span>
              <span className="text-zinc-500 w-28 shrink-0">{a.department}</span>
              <span className="font-mono text-xs text-orange-400 flex-1">{a.domain}</span>
              <div className="flex items-center gap-2 shrink-0">
                {a.shadow_ai_flag && (
                  <span className="flex items-center gap-1 text-xs bg-orange-500/15 text-orange-400 border border-orange-500/30 px-2 py-0.5 rounded-full">
                    <Eye className="h-3 w-3" /> Shadow
                  </span>
                )}
                {a.contains_pii && (
                  <span className="flex items-center gap-1 text-xs bg-red-500/15 text-red-400 border border-red-500/30 px-2 py-0.5 rounded-full">
                    <ShieldAlert className="h-3 w-3" /> PII
                  </span>
                )}
                <span className={`text-xs px-2 py-0.5 rounded-full border ${POLICY_COLOR[a.policy_action] ?? ""}`}>
                  {a.policy_action}
                </span>
                <span className="text-xs text-zinc-600">risk {a.risk_score.toFixed(2)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Privacy notice */}
      <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 px-5 py-3 text-xs text-zinc-500">
        <span className="text-purple-400 font-medium">Privacy note: </span>
        Employee IDs are shown for admin audit purposes only. Raw prompt contents are never stored.
        All governance actions require human review before escalation.
      </div>
    </div>
  );
}
