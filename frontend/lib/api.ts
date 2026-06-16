import type {
  ClarificationAnswerModel,
  ClarificationDefault,
  ClarificationSession,
  DataGap,
  DataGapCandidate,
  ExternalSource,
  AnalysisRefinementSession,
  AnalysisReportSummary,
  AnalysisRun,
  ApprovedPattern,
  FeedbackLogRow,
  HistoryRow,
  LayerRecord,
  MapRecipe,
  PacketsResponse,
  PreviewConfig,
  GenerateReportResponse,
  ReportDetail,
  ReportSummary,
  SystemStatus,
} from "@/types/automap";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_AUTOMAP_API_BASE_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8010";

const PROTECTED_MARKERS = [
  ".env",
  "arcgis_password",
  "arcgis_username",
  "cfs",
  "cfs_dev",
  "database_url",
  "password",
  "postgres_admin_url",
  "secret",
  "token",
];

function hasProtectedMarker(value: string): boolean {
  const lowered = value.toLowerCase();
  return PROTECTED_MARKERS.some((marker) => lowered.includes(marker));
}

export function redactProtected<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((item) => redactProtected(item)) as T;
  }
  if (value && typeof value === "object") {
    const safe: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value)) {
      if (!hasProtectedMarker(key)) {
        safe[key] = redactProtected(item);
      }
    }
    return safe as T;
  }
  if (typeof value === "string" && hasProtectedMarker(value)) {
    return "[redacted]" as T;
  }
  return value;
}

type ApiFetchInit = RequestInit & { timeoutMs?: number };

async function apiFetch<T>(path: string, init?: ApiFetchInit): Promise<T> {
  const controller = new AbortController();
  const timeoutMs = init?.timeoutMs ?? 15000;
  const fetchInit: RequestInit = { ...(init || {}) };
  delete (fetchInit as ApiFetchInit).timeoutMs;
  const timeout: ReturnType<typeof setTimeout> = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...fetchInit,
      cache: "no-store",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(fetchInit.headers || {}),
      },
    });
    if (!response.ok) {
      let detail = `${response.status} ${response.statusText}`;
      try {
        const body = (await response.json()) as { detail?: string };
        detail = body.detail || detail;
      } catch {
        // Keep HTTP status detail.
      }
      throw new Error(detail);
    }
    return redactProtected((await response.json()) as T);
  } catch (exc) {
    if (exc instanceof Error && exc.name === "AbortError") {
      throw new Error("Backend API request timed out. Confirm AutoMap is running on http://127.0.0.1:8010.");
    }
    throw exc;
  } finally {
    clearTimeout(timeout);
  }
}

export async function getSystemStatus(): Promise<SystemStatus> {
  return apiFetch<SystemStatus>("/api/status");
}

export async function getStatus(): Promise<SystemStatus> {
  return getSystemStatus();
}

export async function getStatusOrFallback(): Promise<SystemStatus> {
  try {
    return await getSystemStatus();
  } catch {
    return {
      version: "2.4.0",
      database_connected: false,
      catalog: {},
      profiles: {},
      packets: {},
      real_publish_enabled: false,
      arcgis_publisher_mode: "backend unavailable",
      errors: ["Backend API is not reachable."],
    };
  }
}

export async function getPatterns(): Promise<{
  patterns: ApprovedPattern[];
  clarification_defaults: ClarificationDefault[];
  feedback_log: FeedbackLogRow[];
}> {
  return apiFetch<{
    patterns: ApprovedPattern[];
    clarification_defaults: ClarificationDefault[];
    feedback_log: FeedbackLogRow[];
  }>("/api/patterns");
}

export async function getPattern(patternKey: string): Promise<ApprovedPattern> {
  return apiFetch<ApprovedPattern>(`/api/patterns/${encodeURIComponent(patternKey)}`);
}

export async function learnFromApprovedPacket(approvedPacketFolder: string): Promise<{ pattern: ApprovedPattern }> {
  return apiFetch<{ pattern: ApprovedPattern }>("/api/patterns/learn-from-approved", {
    method: "POST",
    body: JSON.stringify({ approved_packet_folder: approvedPacketFolder }),
  });
}

export async function getClarificationDefaults(): Promise<{ defaults: ClarificationDefault[] }> {
  return apiFetch<{ defaults: ClarificationDefault[] }>("/api/clarification-defaults");
}

export async function planAnalysis(
  prompt: string,
): Promise<{ prompt: string; analysis_plan: Record<string, unknown> }> {
  return apiFetch<{ prompt: string; analysis_plan: Record<string, unknown> }>("/api/analysis/plan", {
    method: "POST",
    timeoutMs: 180000,
    body: JSON.stringify({ prompt }),
  });
}

