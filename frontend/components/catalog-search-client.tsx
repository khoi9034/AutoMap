"use client";

import { useEffect, useState } from "react";

import { StatusChip } from "@/components/status-chip";
import { searchCatalog } from "@/lib/api";
import type { LayerRecord } from "@/types/automap";

export function CatalogSearchClient() {
  const [query, setQuery] = useState("flood");
  const [rows, setRows] = useState<LayerRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function runSearch(nextQuery = query) {
    setLoading(true);
    setError(null);
    try {
      const response = await searchCatalog(nextQuery);
      setRows(response.rows || []);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Catalog search failed.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    runSearch("flood");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="page-stack">
      <section className="panel form-grid">
        <label htmlFor="catalog-query">
          <strong>Search layer catalog</strong>
        </label>
        <div className="button-row">
          <input
            className="text-input"
            id="catalog-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="flood, zoning, schools, parcels"
          />
          <button className="button" type="button" onClick={() => runSearch()} disabled={loading}>
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="panel">
        <h3>Results</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Layer</th>
                <th>Category</th>
                <th>Source</th>
                <th>Priority</th>
                <th>Verified</th>
                <th>Historical</th>
                <th>URL</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.layer_key || row.layer_url}>
                  <td>{row.layer_name}</td>
                  <td>{row.category}</td>
                  <td>{row.source_status}</td>
                  <td>{row.source_priority}</td>
                  <td>
                    <StatusChip tone={row.is_verified ? "success" : "warning"}>{String(row.is_verified)}</StatusChip>
                  </td>
                  <td>{String(row.is_historical || false)}</td>
                  <td>{row.layer_url}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
