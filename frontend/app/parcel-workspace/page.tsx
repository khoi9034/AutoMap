"use client";

import { useEffect, useState } from "react";

import { ParcelCandidateTable } from "@/components/parcel-candidate-table";
import { ParcelContextLayerPicker } from "@/components/parcel-context-layer-picker";
import { ParcelContextSummary } from "@/components/parcel-context-summary";
import { ParcelFieldStatus } from "@/components/parcel-field-status";
import { ParcelInputPanel } from "@/components/parcel-input-panel";
import { ParcelMatchTable } from "@/components/parcel-match-table";
import { ParcelNearbyControls } from "@/components/parcel-nearby-controls";
import { ParcelReportCard } from "@/components/parcel-report-card";
import { ProximityResultCard } from "@/components/proximity-result-card";
import { SelectedParcelLayerCard } from "@/components/selected-parcel-layer-card";
import { SectionHeader } from "@/components/section-header";
import { StatusChip } from "@/components/status-chip";
import { ToastMessage } from "@/components/toast";
import {
  createParcelContext,
  fetchSelectedParcelGeometry,
  generateParcelReport,
  listParcelSets,
  profileParcelFields,
  runNearestFacility,
  runRouteDraft,
} from "@/lib/api";
import type {
  MapRecipe,
  ParcelFieldProfileResponse,
  ParcelParseResult,
  ParcelReport,
  ParcelSet,
  ProximityResult,
  SelectedParcelGeometryResult,
} from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

const DEFAULT_TOPICS = ["zoning", "flood", "schools", "transportation"];

