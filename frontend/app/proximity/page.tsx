"use client";

import { useEffect, useState } from "react";

import { ProximityForm } from "@/components/proximity-form";
import { ProximityMapPanel } from "@/components/proximity-map-panel";
import { ProximityResultCard } from "@/components/proximity-result-card";
import { RouteWarningPanel } from "@/components/route-warning-panel";
import { SectionHeader } from "@/components/section-header";
import { ToastMessage } from "@/components/toast";
import { listProximityResults, runNearestFacility, runProximity, runRouteDraft } from "@/lib/api";
import type { ProximityResult } from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

export default function ProximityPage() {
  const [result, setResult] = useState<ProximityResult | null>(null);
  const [recent, setRecent] = useState<ProximityResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  async function refreshRecent() {
    const response = await listProximityResults();
    setRecent(response.proximity_results || []);
  }

  useEffect(() => {
    refreshRecent().catch(() => {
      // Keep the page usable while backend is offline.
    });
  }, []);

  async function runAction(action: () => Promise<{ proximity_result: ProximityResult }>) {
    setLoading(true);
    setError(null);
    try {
      const response = await action();
      setResult(response.proximity_result);
      await refreshRecent();
      setToast({
        tone: response.proximity_result.status === "ok" ? "success" : "warning",
        message: response.proximity_result.status === "ok" ? "Proximity draft created." : "Proximity request needs review.",
      });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Proximity request failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Proximity"
        title="Nearest facility and route drafts"
        description="Create bounded straight-line proximity outputs from a parcel/address origin to verified facilities or destinations."
      />

      <section className="notice notice-warning">
        <strong>Draft proximity workflow</strong>
        <p>
          AutoMap uses bounded local queries and straight-line distance only. Road-network routing is planned only if an
          approved routing/network service is added later.
        </p>
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-main">
          <ProximityForm
            loading={loading}
            onNearest={(origin, target) => runAction(() => runNearestFacility(origin, target))}
            onRouteDraft={(origin, destination) => runAction(() => runRouteDraft(origin, destination))}
            onPrompt={(prompt) => runAction(() => runProximity(prompt))}
          />
          <ProximityResultCard result={result} />
          {result?.route_status === "network_route_not_available" || result?.target_type === "route_to_address" ? (
            <RouteWarningPanel routeStatus={result?.route_status} warnings={result?.warnings || []} />
          ) : null}
          <ProximityMapPanel result={result} />
        </div>
        <aside className="dashboard-side">
          <section className="panel">
            <h3>Safety rules</h3>
            <ul className="check-list">
              <li>Origin matching uses returnGeometry=false first.</li>
              <li>Target searches use bounded rings: 0.5, 1, 2, 5, and 10 miles.</li>
              <li>Candidate downloads are capped.</li>
              <li>No countywide features are downloaded.</li>
              <li>No real ArcGIS item is published.</li>
            </ul>
          </section>
          <section className="panel">
            <h3>Recent proximity results</h3>
            <div className="mini-list">
              {recent.slice(0, 8).map((item) => (
                <button className="small-button" type="button" key={item.proximity_result_id} onClick={() => setResult(item)}>
                  {item.proximity_result_id} - {item.status || "stored"}
                </button>
              ))}
              {!recent.length ? <p className="muted">No proximity results stored yet.</p> : null}
            </div>
          </section>
        </aside>
      </section>

      {error ? (
        <div className="inline-error" role="alert">
          <strong>Proximity issue</strong>
          <p>{error}</p>
        </div>
      ) : null}
      <ToastMessage toast={toast} />
    </div>
  );
}
