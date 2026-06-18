"use client";

import { useEffect, useState } from "react";

import { StatusChip } from "@/components/status-chip";
import { API_BASE_URL, getExhibits } from "@/lib/api";
import type { ExhibitSummary } from "@/types/automap";

function displayDate(value?: string): string {
  if (!value) return "Not recorded";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function fileUrl(url?: string): string {
  return url ? `${API_BASE_URL}${url}` : "#";
}

export function ExhibitReportCenterClient() {
  const [exhibits, setExhibits] = useState<ExhibitSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getExhibits()
      .then((response) => setExhibits(response.exhibits || []))
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Exhibit packages failed to load."));
  }, []);

  return (
    <div className="page-stack">
      <section className="notice notice-warning">
        <strong>Draft exhibit packages</strong>
        <p>These are local staff-report-style exports. They do not publish ArcGIS items and remain draft-only.</p>
      </section>
      {error ? <p className="error-text">{error}</p> : null}
      <section className="card-grid">
        {exhibits.map((exhibit) => {
          const html = exhibit.files?.find((file) => file.name === "exhibit.html");
          const data = exhibit.files?.find((file) => file.name === "exhibit_data.json");
          const csv = exhibit.files?.find((file) => file.name === "layer_sources.csv");
          return (
            <article className="panel" key={exhibit.exhibit_id || exhibit.exhibit_folder}>
              <div className="panel-title-row">
                <div>
                  <p className="eyebrow">{exhibit.exhibit_type?.replaceAll("_", " ") || "exhibit"}</p>
                  <h3>{exhibit.exhibit_title || "AutoMap exhibit"}</h3>
                  <p className="muted">{exhibit.source_prompt}</p>
                </div>
                <StatusChip tone="warning">Draft</StatusChip>
              </div>
              <p className="muted">Created: {displayDate(exhibit.created_at)}</p>
              <p className="path-text">{exhibit.exhibit_folder}</p>
              <div className="button-row">
                {html ? (
                  <a className="button" href={fileUrl(html.url)} target="_blank" rel="noreferrer">
                    Open HTML
                  </a>
                ) : null}
                {data ? (
                  <a className="button button-secondary" href={fileUrl(data.url)} target="_blank" rel="noreferrer">
                    Data JSON
                  </a>
                ) : null}
                {csv ? (
                  <a className="button button-secondary" href={fileUrl(csv.url)} target="_blank" rel="noreferrer">
                    Layer CSV
                  </a>
                ) : null}
              </div>
            </article>
          );
        })}
        {!exhibits.length && !error ? (
          <section className="panel empty-state">
            <h3>No exhibit packages yet</h3>
            <p>Generate one from Map Composer after creating a preview-ready map.</p>
          </section>
        ) : null}
      </section>
    </div>
  );
}
