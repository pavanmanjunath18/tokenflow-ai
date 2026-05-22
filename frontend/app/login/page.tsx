"use client";

import { useState, FormEvent } from "react";
import { useUser } from "@/context/UserContext";
import { useRouter } from "next/navigation";
import { AlertCircle } from "lucide-react";

export default function LoginPage() {
  const { login, isAuthenticated } = useUser();
  const router = useRouter();
  const [email, setEmail] = useState("admin@tokenflow.local");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) {
    router.replace("/dashboard");
    return null;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-8">
        {/* Logo */}
        <div className="text-center">
          <p className="text-3xl font-bold tracking-tight">
            <span className="text-white">TokenFlow</span>
            <span className="text-orange-400"> AI</span>
          </p>
          <p className="text-sm text-zinc-500 mt-1">Enterprise AI FinOps Platform</p>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-8 space-y-6">
          <div>
            <h1 className="text-xl font-semibold text-white">Sign in</h1>
            <p className="text-sm text-zinc-500 mt-1">Access your organisation's AI intelligence dashboard</p>
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-red-500/20 bg-red-500/5 px-3 py-2.5 text-sm text-red-400">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-400">Work email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="you@company.com"
                className="w-full rounded-lg border border-zinc-700 bg-zinc-800/60 px-3 py-2.5 text-sm text-zinc-100 placeholder-zinc-600 outline-none focus:border-orange-500/60 focus:ring-1 focus:ring-orange-500/30 transition-colors"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-400">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="••••••••"
                className="w-full rounded-lg border border-zinc-700 bg-zinc-800/60 px-3 py-2.5 text-sm text-zinc-100 placeholder-zinc-600 outline-none focus:border-orange-500/60 focus:ring-1 focus:ring-orange-500/30 transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-orange-500 hover:bg-orange-600 disabled:opacity-50 px-4 py-2.5 text-sm font-semibold text-white transition-colors"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <div className="rounded-lg bg-zinc-800/50 px-3 py-2.5 text-xs text-zinc-500 space-y-0.5">
            <p className="font-medium text-zinc-400">Demo credentials</p>
            <p>Email: <span className="text-zinc-300">admin@tokenflow.local</span></p>
            <p>Password: <span className="text-zinc-300">tokenflow2024</span></p>
          </div>
        </div>
      </div>
    </div>
  );
}
