"use client";

import { useEffect, useState } from "react";

import { getApiHealth, getDbHealth } from "@/lib/api";

type HealthState = "checking" | "online" | "waking" | "unavailable";

type ProductionHealthCardProps = {
  compact?: boolean;
};

function statusCopy(state: HealthState): { label: string; detail: string; tone: string } {
  if (state === "online") {
    return {
      label: "Live demo online",
      detail: "Render API and Supabase PostGIS are responding through the Vercel proxy.",
      tone: "success",
    };
  }
  if (state === "waking") {
    return {
      label: "Backend waking up",
      detail: "This can take up to a minute on the free deployment tier. The overview and static demo remain available.",
      tone: "warning",
    };
  }
  if (state === "unavailable") {
    return {
      label: "Live demo temporarily unavailable",
      detail: "The project overview and static demo are still available. Try the live composer again in a moment.",
      tone: "warning",
    };
  }
  return {
    label: "Checking live demo",
    detail: "Testing the Vercel proxy, Render API, and live services.",
    tone: "default",
  };
}

export function ProductionHealthCard({ compact = false }: ProductionHealthCardProps) {
  const [state, setState] = useState<HealthState>("checking");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const poll = async (nextAttempt: number) => {
      if (cancelled) return;
      setAttempt(nextAttempt);
      try {
        const health = await getApiHealth();
        if (!health.ok) throw new Error("api_not_ready");
        const db = await getDbHealth();
        if (!cancelled) {
          setState(db.database_connected ? "online" : "waking");
        }
        if (!db.database_connected && nextAttempt < 9) {
          timer = setTimeout(() => poll(nextAttempt + 1), 10000);
        }
      } catch {
        if (!cancelled) {
          setState(nextAttempt < 9 ? "waking" : "unavailable");
        }
        if (nextAttempt < 9) {
          timer = setTimeout(() => poll(nextAttempt + 1), 10000);
        }
      }
    };

    poll(1);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  const copy = statusCopy(state);

  return (
    <section className={compact ? "production-health-card production-health-card-compact" : "production-health-card"}>
      <div className="panel-title-row">
        <div>
          <p className="eyebrow">Production readiness</p>
          <h3>{copy.label}</h3>
        </div>
        <span className={`chip chip-${copy.tone}`}>{state === "online" ? "Ready" : state === "checking" ? "Checking" : "Safe fallback"}</span>
      </div>
      <p className="muted">{copy.detail}</p>
      <div className="production-health-grid">
        <span>Frontend: Vercel</span>
        <span>API: Render</span>
        <span>Database: Supabase PostGIS</span>
        <span>Real publish: disabled</span>
        <span>{state === "online" ? "Last verified: live system check passed" : "Last verified: static fallback ready"}</span>
      </div>
      {state !== "online" ? (
        <p className="muted">Health check attempt {attempt}/9. Static portfolio content stays available while the backend wakes.</p>
      ) : null}
    </section>
  );
}
