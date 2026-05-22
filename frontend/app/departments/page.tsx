"use client";

import { useEffect, useState } from "react";
import { api, DepartmentStat } from "@/lib/api";
import { fmt$$, fmtNum } from "@/lib/utils";

export default function DepartmentsPage() {
  const [data, setData] = useState<DepartmentStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.departments().then(setData).finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Department Analytics</h1>
        <p className="text-sm text-zinc-500 mt-1">AI spend and usage broken down by department</p>
      </div>

      {loading ? (
        <div className="space-y-2 animate-pulse">
          {Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-14 rounded-xl bg-zinc-800/60" />)}
        </div>
      ) : (
        <div className="rounded-xl border border-zinc-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900/80">
                {["Department","Total Spend","Tokens","Requests","Avg Cost","Top Model","Risk Flags"].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {data.map(d => (
                <tr key={d.department} className="hover:bg-zinc-800/30 transition-colors">
                  <td className="px-4 py-3 font-medium text-zinc-100">{d.department}</td>
                  <td className="px-4 py-3 text-orange-400 font-semibold">{fmt$$(d.total_cost)}</td>
                  <td className="px-4 py-3 text-zinc-300">{fmtNum(d.total_tokens)}</td>
                  <td className="px-4 py-3 text-zinc-300">{fmtNum(d.total_requests)}</td>
                  <td className="px-4 py-3 text-zinc-400">${d.avg_cost_per_request.toFixed(4)}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded-full">{d.top_model}</span>
                  </td>
                  <td className="px-4 py-3">
                    {d.expensive_simple_task_count > 0 ? (
                      <span className="text-xs bg-orange-500/15 text-orange-400 border border-orange-500/30 px-2 py-0.5 rounded-full">
                        {d.expensive_simple_task_count} flagged
                      </span>
                    ) : (
                      <span className="text-xs text-zinc-600">—</span>
                    )}
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
