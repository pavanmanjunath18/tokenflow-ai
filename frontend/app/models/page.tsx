"use client";

import { useEffect, useState } from "react";
import { api, ModelStat } from "@/lib/api";
import { fmt$$, fmtNum } from "@/lib/utils";

const TIER_COLOR: Record<string, string> = {
  ultra:    "bg-red-500/15 text-red-400 border-red-500/30",
  premium:  "bg-orange-500/15 text-orange-400 border-orange-500/30",
  standard: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  economy:  "bg-green-500/15 text-green-400 border-green-500/30",
};

export default function ModelsPage() {
  const [data, setData] = useState<ModelStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.models().then(setData).finally(() => setLoading(false)); }, []);

  const totalSavings = data.reduce((s, m) => s + m.estimated_savings_if_downgraded, 0);

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Model Usage</h1>
          <p className="text-sm text-zinc-500 mt-1">Cost and efficiency across all AI models</p>
        </div>
        {totalSavings > 0 && (
          <div className="rounded-lg border border-orange-500/30 bg-orange-500/5 px-4 py-2 text-right">
            <p className="text-xs text-zinc-500">Est. downgrade savings</p>
            <p className="text-lg font-bold text-orange-400">{fmt$$(totalSavings)}</p>
          </div>
        )}
      </div>

      {loading ? (
        <div className="space-y-2 animate-pulse">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-14 rounded-xl bg-zinc-800/60" />)}
        </div>
      ) : (
        <div className="rounded-xl border border-zinc-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900/80">
                {["Model","Provider","Tier","Total Spend","Tokens","Requests","Simple-task Flags","Downgrade Savings"].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {data.map(m => (
                <tr key={m.model_name} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-zinc-200">{m.model_name}</td>
                  <td className="px-4 py-3 text-zinc-400">{m.provider}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${TIER_COLOR[m.tier] ?? "text-zinc-400 border-zinc-700"}`}>
                      {m.tier}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-orange-400 font-semibold">{fmt$$(m.total_cost)}</td>
                  <td className="px-4 py-3 text-zinc-300">{fmtNum(m.total_tokens)}</td>
                  <td className="px-4 py-3 text-zinc-300">{fmtNum(m.total_requests)}</td>
                  <td className="px-4 py-3">
                    {m.expensive_simple_task_count > 0 ? (
                      <span className="text-xs bg-orange-500/15 text-orange-400 border border-orange-500/30 px-2 py-0.5 rounded-full">
                        {fmtNum(m.expensive_simple_task_count)}
                      </span>
                    ) : <span className="text-zinc-600">—</span>}
                  </td>
                  <td className="px-4 py-3 text-green-400 font-medium">
                    {m.estimated_savings_if_downgraded > 0 ? fmt$$(m.estimated_savings_if_downgraded) : <span className="text-zinc-600">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
