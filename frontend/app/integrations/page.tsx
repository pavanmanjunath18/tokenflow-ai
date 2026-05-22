"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, XCircle, RefreshCw, Clock } from "lucide-react";
import { api, IntegrationStatus } from "@/lib/api";
import { fmtNum } from "@/lib/utils";

export default function IntegrationsPage() {
  const [statuses, setStatuses] = useState<IntegrationStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [syncAll, setSyncAll] = useState(false);

  const load = () => {
    setLoading(true);
    api.integrationStatus().then(setStatuses).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleSync = async (sourceKey: string) => {
    setSyncing(sourceKey);
    try { await api.syncSource(sourceKey); load(); }
    finally { setSyncing(null); }
  };

  const handleSyncAll = async () => {
    setSyncAll(true);
    try { await api.syncAll(); load(); }
    finally { setSyncAll(false); }
  };

  // Map display names to internal keys
  const SOURCE_KEYS: Record<string, string> = {
    "SSO Identity Directory":       "identity",
    "Model Pricing Catalog":        "model_pricing",
    "AI License Inventory":         "licenses",
    "AI Gateway Traces":            "api_gateway",
    "Browser Extension Telemetry":  "browser",
    "Kafka AI Telemetry Stream":    "kafka",
    "ClickHouse Analytics Store":   "clickhouse",
    "Kubernetes Gateway Logs":      "kubernetes",
    "Productivity Metrics":         "productivity",
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Integrations</h1>
          <p className="text-sm text-zinc-500 mt-1">Connector-based architecture — CSV/JSONL for MVP, real APIs in production</p>
        </div>
        <button
          onClick={handleSyncAll}
          disabled={syncAll}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${syncAll ? "animate-spin" : ""}`} />
          {syncAll ? "Syncing…" : "Sync All"}
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-52 rounded-xl bg-zinc-800/60" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {statuses.map(s => {
            const key = SOURCE_KEYS[s.source_name] ?? "";
            const isSyncing = syncing === key;
            return (
              <div key={s.source_name} className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-zinc-100">{s.source_name}</p>
                    <p className="text-xs text-zinc-500 mt-0.5">{s.connection_mode}</p>
                  </div>
                  <StatusBadge status={s.status} />
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <Stat label="Rows ingested" value={fmtNum(s.rows_ingested)} />
                  <Stat label="Schema" value={s.schema_valid ? "Valid" : "⚠ Warnings"} />
                  <Stat label="Last sync" value={s.last_sync ? new Date(s.last_sync).toLocaleString() : "Never"} />
                  <Stat label="Status" value={s.status} />
                </div>

                {/* Production upgrade */}
                <div className="rounded-lg bg-zinc-800/50 px-3 py-2 text-xs text-zinc-400">
                  <span className="text-zinc-500">Production equivalent: </span>
                  {s.production_equivalent}
                </div>

                {/* Sync button */}
                {key && (
                  <button
                    onClick={() => handleSync(key)}
                    disabled={!!syncing || syncAll}
                    className="w-full flex items-center justify-center gap-2 py-1.5 rounded-lg border border-zinc-700 hover:border-orange-500/50 hover:text-orange-400 text-zinc-400 text-xs transition-colors disabled:opacity-40"
                  >
                    <RefreshCw className={`h-3 w-3 ${isSyncing ? "animate-spin" : ""}`} />
                    {isSyncing ? "Syncing…" : "Sync now"}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === "success") return (
    <span className="flex items-center gap-1 text-xs text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full border border-green-500/20">
      <CheckCircle2 className="h-3 w-3" /> Synced
    </span>
  );
  if (status === "failed") return (
    <span className="flex items-center gap-1 text-xs text-red-400 bg-red-500/10 px-2 py-0.5 rounded-full border border-red-500/20">
      <XCircle className="h-3 w-3" /> Failed
    </span>
  );
  return (
    <span className="flex items-center gap-1 text-xs text-zinc-400 bg-zinc-500/10 px-2 py-0.5 rounded-full border border-zinc-700">
      <Clock className="h-3 w-3" /> Not synced
    </span>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="text-sm text-zinc-200 font-medium">{value}</p>
    </div>
  );
}
