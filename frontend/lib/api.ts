const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── types ────────────────────────────────────────────────────────────────────

export interface DashboardOverview {
  total_spend: number;
  monthly_projected_spend: number;
  total_tokens: number;
  total_requests: number;
  avg_cost_per_request: number;
  top_spending_department: string;
  estimated_monthly_savings: number;
  high_risk_events: number;
  inactive_licenses: number;
  period_start: string;
  period_end: string;
}

export interface SpendPoint {
  date: string;
  cost_usd: number;
}

export interface DepartmentStat {
  department: string;
  total_cost: number;
  total_tokens: number;
  total_requests: number;
  avg_cost_per_request: number;
  top_model: string;
  expensive_simple_task_count: number;
}

export interface ModelStat {
  model_name: string;
  provider: string;
  tier: string;
  total_cost: number;
  total_tokens: number;
  total_requests: number;
  expensive_simple_task_count: number;
  estimated_savings_if_downgraded: number;
}

export interface LicenseWaste {
  license_id: string;
  employee_id: string;
  department: string;
  tool_name: string;
  plan_type: string;
  monthly_seat_cost: number;
  active_days_last_30: number;
  license_status: string;
  waste_reason: string;
  last_active_date: string | null;
}

export interface LicenseWasteSummary {
  inactive_licenses: number;
  duplicate_licenses: number;
  total_monthly_waste: number;
  licenses: LicenseWaste[];
}

export interface Recommendation {
  id: number;
  created_at: string;
  recommendation_type: string;
  severity: string;
  department: string;
  employee_id: string;
  title: string;
  description: string;
  reasoning: string;
  estimated_monthly_savings: number;
  confidence_score: number;
  status: string;
  requires_human_review: boolean;
}

export interface IntegrationStatus {
  source_name: string;
  source_type: string;
  connection_mode: string;
  rows_ingested: number;
  last_sync: string | null;
  status: string;
  schema_valid: boolean;
  production_equivalent: string;
}

export interface AuditLog {
  id: number;
  timestamp: string;
  action: string;
  actor: string;
  resource_type: string;
  resource_id: string;
  details: string;
}

// ── api calls ────────────────────────────────────────────────────────────────

export const api = {
  // dashboard
  overview:       () => apiFetch<DashboardOverview>("/api/dashboard/overview"),
  spendOverTime:  () => apiFetch<SpendPoint[]>("/api/dashboard/spend-over-time"),
  departments:    () => apiFetch<DepartmentStat[]>("/api/dashboard/departments"),
  models:         () => apiFetch<ModelStat[]>("/api/dashboard/models"),

  // licenses
  licenseWaste:   () => apiFetch<LicenseWasteSummary>("/api/licenses/waste"),

  // recommendations
  recommendations: (status?: string) =>
    apiFetch<Recommendation[]>(`/api/recommendations${status ? `?status=${status}` : ""}`),
  generateRecs:   () => apiFetch<{ generated: number }>("/api/recommendations/generate", { method: "POST" }),
  reviewRec: (id: number, status: string, reviewed_by: string, review_notes = "") =>
    apiFetch<Recommendation>(`/api/recommendations/${id}/review`, {
      method: "PATCH",
      body: JSON.stringify({ status, reviewed_by, review_notes }),
    }),

  // integrations
  integrationStatus: () => apiFetch<IntegrationStatus[]>("/api/integrations/status"),
  syncSource: (source: string) =>
    apiFetch<{ rows_ingested: number; status: string }>(`/api/integrations/sync/${source}`, { method: "POST" }),
  syncAll: () =>
    apiFetch<{ rows_ingested: number; status: string }[]>("/api/integrations/sync/all/run", { method: "POST" }),

  // governance
  governanceSummary: () => apiFetch<{
    total_shadow_events: number; unique_shadow_domains: number;
    blocked_events: number; pii_flag_events: number; high_risk_events: number;
  }>("/api/governance/summary"),
  shadowAIDomains: () => apiFetch<{
    domain: string; event_count: number; employee_count: number; pii_count: number; departments: string;
  }[]>("/api/governance/shadow-ai-domains"),
  governanceAlerts: () => apiFetch<{
    timestamp: string; employee_id: string; department: string; domain: string;
    policy_action: string; contains_pii: boolean; pii_types: string; risk_score: number; shadow_ai_flag: boolean;
  }[]>("/api/governance/alerts"),

  // infrastructure
  infraSummary: () => apiFetch<{
    total_requests: number; total_errors: number; overall_error_rate: number;
    avg_latency_ms: number; p95_latency_ms: number; degraded_pods: number; total_restarts: number;
  }>("/api/infrastructure/summary"),
  podStats: () => apiFetch<{
    pod_name: string; cluster: string; avg_request_count: number; avg_error_rate: number;
    avg_latency_ms: number; p95_latency_ms: number; avg_cpu_percent: number;
    avg_memory_mb: number; total_restarts: number; latest_status: string;
  }[]>("/api/infrastructure/pods"),
  latencyOverTime: () => apiFetch<{ date: string; avg_latency_ms: number; p95_latency_ms: number }[]>(
    "/api/infrastructure/latency-over-time"
  ),

  // audit
  auditLogs: () => apiFetch<AuditLog[]>("/api/audit"),
};