export default function ParcelWorkspacePage() {
  const [parseResult, setParseResult] = useState<ParcelParseResult | null>(null);
  const [parcelSet, setParcelSet] = useState<ParcelSet | null>(null);
  const [recentSets, setRecentSets] = useState<ParcelSet[]>([]);
  const [selectedTopics, setSelectedTopics] = useState<string[]>(DEFAULT_TOPICS);
  const [nearbyDistance, setNearbyDistance] = useState("0.25 miles");
  const [recipe, setRecipe] = useState<MapRecipe | null>(null);
  const [report, setReport] = useState<ParcelReport | null>(null);
  const [fieldProfile, setFieldProfile] = useState<ParcelFieldProfileResponse | null>(null);
  const [geometryResult, setGeometryResult] = useState<SelectedParcelGeometryResult | null>(null);
  const [proximityResult, setProximityResult] = useState<ProximityResult | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  async function refreshSets() {
    const response = await listParcelSets();
    setRecentSets(response.parcel_sets || []);
  }

  useEffect(() => {
    refreshSets().catch(() => {
      // Keep the workspace usable while backend is offline.
    });
  }, []);

  async function runFieldProfile() {
    setLoading("profile");
    setError(null);
    try {
      const response = await profileParcelFields();
      setFieldProfile(response);
      setToast({ tone: "success", message: "Verified parcel and address field maps updated." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Parcel field profiling failed.");
    } finally {
      setLoading(null);
    }
  }

  async function runFetchSelectedGeometry() {
    const parcelSetId = parcelSet?.parcel_set_id;
    if (!parcelSetId) {
      setToast({ tone: "warning", message: "Match parcels before fetching selected parcel geometry." });
      return;
    }
    setLoading("geometry");
    setError(null);
    try {
      const response = await fetchSelectedParcelGeometry(parcelSetId);
      setGeometryResult(response);
      if (response.geometry_output_path) {
        setParcelSet({ ...parcelSet, geometry_output_path: response.geometry_output_path, downloaded_geometry: true });
      }
      await refreshSets();
      setToast({
        tone: response.status === "ok" ? "success" : "warning",
        message: response.status === "ok" ? "Selected parcel GeoJSON created." : "Selected parcel geometry was blocked by safety checks.",
      });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Selected parcel geometry fetch failed.");
    } finally {
      setLoading(null);
    }
  }

  async function createContext() {
    const prompt =
      parcelSet?.raw_input ||
      parseResult?.raw_input ||
      "Make a parcel context map with zoning, floodplain, schools, and roads.";
    setLoading("context");
    setError(null);
    try {
      const response = await createParcelContext({
        prompt,
        parcel_set_id: parcelSet?.parcel_set_id || null,
        requested_topics: selectedTopics,
        nearby_distance: nearbyDistance || null,
      });
      setRecipe(response.recipe || response.parcel_context_session.context_recipe || null);
      if (response.parcel_context_session.parcel_set_id) {
        setParcelSet({
          ...(parcelSet || {}),
          parcel_set_id: response.parcel_context_session.parcel_set_id,
        });
      }
      await refreshSets();
      setToast({ tone: "success", message: "Parcel context recipe created." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Parcel context generation failed.");
    } finally {
      setLoading(null);
    }
  }

  async function runReport() {
    const parcelSetId = parcelSet?.parcel_set_id || recipe?.parcel_context?.parcel_set_id;
    if (!parcelSetId) {
      setToast({ tone: "warning", message: "Create a parcel set before generating a parcel report." });
      return;
    }
    setLoading("report");
    setError(null);
    try {
      const generated = await generateParcelReport(parcelSetId);
      setReport(generated);
      setToast({ tone: "success", message: "Parcel report generated under outputs/parcel_reports." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Parcel report generation failed.");
    } finally {
      setLoading(null);
    }
  }

  async function runParcelProximity(targetType: string) {
    const origin = parcelSet?.raw_input || parseResult?.raw_input;
    if (!origin) {
      setToast({ tone: "warning", message: "Match or parse a parcel/address before running proximity." });
      return;
    }
    setLoading(`proximity-${targetType}`);
    setError(null);
    try {
      const response = await runNearestFacility(origin, targetType);
      setProximityResult(response.proximity_result);
      setToast({
        tone: response.proximity_result.status === "ok" ? "success" : "warning",
        message: response.proximity_result.status === "ok" ? "Proximity result created." : "Proximity result needs review.",
      });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Parcel proximity request failed.");
    } finally {
      setLoading(null);
    }
  }

  async function runParcelRouteDraft() {
    const origin = parcelSet?.raw_input || parseResult?.raw_input;
    if (!origin) {
      setToast({ tone: "warning", message: "Match or parse a parcel/address before running a route draft." });
      return;
    }
    const destination = window.prompt("Destination address for route draft");
    if (!destination) {
      return;
    }
    setLoading("route-draft");
    setError(null);
    try {
      const response = await runRouteDraft(origin, destination);
      setProximityResult(response.proximity_result);
      setToast({ tone: "warning", message: "Route draft created as straight-line reference only." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Route draft failed.");
    } finally {
      setLoading(null);
    }
  }

  function handleRecentSetClick(item: ParcelSet) {
    setParcelSet(item);
    setParseResult({
      raw_input: item.raw_input,
      input_type: item.input_type,
      parsed_identifiers: item.parsed_identifiers,
    });
    setRecipe(null);
    setReport(null);
  }

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Parcel Workspace"
        title="Parcel-centered map requests"
        description="Parse parcel IDs, PIN/PIN14 values, addresses, and pasted parcel lists, then build safe parcel context maps and local reports."
      />

      <section className="notice notice-warning">
        <strong>Draft parcel review only</strong>
        <p>
          AutoMap does not bulk-ingest parcels, does not download countywide parcel geometry, and does not treat proxy
          planning/development activity as official approvals.
        </p>
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-main">
          <ParcelInputPanel
            onParsed={(result) => {
              setParseResult(result);
              setToast({ tone: "success", message: "Parcel identifiers parsed." });
            }}
            onParcelSet={(created) => {
              setParcelSet(created);
              setRecipe(null);
              setReport(null);
              setGeometryResult(null);
              void refreshSets();
              setToast({ tone: created.match_status === "matched" ? "success" : "warning", message: "Parcel matching complete." });
            }}
            onError={setError}
          />
          <ParcelMatchTable parseResult={parseResult} parcelSet={parcelSet} />
          <ParcelCandidateTable candidates={parcelSet?.candidate_matches || []} />
          <ParcelContextLayerPicker
            selectedTopics={selectedTopics}
            onChange={setSelectedTopics}
          />
          <ParcelNearbyControls nearbyDistance={nearbyDistance} onDistanceChange={setNearbyDistance} />
          <SelectedParcelLayerCard
            parcelSet={parcelSet}
            geometryResult={geometryResult}
            loading={loading === "geometry"}
            onFetch={runFetchSelectedGeometry}
          />
          <section className="panel">
            <div className="panel-title-row">
              <div>
                <h3>Build context outputs</h3>
                <p className="muted">Generate a parcel context recipe or local report. Nothing is published.</p>
              </div>
              <StatusChip tone="warning">Local draft</StatusChip>
            </div>
            <div className="button-row">
              <button className="button" type="button" onClick={createContext} disabled={loading === "context"}>
                {loading === "context" ? "Generating..." : "Generate Parcel Context"}
              </button>
              <button
                className="button button-secondary"
                type="button"
                onClick={runReport}
                disabled={loading === "report" || !(parcelSet?.parcel_set_id || recipe?.parcel_context?.parcel_set_id)}
              >
                {loading === "report" ? "Generating..." : "Generate Parcel Report"}
              </button>
            </div>
          </section>
          <section className="panel">
            <div className="panel-title-row">
              <div>
                <h3>Parcel proximity actions</h3>
                <p className="muted">Use the current parcel/address input as the origin for bounded nearest-facility drafts.</p>
              </div>
              <StatusChip tone="warning">Straight-line</StatusChip>
            </div>
            <div className="button-row">
              <button className="button button-secondary" type="button" onClick={() => runParcelProximity("nearest_school")}>
                Nearest School
              </button>
              <button className="button button-secondary" type="button" onClick={() => runParcelProximity("nearest_fire_station")}>
                Nearest Fire Station
              </button>
              <button className="button button-secondary" type="button" onClick={() => runParcelProximity("containing_fire_district")}>
                Containing Fire District
              </button>
              <button className="button button-secondary" type="button" onClick={runParcelRouteDraft}>
                Route Draft to Address
              </button>
            </div>
          </section>
          <ProximityResultCard result={proximityResult} />
          <ParcelContextSummary parcelSet={parcelSet} recipe={recipe} />
        </div>

        <aside className="dashboard-side">
          <ParcelFieldStatus profile={fieldProfile} loading={loading === "profile"} onProfile={runFieldProfile} />
          <section className="panel safety-card">
            <h3>Parcel safety rules</h3>
            <ul className="check-list">
              <li>Tax Parcels is selected from the verified catalog.</li>
              <li>Matching uses returnGeometry=false first.</li>
              <li>Unmatched identifiers stay visible.</li>
              <li>Nearby activity uses proxy and limited-coverage warnings.</li>
              <li>Current permits remain unresolved unless an official verified source is added.</li>
            </ul>
          </section>
          <section className="panel">
            <div className="panel-title-row">
              <h3>Recent parcel sets</h3>
              <StatusChip>{recentSets.length}</StatusChip>
            </div>
            <div className="mini-list">
              {recentSets.slice(0, 8).map((item) => (
                <button className="small-button" type="button" key={item.parcel_set_id} onClick={() => handleRecentSetClick(item)}>
                  {item.parcel_set_id} - {item.match_status}
                </button>
              ))}
              {!recentSets.length ? <p className="muted">No parcel sets stored yet.</p> : null}
            </div>
          </section>
          <ParcelReportCard report={report} />
        </aside>
      </section>

      {error ? (
        <div className="inline-error" role="alert">
          <strong>Parcel Workspace issue</strong>
          <p>{error}</p>
        </div>
      ) : null}
      <ToastMessage toast={toast} />
    </div>
  );
}
