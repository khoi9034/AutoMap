"use client";

import { useEffect, useMemo, useState } from "react";

import { StatusChip } from "@/components/status-chip";
import { searchCatalog } from "@/lib/api";
import type { LayerRecord } from "@/types/automap";

export function CatalogSearchClient() {
  const [query, setQuery] = useState("flood");
  const [rows, setRows] = useState<LayerRecord[]>([]);
  const [category, setCategory] = useState("all");
  const [sourceStatus, setSourceStatus] = useState("all");
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

  const categories = useMemo(
    () => Array.from(new Set(rows.map((row) => row.category).filter(Boolean) as string[])).sort(),
    [rows],
  );
  const sourceStatuses = useMemo(
    () => Array.from(new Set(rows.map((row) => row.source_status).filter(Boolean) as string[])).sort(),
    [rows],
  );
  const filteredRows = rows.filter((row) => {
    const categoryMatch = category === "all" || row.category === category;
    const sourceMatch = sourceStatus === "all" || row.source_status === sourceStatus;
    return categoryMatch && sourceMatch;
  });

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
        <div className="button-row">
          {["flood", "zoning", "schools", "parcels", "roads"].map((topic) => (
            <button
              className="button button-secondary"
              key={topic}
              type="button"
              onClick={() => {
                setQuery(topic);
                runSearch(topic);
              }}
            >
              {topic}
            </button>
          ))}
        </div>
        <div className="filter-row">
          <label>
            Category
            <select className="select-input" value={category} onChange={(event) => setCategory(event.target.value)}>
              <option value="all">All categories</option>
              {categories.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label>
            Source
            <select className="select-input" value={sourceStatus} onChange={(event) => setSourceStatus(event.target.value)}>
              <option value="all">All sources</option>
              {sourceStatuses.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
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
              {filteredRows.map((row) => (
                <tr key={row.layer_key || row.layer_url}>
                  <td>{row.layer_name}</td>
                  <td>{row.category}</td>
                  <td>{row.source_status}</td>
                  <td>{row.source_priority}</td>
                  <td>
                    <StatusChip tone={row.is_verified ? "success" : "warning"}>{String(row.is_verified)}</StatusChip>
                  </td>
                  <td>{String(row.is_historical || false)}</td>
                  <td className="url-cell">{row.layer_url}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
