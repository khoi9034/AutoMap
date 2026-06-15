import type {
  DataGap,
  HistoryRow,
  LayerRecord,
  MapRecipe,
  PacketsResponse,
  PreviewConfig,
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

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout: ReturnType<typeof setTimeout> = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      cache: "no-store",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
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
      version: "1.6.0",
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

export async function searchCatalog(query: string): Promise<{ query: string; rows: LayerRecord[] }> {
  return apiFetch<{ query: string; rows: LayerRecord[] }>(`/api/catalog/search?q=${encodeURIComponent(query)}`);
}

export async function getDataGaps(): Promise<{ rows: DataGap[] }> {
  return apiFetch<{ rows: DataGap[] }>("/api/data-gaps");
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
