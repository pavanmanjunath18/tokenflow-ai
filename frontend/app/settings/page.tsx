"use client";

import { useState } from "react";
import { RefreshCw, Database, Shield, Bell, Info } from "lucide-react";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [genResult, setGenResult] = useState<string | null>(null);

  const handleSyncAll = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const results = await api.syncAll();
      const total = results.reduce((s, r) => s + r.rows_ingested, 0);
      setSyncResult(`Synced ${results.length} sources · ${total.toLocaleString()} rows total`);
    } catch (e: unknown) {
      setSyncResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setSyncing(false);
    }
  };

  const handleGenerateRecs = async () => {
    setGenerating(true);
    setGenResult(null);
    try {
      const r = await api.generateRecs();
      setGenResult(`Generated ${r.generated} recommendations`);
    } catch (e: unknown) {
      setGenResult(`Error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings & Admin</h1>
        <p className="text-sm text-zinc-500 mt-1">Data management and platform configuration</p>
      </div>

      {/* Data Management */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
          <Database className="h-4 w-4" /> Data Management
        </h2>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-zinc-200">Sync All Connectors</p>
              <p className="text-xs text-zinc-500 mt-0.5">Re-ingest all 9 data sources from CSV/JSONL files</p>
            </div>
            <button
              onClick={handleSyncAll}
              disabled={syncing}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
              {syncing ? "Syncing…" : "Sync Now"}
            </button>
          </div>
          {syncResult && (
            <p className="text-xs text-zinc-400 bg-zinc-800/50 rounded-lg px-3 py-2">{syncResult}</p>
          )}
        </div>

        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-zinc-200">Regenerate Recommendations</p>
              <p className="text-xs text-zinc-500 mt-0.5">Re-run the rule engine against current data</p>
            </div>
            <button
              onClick={handleGenerateRecs}
              disabled={generating}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-zinc-700 hover:border-orange-500/50 hover:text-orange-400 text-zinc-300 text-sm font-medium disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`h-4 w-4 ${generating ? "animate-spin" : ""}`} />
              {generating ? "Generating…" : "Regenerate"}
            </button>
          </div>
          {genResult && (
            <p className="text-xs text-zinc-400 bg-zinc-800/50 rounded-lg px-3 py-2">{genResult}</p>
          )}
        </div>
      </section>

      {/* Privacy Configuration */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
          <Shield className="h-4 w-4" /> Privacy Configuration
        </h2>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 divide-y divide-zinc-800">
          {[
            { label: "Store raw prompt content",    value: "Disabled",  note: "Metadata only" },
            { label: "Individual-level views",       value: "Admin only", note: "Team rollups shown by default" },
            { label: "PII detection",                value: "Enabled",   note: "Flags on ingest, no content stored" },
            { label: "Automated disciplinary actions", value: "Disabled", note: "All decisions require human review" },
            { label: "Data retention window",        value: "180 days",  note: "Configurable per policy" },
          ].map(item => (
            <div key={item.label} className="flex items-center justify-between px-5 py-3">
              <div>
                <p className="text-sm text-zinc-300">{item.label}</p>
                <p className="text-xs text-zinc-600">{item.note}</p>
              </div>
              <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-zinc-700">
                {item.value}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Alert Thresholds */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
          <Bell className="h-4 w-4" /> Alert Thresholds (read-only in MVP)
        </h2>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 divide-y divide-zinc-800">
          {[
            { label: "Cost spike threshold",           value: "2.5× rolling weekly avg" },
            { label: "Inactive license threshold",     value: "≤3 active days / 30d" },
            { label: "Risk score alert threshold",     value: "≥0.7" },
            { label: "Expensive-model misuse",         value: "premium/ultra on simple tasks" },
          ].map(item => (
            <div key={item.label} className="flex items-center justify-between px-5 py-3">
              <p className="text-sm text-zinc-300">{item.label}</p>
              <span className="text-xs font-mono text-orange-400">{item.value}</span>
            </div>
          ))}
        </div>
      </section>

      {/* About */}
      <section className="rounded-xl border border-zinc-800/50 bg-zinc-900/30 p-5 flex gap-3">
        <Info className="h-4 w-4 text-zinc-600 shrink-0 mt-0.5" />
        <div className="text-xs text-zinc-600 space-y-1">
          <p><span className="text-zinc-500">Version:</span> 0.1.0 — MVP Phase 2</p>
          <p><span className="text-zinc-500">Data:</span> Synthetic CSV/JSONL (9 connectors · 253k rows)</p>
          <p><span className="text-zinc-500">Backend:</span> FastAPI · PostgreSQL · SQLAlchemy 2</p>
          <p><span className="text-zinc-500">Frontend:</span> Next.js 15 · Tailwind CSS · shadcn/ui · Recharts</p>
        </div>
      </section>
    </div>
  );
}
