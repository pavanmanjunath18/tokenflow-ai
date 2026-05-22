"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle2, XCircle, RefreshCw, Clock, AlertTriangle,
  ArrowRight, Zap, SkipForward, ShieldAlert,
} from "lucide-react";
import { api, IntegrationStatus } from "@/lib/api";
import { fmtNum } from "@/lib/utils";
import { useUser } from "@/context/UserContext";

function fmtDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function fmtTime(iso: string | null): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export default function IntegrationsPage() {
  const { hasRole } = useUser();
  const canSync = hasRole("admin");
  const [statuses, setStatuses] = useState<IntegrationStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [syncingAll, setSyncingAll] = useState(false);
  const [lastResult, setLastResult] = useState<Record<string, string>>({});

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

  const load = () => {
    setLoading(true);
    api.integrationStatus().then(setStatuses).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleSync = async (sourceKey: string) => {
    setSyncing(sourceKey);
    try {
      const r = await api.syncSource(sourceKey);
      setLastResult(prev => ({
        ...prev,
        [sourceKey]: r.status === "success"
          ? `✓ ${fmtNum(r.rows_ingested)} upserted, ${fmtNum(r.rows_skipped)} skipped`
          : `✗ ${r.message.slice(0, 60)}`,
      }));
      load();
    } finally {
      setSyncing(null);
    }
  };

  const handleSyncAll = async () => {
    setSyncingAll(true);
    try {
      await api.syncAll();
      load();
    } finally {
      setSyncingAll(false);
    }
  };

  const summary = {
    healthy:    statuses.filter(s => s.health === "healthy").length,
    degraded:   statuses.filter(s => s.health === "degraded").length,
    failed:     statuses.filter(s => s.health === "failed").length,
    not_synced: statuses.filter(s => s.health === "not_synced").length,
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Integrations</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Connector-based architecture — incremental watermark sync, schema-drift detection
          </p>
        </div>
        {canSync && (
          <button
            onClick={handleSyncAll}
            disabled={syncingAll}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${syncingAll ? "animate-spin" : ""}`} />
            {syncingAll ? "Syncing all…" : "Sync All"}
          </button>
        )}
      </div>

      {/* Fleet health summary */}
      {!loading && (
        <div className="grid grid-cols-4 gap-3">
          <FleetCard label="Healthy"   count={summary.healthy}    color="text-green-400"  bg="bg-green-500/5 border-green-500/20" />
          <FleetCard label="Degraded"  count={summary.degraded}   color="text-yellow-400" bg="bg-yellow-500/5 border-yellow-500/20" />
          <FleetCard label="Failed"    count={summary.failed}     color="text-red-400"    bg="bg-red-500/5 border-red-500/20" />
          <FleetCard label="Not Synced" count={summary.not_synced} color="text-zinc-400"   bg="bg-zinc-500/5 border-zinc-700" />
        </div>
      )}

      {/* Connector cards */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-64 rounded-xl bg-zinc-800/60" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {statuses.map(s => {
            const key = SOURCE_KEYS[s.source_name] ?? "";
            const isSyncing = syncing === key;
            const result = lastResult[key];
            return (
              <ConnectorCard
                key={s.source_name}
                s={s}
                sourceKey={key}
                isSyncing={isSyncing}
                syncingAll={syncingAll}
                canSync={canSync}
                result={result}
                onSync={handleSync}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

function FleetCard({ label, count, color, bg }: {
  label: string; count: number; color: string; bg: string;
}) {
  return (
    <div className={`rounded-xl border ${bg} px-4 py-3 text-center`}>
      <p className={`text-2xl font-bold ${color}`}>{count}</p>
      <p className="text-xs text-zinc-500 mt-0.5">{label}</p>
    </div>
  );
}

function ConnectorCard({ s, sourceKey, isSyncing, syncingAll, canSync, result, onSync }: {
  s: IntegrationStatus;
  sourceKey: string;
  isSyncing: boolean;
  syncingAll: boolean;
  canSync: boolean;
  result?: string;
  onSync: (key: string) => void;
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-zinc-100">{s.source_name}</p>
          <p className="text-xs text-zinc-500 mt-0.5">{s.connection_mode}</p>
        </div>
        <HealthBadge health={s.health} />
      </div>

      {/* Observability grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
        <ObsStat
          icon={<ArrowRight className="h-3 w-3 text-green-400" />}
          label="Rows upserted"
          value={fmtNum(s.rows_ingested)}
        />
        <ObsStat
          icon={<SkipForward className="h-3 w-3 text-zinc-400" />}
          label="Rows skipped"
          value={fmtNum(s.rows_skipped)}
          muted={s.rows_skipped === 0}
        />
        <ObsStat
          icon={<Zap className="h-3 w-3 text-orange-400" />}
          label="Last duration"
          value={s.last_duration_ms > 0 ? fmtDuration(s.last_duration_ms) : "—"}
        />
        <ObsStat
          icon={<ShieldAlert className="h-3 w-3 text-yellow-400" />}
          label="Warnings"
          value={s.validation_warnings > 0 ? String(s.validation_warnings) : "None"}
          accent={s.validation_warnings > 0}
        />
        <div className="col-span-2 space-y-1">
          <p className="text-xs text-zinc-500">
            Last success:{" "}
            <span className="text-zinc-300">{fmtTime(s.last_sync_success)}</span>
          </p>
          {s.last_sync_failed && (
            <p className="text-xs text-zinc-500">
              Last failure:{" "}
              <span className="text-red-400">{fmtTime(s.last_sync_failed)}</span>
            </p>
          )}
          {s.watermark_since && (
            <p className="text-xs text-zinc-500">
              Watermark:{" "}
              <span className="text-zinc-400">{fmtTime(s.watermark_since)}</span>
            </p>
          )}
        </div>
      </div>

      {/* Production equivalent */}
      <div className="rounded-lg bg-zinc-800/50 px-3 py-2 text-xs text-zinc-400">
        <span className="text-zinc-500">Production: </span>
        {s.production_equivalent}
      </div>

      {/* Last sync result flash */}
      {result && (
        <p className={`text-xs font-medium ${result.startsWith("✓") ? "text-green-400" : "text-red-400"}`}>
          {result}
        </p>
      )}

      {/* Sync button */}
      {sourceKey && canSync && (
        <button
          onClick={() => onSync(sourceKey)}
          disabled={isSyncing || syncingAll}
          className="w-full flex items-center justify-center gap-2 py-1.5 rounded-lg border border-zinc-700 hover:border-orange-500/50 hover:text-orange-400 text-zinc-400 text-xs transition-colors disabled:opacity-40"
        >
          <RefreshCw className={`h-3 w-3 ${isSyncing ? "animate-spin" : ""}`} />
          {isSyncing ? "Syncing…" : "Sync now"}
        </button>
      )}
    </div>
  );
}

function HealthBadge({ health }: { health: IntegrationStatus["health"] }) {
  const cfg: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
    healthy:    { label: "Healthy",    cls: "text-green-400 bg-green-500/10 border-green-500/20",  icon: <CheckCircle2 className="h-3 w-3" /> },
    degraded:   { label: "Degraded",   cls: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20", icon: <AlertTriangle className="h-3 w-3" /> },
    failed:     { label: "Failed",     cls: "text-red-400 bg-red-500/10 border-red-500/20",        icon: <XCircle className="h-3 w-3" /> },
    syncing:    { label: "Syncing",    cls: "text-blue-400 bg-blue-500/10 border-blue-500/20",     icon: <RefreshCw className="h-3 w-3 animate-spin" /> },
    not_synced: { label: "Not Synced", cls: "text-zinc-400 bg-zinc-500/10 border-zinc-700",         icon: <Clock className="h-3 w-3" /> },
  };
  const { label, cls, icon } = cfg[health] ?? cfg.not_synced;
  return (
    <span className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${cls} shrink-0`}>
      {icon} {label}
    </span>
  );
}

function ObsStat({ icon, label, value, muted, accent }: {
  icon: React.ReactNode; label: string; value: string; muted?: boolean; accent?: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      {icon}
      <div>
        <p className="text-xs text-zinc-500">{label}</p>
        <p className={`text-sm font-medium ${accent ? "text-yellow-400" : muted ? "text-zinc-600" : "text-zinc-200"}`}>
          {value}
        </p>
      </div>
    </div>
  );
}