export async function executeAnalysis(prompt: string): Promise<{ prompt: string; analysis_result: AnalysisRun }> {
  return apiFetch<{ prompt: string; analysis_result: AnalysisRun }>("/api/analysis/execute", {
    method: "POST",
    timeoutMs: 300000,
    body: JSON.stringify({ prompt }),
  });
}

export async function listAnalysisRuns(): Promise<{ analysis_runs: AnalysisRun[] }> {
  return apiFetch<{ analysis_runs: AnalysisRun[] }>("/api/analysis/runs");
}

export async function getAnalysisRun(analysisRunId: string): Promise<AnalysisRun> {
  return apiFetch<AnalysisRun>(`/api/analysis/runs/${encodeURIComponent(analysisRunId)}`);
}

export async function createAnalysisRefinement(
  analysisRunId: string,
): Promise<{ refinement_session: AnalysisRefinementSession }> {
  return apiFetch<{ refinement_session: AnalysisRefinementSession }>("/api/analysis/refinements", {
    method: "POST",
    timeoutMs: 120000,
    body: JSON.stringify({ analysis_run_id: analysisRunId }),
  });
}

export async function listAnalysisRefinements(): Promise<{ refinement_sessions: AnalysisRefinementSession[] }> {
  return apiFetch<{ refinement_sessions: AnalysisRefinementSession[] }>("/api/analysis/refinements");
}

export async function getAnalysisRefinement(sessionId: string): Promise<AnalysisRefinementSession> {
  return apiFetch<AnalysisRefinementSession>(`/api/analysis/refinements/${encodeURIComponent(sessionId)}`);
}

export async function selectAnalysisRefinement(
  sessionId: string,
  optionId: string,
  parameters: Record<string, unknown> = {},
): Promise<{ refinement_session: AnalysisRefinementSession }> {
  return apiFetch<{ refinement_session: AnalysisRefinementSession }>(
    `/api/analysis/refinements/${encodeURIComponent(sessionId)}/select`,
    {
      method: "POST",
      body: JSON.stringify({ option_id: optionId, parameters }),
    },
  );
}

export async function executeAnalysisRefinement(
  sessionId: string,
): Promise<{ refinement_session: AnalysisRefinementSession }> {
  return apiFetch<{ refinement_session: AnalysisRefinementSession }>(
    `/api/analysis/refinements/${encodeURIComponent(sessionId)}/execute`,
    {
      method: "POST",
      timeoutMs: 180000,
      body: JSON.stringify({}),
    },
  );
}

export async function generateAnalysisReport(
  analysisRunId: string,
): Promise<AnalysisReportSummary> {
  return apiFetch<AnalysisReportSummary>("/api/analysis/reports", {
    method: "POST",
    timeoutMs: 180000,
    body: JSON.stringify({ analysis_run_id: analysisRunId }),
  });
}

export async function generateAnalysisReportFromRefinement(
  refinementSessionId: string,
): Promise<AnalysisReportSummary> {
  return apiFetch<AnalysisReportSummary>("/api/analysis/reports/from-refinement", {
    method: "POST",
    timeoutMs: 180000,
    body: JSON.stringify({ refinement_session_id: refinementSessionId }),
  });
}

export async function listAnalysisReports(): Promise<{ analysis_reports: AnalysisReportSummary[] }> {
  return apiFetch<{ analysis_reports: AnalysisReportSummary[] }>("/api/analysis/reports");
}

export async function getAnalysisReport(reportId: string): Promise<AnalysisReportSummary> {
  return apiFetch<AnalysisReportSummary>(`/api/analysis/reports/${encodeURIComponent(reportId)}`);
}

