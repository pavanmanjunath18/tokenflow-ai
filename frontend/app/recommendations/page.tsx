"use client";

import { useEffect, useState } from "react";
import { RefreshCw, CheckCircle, XCircle, Search } from "lucide-react";
import { api, Recommendation } from "@/lib/api";
import { fmt$$, SEVERITY_COLOR, STATUS_COLOR } from "@/lib/utils";
import { useUser } from "@/context/UserContext";

export default function RecommendationsPage() {
  const { hasRole } = useUser();
  const canGenerate = hasRole("admin");
  const canReview   = hasRole("admin", "reviewer");
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [reviewing, setReviewing] = useState<number | null>(null);

  const load = () => {
    setLoading(true);
    api.recommendations().then(setRecs).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const generate = async () => {
    setGenerating(true);
    try { await api.generateRecs(); load(); }
    finally { setGenerating(false); }
  };

  const review = async (id: number, status: "accepted" | "rejected") => {
    setReviewing(id);
    try {
      await api.reviewRec(id, status);
      load();
    } finally { setReviewing(null); }
  };

  const pending   = recs.filter(r => r.status === "pending");
  const actioned  = recs.filter(r => r.status !== "pending");
  const totalSavings = pending.reduce((s, r) => s + r.estimated_monthly_savings, 0);

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Recommendation Center</h1>
          <p className="text-sm text-zinc-500 mt-1">
            All recommendations require human review · no automated decisions
          </p>
        </div>
        {canGenerate && (
          <button
            onClick={generate}
            disabled={generating}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${generating ? "animate-spin" : ""}`} />
            {generating ? "Generating…" : "Regenerate"}
          </button>
        )}
      </div>

      {totalSavings > 0 && (
        <div className="rounded-xl border border-green-500/20 bg-green-500/5 px-5 py-3 flex items-center gap-3">
          <p className="text-sm text-zinc-300">
            Pending recommendations could save up to{" "}
            <span className="font-bold text-green-400">{fmt$$(totalSavings)}/month</span> if accepted.
            All require human review before any action is taken.
          </p>
        </div>
      )}

      {loading ? (
        <div className="space-y-3 animate-pulse">
          {Array.from({length:4}).map((_,i)=><div key={i} className="h-36 rounded-xl bg-zinc-800/60"/>)}
        </div>
      ) : (
        <>
          {pending.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Pending Review ({pending.length})</h2>
              {pending.map(r => (
                <RecCard key={r.id} rec={r} reviewing={reviewing} onReview={review} canReview={canReview} />
              ))}
            </section>
          )}
          {actioned.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Actioned ({actioned.length})</h2>
              {actioned.map(r => (
                <RecCard key={r.id} rec={r} reviewing={reviewing} onReview={review} readonly />
              ))}
            </section>
          )}
          {recs.length === 0 && (
            <div className="text-center py-16 text-zinc-600">
              <Search className="h-8 w-8 mx-auto mb-2" />
              No recommendations yet. Click Regenerate to analyse current data.
            </div>
          )}
        </>
      )}
    </div>
  );
}

function RecCard({
  rec, reviewing, onReview, canReview, readonly,
}: {
  rec: Recommendation;
  reviewing: number | null;
  onReview: (id: number, status: "accepted" | "rejected") => void;
  canReview?: boolean;
  readonly?: boolean;
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded-full border ${SEVERITY_COLOR[rec.severity] ?? ""}`}>
              {rec.severity}
            </span>
            <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-full">{rec.recommendation_type}</span>
            <span className="text-xs text-zinc-500">{rec.department}</span>
          </div>
          <p className="font-semibold text-zinc-100">{rec.title}</p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-xs text-zinc-500">Est. savings</p>
          <p className="text-lg font-bold text-green-400">{fmt$$(rec.estimated_monthly_savings)}<span className="text-xs text-zinc-500">/mo</span></p>
        </div>
      </div>

      <p className="text-sm text-zinc-400">{rec.description}</p>
      <p className="text-xs text-zinc-600 italic">{rec.reasoning}</p>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_COLOR[rec.status] ?? ""}`}>
            {rec.status}
          </span>
          <span className="text-xs text-zinc-600">
            Confidence: {(rec.confidence_score * 100).toFixed(0)}%
          </span>
          {rec.requires_human_review && (
            <span className="text-xs text-purple-400 bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 rounded-full">
              Human review required
            </span>
          )}
        </div>

        {!readonly && canReview && rec.status === "pending" && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => onReview(rec.id, "rejected")}
              disabled={reviewing === rec.id}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-zinc-700 text-zinc-400 hover:border-red-500/50 hover:text-red-400 text-xs transition-colors disabled:opacity-40"
            >
              <XCircle className="h-3.5 w-3.5" /> Reject
            </button>
            <button
              onClick={() => onReview(rec.id, "accepted")}
              disabled={reviewing === rec.id}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-green-600/20 border border-green-500/30 text-green-400 hover:bg-green-600/30 text-xs transition-colors disabled:opacity-40"
            >
              <CheckCircle className="h-3.5 w-3.5" /> Accept
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
