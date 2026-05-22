"use client";

import { useEffect, useState } from "react";
import { Activity, AlertTriangle, CheckCircle2 } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { api } from "@/lib/api";
import { StatCard } from "@/components/cards/StatCard";
import { fmtNum } from "@/lib/utils";

type Summary = {
  total_requests: number; total_errors: number; overall_error_rate: number;
  avg_latency_ms: number; p95_latency_ms: number; degraded_pods: number; total_restarts: number;
};
type Pod = {
  pod_name: string; cluster: string; avg_request_count: number; avg_error_rate: number;
  avg_latency_ms: number; p95_latency_ms: number; avg_cpu_percent: number;
  avg_memory_mb: number; total_restarts: number; latest_status: string;
};
type LatencyPoint = { date: string; avg_latency_ms: number; p95_latency_ms: number };

export default function InfrastructurePage() {
  const [summary, setSummary]         = useState<Summary | null>(null);
  const [pods, setPods]               = useState<Pod[]>([]);
  const [latency, setLatency]         = useState<LatencyPoint[]>([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.infraSummary(), api.podStats(), api.latencyOverTime()])
      .then(([s, p, l]) => { setSummary(s); setPods(p); setLatency(l); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="p-8 space-y-4 animate-pulse">
      <div className="h-7 w-56 rounded bg-zinc-800" />
      <div className="grid grid-cols-4 gap-4">{Array.from({length:4}).map((_,i)=><div key={i} className="h-24 rounded-xl bg-zinc-800/60"/>)}</div>
    </div>
  );

  if (error) return (
    <div className="p-8 flex flex-col items-center gap-3 min-h-[50vh] justify-center text-center">
      <AlertTriangle className="h-10 w-10 text-orange-400" />
      <p className="text-zinc-300">{error}</p>
      <p className="text-xs text-zinc-600">Sync the kubernetes connector first: POST /api/integrations/sync/kubernetes</p>
    </div>
  );

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Infrastructure Health</h1>
        <p className="text-sm text-zinc-500 mt-1">AI gateway pod metrics from Kubernetes (synthetic data)</p>
      </div>

      {summary && (
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          <StatCard label="Total Requests"   value={fmtNum(summary.total_requests)} />
          <StatCard label="Error Rate"       value={`${(summary.overall_error_rate * 100).toFixed(2)}%`}
            accent={summary.overall_error_rate > 0.02} />
          <StatCard label="Avg Latency"      value={`${summary.avg_latency_ms.toFixed(0)}ms`} />
          <StatCard label="p95 Latency"      value={`${summary.p95_latency_ms.toFixed(0)}ms`} />
          <StatCard label="Degraded Pods"    value={String(summary.degraded_pods)}
            accent={summary.degraded_pods > 0} />
          <StatCard label="Total Restarts"   value={String(summary.total_restarts)}
            accent={summary.total_restarts > 5} />
          <StatCard label="Total Errors"     value={fmtNum(summary.total_errors)} />
          <StatCard label="Total Errors"     value={fmtNum(summary.total_errors)} />
        </div>
      )}

      {/* Latency over time */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6">
        <h2 className="text-sm font-semibold text-zinc-300 mb-4">Gateway Latency Over Time</h2>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={latency} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <XAxis dataKey="date" tick={{ fill: "#71717a", fontSize: 11 }} tickLine={false} axisLine={false}
              tickFormatter={v => v.slice(5)} interval={13} />
            <YAxis tick={{ fill: "#71717a", fontSize: 11 }} tickLine={false} axisLine={false}
              tickFormatter={v => `${v}ms`} width={52} />
            <Tooltip
              contentStyle={{ background: "#18181b", border: "1px solid #3f3f46", borderRadius: 8 }}
              formatter={(v) => [`${Number(v).toFixed(0)}ms`]}
            />
            <Legend wrapperStyle={{ color: "#a1a1aa", fontSize: 12 }} />
            <Line type="monotone" dataKey="avg_latency_ms" name="Avg" stroke="#f97316" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="p95_latency_ms" name="p95" stroke="#fb923c" dot={false} strokeWidth={1.5} strokeDasharray="4 2" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Pod table */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Pod Health</h2>
        <div className="rounded-xl border border-zinc-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900/80">
                {["Pod","Cluster","Avg Req/hr","Error Rate","Avg Lat","p95 Lat","CPU %","Mem MB","Restarts","Status"].map(h => (
                  <th key={h} className="px-3 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {pods.map(p => (
                <tr key={p.pod_name} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-3 py-3 font-mono text-xs text-zinc-200">{p.pod_name}</td>
                  <td className="px-3 py-3 text-xs text-zinc-500">{p.cluster.split("-").slice(-2).join("-")}</td>
                  <td className="px-3 py-3 text-zinc-300">{p.avg_request_count.toFixed(0)}</td>
                  <td className="px-3 py-3">
                    <span className={p.avg_error_rate > 0.03 ? "text-red-400" : "text-zinc-400"}>
                      {(p.avg_error_rate * 100).toFixed(2)}%
                    </span>
                  </td>
                  <td className="px-3 py-3 text-zinc-300">{p.avg_latency_ms.toFixed(0)}ms</td>
                  <td className="px-3 py-3 text-zinc-300">{p.p95_latency_ms.toFixed(0)}ms</td>
                  <td className="px-3 py-3">
                    <span className={p.avg_cpu_percent > 70 ? "text-orange-400" : "text-zinc-400"}>
                      {p.avg_cpu_percent.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-3 py-3 text-zinc-400">{p.avg_memory_mb.toFixed(0)}</td>
                  <td className="px-3 py-3">
                    {p.total_restarts > 0
                      ? <span className="text-red-400 font-medium">{p.total_restarts}</span>
                      : <span className="text-zinc-600">0</span>}
                  </td>
                  <td className="px-3 py-3">
                    {p.latest_status === "healthy" ? (
                      <span className="flex items-center gap-1 text-xs text-green-400">
                        <CheckCircle2 className="h-3 w-3" /> healthy
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs text-orange-400">
                        <Activity className="h-3 w-3" /> {p.latest_status}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