export async function recordRecipeFeedback(payload: {
  raw_prompt: string;
  recipe: Record<string, unknown>;
  feedback_type: string;
  feedback_json?: Record<string, unknown>;
  source_packet_path?: string;
}): Promise<{ feedback: FeedbackLogRow }> {
  return apiFetch<{ feedback: FeedbackLogRow }>("/api/feedback/recipe", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function learnFromClarificationSession(sessionId: string): Promise<{ feedback: FeedbackLogRow }> {
  return apiFetch<{ feedback: FeedbackLogRow }>(`/api/clarification/${encodeURIComponent(sessionId)}/learn`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function searchCatalog(query: string): Promise<{ query: string; rows: LayerRecord[] }> {
  return apiFetch<{ query: string; rows: LayerRecord[] }>(`/api/catalog/search?q=${encodeURIComponent(query)}`);
}

export async function getDataGaps(): Promise<{ rows: DataGap[] }> {
  return apiFetch<{ rows: DataGap[] }>("/api/data-gaps");
}

export async function getGapCandidates(gapKey: string): Promise<{ gap_key: string; candidates: DataGapCandidate[] }> {
  return apiFetch<{ gap_key: string; candidates: DataGapCandidate[] }>(
    `/api/data-gaps/${encodeURIComponent(gapKey)}/candidates`,
  );
}

export async function resolveDataGap(payload: {
  gap_key: string;
  source_key?: string;
  resolution_status?: string;
  notes?: string;
}): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/data-gaps/resolve", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getExternalSources(): Promise<{ external_sources: ExternalSource[] }> {
  return apiFetch<{ external_sources: ExternalSource[] }>("/api/external-sources");
}

export async function loadExternalSources(): Promise<{ loaded: number; sources: ExternalSource[] }> {
  return apiFetch<{ loaded: number; sources: ExternalSource[] }>("/api/external-sources/load", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function inspectExternalSources(): Promise<{
  inspected: number;
  catalog_upserts: number;
  sources: ExternalSource[];
}> {
  return apiFetch<{ inspected: number; catalog_upserts: number; sources: ExternalSource[] }>("/api/external-sources/inspect", {
    method: "POST",
    timeoutMs: 180000,
    body: JSON.stringify({}),
  });
}

export async function getHistory(): Promise<{ request_history: HistoryRow[]; approval_history: HistoryRow[] }> {
  return apiFetch<{ request_history: HistoryRow[]; approval_history: HistoryRow[] }>("/api/history");
}

export async function listPackets(): Promise<PacketsResponse> {
  return apiFetch<PacketsResponse>("/api/packets");
}

export async function getPackets(): Promise<PacketsResponse> {
  return listPackets();
}

export async function getPreviewConfig(packetId: string): Promise<PreviewConfig> {
  return apiFetch<PreviewConfig>(`/api/preview-config/${encodeURIComponent(packetId)}`);
}

export async function getReports(): Promise<{ reports: ReportSummary[] }> {
  return apiFetch<{ reports: ReportSummary[] }>("/api/reports");
}

export async function getReport(reportId: string): Promise<ReportDetail> {
  return apiFetch<ReportDetail>(`/api/reports/${encodeURIComponent(reportId)}`);
}

export async function generateReport(packetFolder: string): Promise<GenerateReportResponse> {
  return apiFetch<GenerateReportResponse>("/api/generate-report", {
    method: "POST",
    body: JSON.stringify({ packet_folder: packetFolder }),
  });
}

export async function startClarification(prompt: string): Promise<ClarificationSession> {
  return apiFetch<ClarificationSession>("/api/clarification/start", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export async function getClarificationSession(sessionId: string): Promise<ClarificationSession> {
  return apiFetch<ClarificationSession>(`/api/clarification/${encodeURIComponent(sessionId)}`);
}

export async function listClarificationSessions(): Promise<{ sessions: ClarificationSession[] }> {
  return apiFetch<{ sessions: ClarificationSession[] }>("/api/clarification");
}

export async function answerClarificationSession(
  sessionId: string,
  answers: ClarificationAnswerModel[],
): Promise<ClarificationSession> {
  return apiFetch<ClarificationSession>(`/api/clarification/${encodeURIComponent(sessionId)}/answer`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
}

export async function refineClarificationSession(sessionId: string): Promise<ClarificationSession> {
  return apiFetch<ClarificationSession>(`/api/clarification/${encodeURIComponent(sessionId)}/refine`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function makeRecipe(prompt: string): Promise<{ prompt: string; recipe: MapRecipe; data_gaps: unknown[] }> {
  return apiFetch<{ prompt: string; recipe: MapRecipe; data_gaps: unknown[] }>("/api/recipe", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export async function makeReviewPacket(prompt: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/review-packet", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export async function makeWebmapDraft(prompt: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/webmap-draft", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export async function createAdjustmentTemplate(packetFolder: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/adjustment-template", {
    method: "POST",
    body: JSON.stringify({ packet_folder: packetFolder }),
  });
}

export async function applyAdjustments(packetFolder: string, adjustmentYaml: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/apply-adjustments", {
    method: "POST",
    body: JSON.stringify({ packet_folder: packetFolder, adjustment_yaml: adjustmentYaml }),
  });
}

export async function createApprovalTemplate(adjustedPacketFolder: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/approval-template", {
    method: "POST",
    body: JSON.stringify({ adjusted_packet_folder: adjustedPacketFolder }),
  });
}

export async function applyApproval(adjustedPacketFolder: string, approvalYaml: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/apply-approval", {
    method: "POST",
    body: JSON.stringify({ adjusted_packet_folder: adjustedPacketFolder, approval_yaml: approvalYaml }),
  });
}

export async function dryRunPublish(approvedPacketFolder: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/publish-dry-run", {
    method: "POST",
    body: JSON.stringify({ approved_packet_folder: approvedPacketFolder }),
  });
}

export async function publishDryRun(approvedPacketFolder: string): Promise<Record<string, unknown>> {
  return dryRunPublish(approvedPacketFolder);
}

export async function portalSmokeTestDryRun(approvedPacketFolder: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/api/portal-smoke-test-dry-run", {
    method: "POST",
    body: JSON.stringify({ approved_packet_folder: approvedPacketFolder }),
  });
}
