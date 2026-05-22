"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  CheckCircle2, XCircle, RefreshCw, Clock, AlertTriangle,
  ArrowRight, Zap, SkipForward, ShieldAlert, RotateCcw,
  Activity, Circle, ChevronDown, ChevronUp, Terminal,
} from "lucide-react";
import {
  api, IntegrationStatus, ActivityEvent, HeartbeatData, SystemStatus,
} from "@/lib/api";
import { fmtNum } from "@/lib/utils";
import { useUser } from "@/context/UserContext";

// ── formatters ────────────────────────────────────────────────────────────────

function fmtDuration(ms: number): string {
  if (ms <= 0) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function fmtTime(iso: string | null): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 5)   return "just now";
  if (s < 60)  return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

// ── source key map ────────────────────────────────────────────────────────────

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

// ── main page ─────────────────────────────────────────────────────────────────

export default function IntegrationsPage() {
  const { hasRole } = useUser();
  const canSync = hasRole("admin");

  const [statuses, setStatuses]       = useState<IntegrationStatus[]>([]);
  const [activity, setActivity]       = useState<ActivityEvent[]>([]);
  const [heartbeat, setHeartbeat]     = useState<HeartbeatData>({});
  const [sysStatus, setSysStatus]     = useState<SystemStatus | null>(null);
  const [loading, setLoading]         = useState(true);
  const [syncing, setSyncing]         = useState<string | null>(null);
  const [syncingAll, setSyncingAll]   = useState(false);
  const [lastResult, setLastResult]   = useState<Record<string, string>>({});
  const [activityOpen, setActivityOpen] = useState(true);

  const isSomethingSyncing = statuses.some(s => s.health === "syncing");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadStatuses = useCallback(() => {
    api.integrationStatus().then(setStatuses);
  }, []);

  const loadAll = useCallback(() => {
    setLoading(true);
    Promise.all([
      api.integrationStatus(),
      api.activityFeed(20),
      api.heartbeat(),
      api.systemStatus(),
    ])
      .then(([s, a, h, sys]) => {
        setStatuses(s);
        setActivity(a);
        setHeartbeat(h);
        setSysStatus(sys);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(loadAll, [loadAll]);

  // Live poll every 3 s while any connector is syncing
  useEffect(() => {
    if (isSomethingSyncing) {
      if (!pollRef.current) {
        pollRef.current = setInterval(() => {
          loadStatuses();
          api.activityFeed(20).then(setActivity);
        }, 3000);
      }
    } else {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
        // Final refresh to pick up completed sync stats
        loadAll();
      }
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [isSomethingSyncing, loadStatuses, loadAll]);

  const handleSync = async (sourceKey: string) => {
    setSyncing(sourceKey);
    try {
      const r = await api.syncSource(sourceKey);
      setLastResult(prev => ({
        ...prev,
        [sourceKey]: r.status === "queued"
          ? `⟳ Queued (${r.job_id.slice(0, 8)}…)`
          : `✗ ${r.message.slice(0, 60)}`,
      }));
      loadStatuses();
    } finally {
      setSyncing(null);
    }
  };

  const handleSyncAll = async () => {
    setSyncingAll(true);
    try {
      await api.syncAll();
      loadStatuses();
    } finally {
      setSyncingAll(false);
    }
  };

  const handleRetry = async (runId: number, sourceKey: string) => {
    try {
      const r = await api.retrySync(runId);
      setLastResult(prev => ({
        ...prev,
        [sourceKey]: `⟳ Retry queued (${r.job_id.slice(0, 8)}…)`,
      }));
      loadStatuses();
    } catch {
      setLastResult(prev => ({ ...prev, [sourceKey]: "✗ Retry failed" }));
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

      {/* System status bar */}
      <SystemStatusBar status={sysStatus} polling={isSomethingSyncing} />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Integrations</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Connector-based architecture — arq background workers · watermark sync · schema-drift detection
          </p>
        </div>
        {canSync && (
          <button
            onClick={handleSyncAll}
            disabled={syncingAll || isSomethingSyncing}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${syncingAll ? "animate-spin" : ""}`} />
            {syncingAll ? "Queuing all…" : "Sync All"}
          </button>
        )}
      </div>

      {/* Fleet health summary */}
      {!loading && (
        <div className="grid grid-cols-4 gap-3">
          <FleetCard label="Healthy"    count={summary.healthy}    color="text-green-400"  bg="bg-green-500/5 border-green-500/20" />
          <FleetCard label="Degraded"   count={summary.degraded}   color="text-yellow-400" bg="bg-yellow-500/5 border-yellow-500/20" />
          <FleetCard label="Failed"     count={summary.failed}     color="text-red-400"    bg="bg-red-500/5 border-red-500/20" />
          <FleetCard label="Not Synced" count={summary.not_synced} color="text-zinc-400"   bg="bg-zinc-500/5 border-zinc-700" />
        </div>
      )}

      {/* Connector cards */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-72 rounded-xl bg-zinc-800/60" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {statuses.map(s => {
            const key = SOURCE_KEYS[s.source_name] ?? "";
            return (
              <ConnectorCard
                key={s.source_name}
                s={s}
                sourceKey={key}
                isSyncing={syncing === key}
                syncingAll={syncingAll}
                canSync={canSync}
                result={lastResult[key]}
                heartbeat={heartbeat[key]}
                activity={activity}
                onSync={handleSync}
                onRetry={handleRetry}
              />
            );
          })}
        </div>
      )}

      {/* Activity feed */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40">
        <button
          className="w-full flex items-center justify-between px-5 py-3 text-sm font-medium text-zinc-300 hover:text-white transition-colors"
          onClick={() => setActivityOpen(o => !o)}
        >
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-orange-400" />
            Recent Sync Activity
            {activity.some(a => a.status === "running") && (
              <span className="flex items-center gap-1 text-xs text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                live
              </span>
            )}
          </div>
          {activityOpen ? <ChevronUp className="h-4 w-4 text-zinc-500" /> : <ChevronDown className="h-4 w-4 text-zinc-500" />}
        </button>

        {activityOpen && (
          <div className="border-t border-zinc-800 divide-y divide-zinc-800/50 max-h-80 overflow-y-auto">
            {activity.length === 0 ? (
              <p className="px-5 py-6 text-sm text-zinc-600 text-center">No sync activity yet. Run a sync to see events here.</p>
            ) : (
              activity.map(ev => <ActivityRow key={ev.id} event={ev} />)
            )}
          </div>
        )}
      </div>

    </div>
  );
}

// ── sub-components ────────────────────────────────────────────────────────────

function SystemStatusBar({ status, polling }: { status: SystemStatus | null; polling: boolean }) {
  if (!status) return null;
  const redisOk = status.redis === "connected";
  return (
    <div className="flex items-center gap-4 px-4 py-2 rounded-lg bg-zinc-900/70 border border-zinc-800 text-xs flex-wrap">
      <div className="flex items-center gap-1.5">
        <Circle
          className={`h-2 w-2 fill-current ${redisOk ? "text-green-400" : "text-red-400"}`}
        />
        <span className={redisOk ? "text-green-400" : "text-red-400"}>
          Redis {redisOk ? `${status.redis_version}` : "disconnected"}
        </span>
      </div>
      <span className="text-zinc-700">|</span>
      <div className="flex items-center gap-1 text-zinc-400">
        <Terminal className="h-3 w-3 text-zinc-500" />
        <span className="text-zinc-500">worker:</span>
        <span className="font-mono">{status.worker}</span>
      </div>
      <span className="text-zinc-700">|</span>
      <span className="text-zinc-400">
        <span className="text-zinc-500">active: </span>
        {status.active_jobs}
      </span>
      {polling && (
        <>
          <span className="text-zinc-700">|</span>
          <div className="flex items-center gap-1.5 text-blue-400">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            live polling
          </div>
        </>
      )}
      <span className="ml-auto text-zinc-600 font-mono text-xs hidden sm:block">
        {status.worker_command}
      </span>
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

function ConnectorCard({
  s, sourceKey, isSyncing, syncingAll, canSync, result, heartbeat,
  activity, onSync, onRetry,
}: {
  s: IntegrationStatus;
  sourceKey: string;
  isSyncing: boolean;
  syncingAll: boolean;
  canSync: boolean;
  result?: string;
  heartbeat?: { status: string; data_freshness_hours: number | null };
  activity: ActivityEvent[];
  onSync: (key: string) => void;
  onRetry: (runId: number, key: string) => void;
}) {
  // Find the last failed run ID for this connector (for retry button)
  const lastFailedRun = activity.find(
    a => a.source_name === s.source_name && a.status === "failed"
  );

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-4">

      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="font-semibold text-zinc-100 truncate">{s.source_name}</p>
            {heartbeat && <FreshnessBadge heartbeat={heartbeat} />}
          </div>
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
          value={fmtDuration(s.last_duration_ms)}
        />
        <ObsStat
          icon={<ShieldAlert className="h-3 w-3 text-yellow-400" />}
          label="Warnings"
          value={s.validation_warnings > 0 ? String(s.validation_warnings) : "None"}
          accent={s.validation_warnings > 0}
        />
        <div className="col-span-2 space-y-1">
          <p className="text-xs text-zinc-500">
            Last success: <span className="text-zinc-300">{fmtTime(s.last_sync_success)}</span>
          </p>
          {s.last_sync_failed && (
            <p className="text-xs text-zinc-500">
              Last failure: <span className="text-red-400">{fmtTime(s.last_sync_failed)}</span>
            </p>
          )}
          {s.watermark_since && (
            <p className="text-xs text-zinc-500">
              Watermark: <span className="text-zinc-400">{fmtTime(s.watermark_since)}</span>
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
        <p className={`text-xs font-medium ${
          result.startsWith("⟳") ? "text-blue-400" : result.startsWith("✓") ? "text-green-400" : "text-red-400"
        }`}>
          {result}
        </p>
      )}

      {/* Action buttons */}
      {sourceKey && canSync && (
        <div className="flex gap-2">
          <button
            onClick={() => onSync(sourceKey)}
            disabled={isSyncing || syncingAll || s.health === "syncing"}
            className="flex-1 flex items-center justify-center gap-2 py-1.5 rounded-lg border border-zinc-700 hover:border-orange-500/50 hover:text-orange-400 text-zinc-400 text-xs transition-colors disabled:opacity-40"
          >
            <RefreshCw className={`h-3 w-3 ${(isSyncing || s.health === "syncing") ? "animate-spin" : ""}`} />
            {s.health === "syncing" ? "Syncing…" : isSyncing ? "Queuing…" : "Sync now"}
          </button>

          {s.health === "failed" && lastFailedRun && (
            <button
              onClick={() => onRetry(lastFailedRun.id, sourceKey)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-red-500/30 hover:border-red-500/60 text-red-400/70 hover:text-red-400 text-xs transition-colors"
              title="Retry last failed sync"
            >
              <RotateCcw className="h-3 w-3" />
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function FreshnessBadge({ heartbeat }: { heartbeat: { status: string; data_freshness_hours: number | null } }) {
  const { status, data_freshness_hours: h } = heartbeat;
  if (status === "no_data" || status === "unknown") return null;

  const age = h !== null
    ? (h < 1 ? "<1h" : `${Math.floor(h)}h`)
    : null;

  if (status === "healthy") {
    return (
      <span className="text-xs text-green-400/70 bg-green-500/5 border border-green-500/10 px-1.5 py-0.5 rounded">
        Fresh{age ? ` · ${age}` : ""}
      </span>
    );
  }
  return (
    <span className="text-xs text-yellow-400/70 bg-yellow-500/5 border border-yellow-500/10 px-1.5 py-0.5 rounded">
      Stale{age ? ` · ${age}` : ""}
    </span>
  );
}

function HealthBadge({ health }: { health: IntegrationStatus["health"] }) {
  const cfg: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
    healthy:    { label: "Healthy",    cls: "text-green-400 bg-green-500/10 border-green-500/20",   icon: <CheckCircle2 className="h-3 w-3" /> },
    degraded:   { label: "Degraded",   cls: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20", icon: <AlertTriangle className="h-3 w-3" /> },
    failed:     { label: "Failed",     cls: "text-red-400 bg-red-500/10 border-red-500/20",          icon: <XCircle className="h-3 w-3" /> },
    syncing:    { label: "Syncing",    cls: "text-blue-400 bg-blue-500/10 border-blue-500/20",       icon: <RefreshCw className="h-3 w-3 animate-spin" /> },
    not_synced: { label: "Not Synced", cls: "text-zinc-400 bg-zinc-500/10 border-zinc-700",           icon: <Clock className="h-3 w-3" /> },
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

function ActivityRow({ event }: { event: ActivityEvent }) {
  const { status, source_name, started_at, rows_ingested, duration_ms, error_message } = event;

  const icon =
    status === "success" ? <CheckCircle2 className="h-3.5 w-3.5 text-green-400 shrink-0 mt-0.5" /> :
    status === "failed"  ? <XCircle className="h-3.5 w-3.5 text-red-400 shrink-0 mt-0.5" /> :
                           <RefreshCw className="h-3.5 w-3.5 text-blue-400 animate-spin shrink-0 mt-0.5" />;

  const detail =
    status === "success" ? `${fmtNum(rows_ingested)} rows · ${fmtDuration(duration_ms)}` :
    status === "failed"  ? (error_message?.slice(0, 80) || "Unknown error") :
                           "Running…";

  const detailColor =
    status === "success" ? "text-zinc-500" :
    status === "failed"  ? "text-red-400/80" :
                           "text-blue-400/80";

  return (
    <div className="flex items-start gap-3 px-5 py-2.5 hover:bg-zinc-800/30 transition-colors">
      {icon}
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-medium text-zinc-300">{source_name}</span>
          <span className="text-xs text-zinc-600">{timeAgo(started_at)}</span>
        </div>
        <p className={`text-xs ${detailColor} truncate`}>{detail}</p>
      </div>
      <span className="text-xs text-zinc-700 font-mono shrink-0 hidden sm:block">
        {event.triggered_by?.split("@")[0] ?? "system"}
      </span>
    </div>
  );
}
