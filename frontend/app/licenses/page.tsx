"use client";

import { useEffect, useState } from "react";
import { api, LicenseWasteSummary } from "@/lib/api";
import { fmt$$, fmtNum } from "@/lib/utils";
import { StatCard } from "@/components/cards/StatCard";

export default function LicensesPage() {
  const [data, setData] = useState<LicenseWasteSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.licenseWaste().then(setData).finally(() => setLoading(false)); }, []);

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">License Waste</h1>
        <p className="text-sm text-zinc-500 mt-1">Inactive and duplicate AI seats burning budget</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-3 gap-4 animate-pulse">
          {Array.from({length:3}).map((_,i)=><div key={i} className="h-24 rounded-xl bg-zinc-800/60"/>)}
        </div>
      ) : data ? (
        <>
          <div className="grid grid-cols-3 gap-4">
            <StatCard label="Inactive Licenses"   value={fmtNum(data.inactive_licenses)}  accent />
            <StatCard label="Duplicate Seats"     value={fmtNum(data.duplicate_licenses)} />
            <StatCard label="Monthly Waste"       value={fmt$$(data.total_monthly_waste)}  accent />
          </div>

          <div className="rounded-xl border border-zinc-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900/80">
                  {["Employee","Department","Tool","Plan","Monthly Cost","Active Days (30d)","Reason"].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/50">
                {data.licenses.map(l => (
                  <tr key={l.license_id} className="hover:bg-zinc-800/30 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-zinc-400">{l.employee_id}</td>
                    <td className="px-4 py-3 text-zinc-300">{l.department}</td>
                    <td className="px-4 py-3 text-zinc-200">{l.tool_name}</td>
                    <td className="px-4 py-3 text-zinc-400">{l.plan_type}</td>
                    <td className="px-4 py-3 text-orange-400 font-semibold">{fmt$$(l.monthly_seat_cost)}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${
                        l.active_days_last_30 <= 3
                          ? "bg-red-500/15 text-red-400 border-red-500/30"
                          : "bg-zinc-800 text-zinc-400 border-zinc-700"
                      }`}>
                        {l.active_days_last_30}d
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-zinc-500">{l.waste_reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </div>
  );
}
