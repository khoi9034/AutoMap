"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";

import { TableExportCard } from "@/components/table-export-card";
import { TablePreviewGrid } from "@/components/table-preview-grid";
import { TableRecipeCard } from "@/components/table-recipe-card";
import { TableRequestPanel } from "@/components/table-request-panel";
import { TableSafetyWarning } from "@/components/table-safety-warning";
import { exportTableRequest, planTableRequest, previewTableRequest } from "@/lib/api";
import type { TableExportResponse, TableRecipe } from "@/types/automap";

export function TableCenterClient() {
  const searchParams = useSearchParams();
  const [prompt, setPrompt] = useState(searchParams.get("prompt") || "Give me a table of parcels in Concord.");
  const [recipe, setRecipe] = useState<TableRecipe | null>(null);
  const [exportResult, setExportResult] = useState<TableExportResponse | null>(null);
  const [loading, setLoading] = useState<"plan" | "export" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function plan() {
    setLoading("plan");
    setError(null);
    setExportResult(null);
    try {
      const result = await planTableRequest(prompt);
      const planned = result.table_recipe || null;
      if (planned) {
        const preview = await previewTableRequest(planned);
        setRecipe({ ...planned, preview_rows: preview.preview_rows || [] });
      } else {
        setRecipe(null);
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Table planning failed.");
    } finally {
      setLoading(null);
    }
  }

  async function exportRows() {
    if (!recipe) return;
    setLoading("export");
    setError(null);
    try {
      setExportResult(await exportTableRequest(recipe));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Table export failed.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="page-stack">
      {error ? <section className="notice notice-danger">{error}</section> : null}
      <div className="two-column-layout">
        <div className="page-stack">
          <TableRequestPanel loading={loading === "plan"} onPlan={plan} prompt={prompt} setPrompt={setPrompt} />
          <TablePreviewGrid recipe={recipe} />
        </div>
        <aside className="page-stack">
          <TableSafetyWarning recipe={recipe} />
          <TableRecipeCard recipe={recipe} />
          <TableExportCard exportResult={exportResult} loading={loading === "export"} onExport={exportRows} recipe={recipe} />
        </aside>
      </div>
    </div>
  );
}
