"use client";

import type { ComposerLayerEdit } from "@/components/map-composer/types";
import type { ComposerMapState, ComposerResponse } from "@/types/automap";
import type { LivePrintOptions } from "@/types/print-options";

const SESSION_PREFIX = "automap-composer-session:";
const LOCKED_STATE_PREFIX = "automap-locked-map-state:";
const PRINT_SNAPSHOT_PREFIX = "automap-print-snapshot:";
const MOST_RECENT_KEY = "automap-composer-most-recent-session";
const SCHEMA_VERSION = 3;
const TTL_MS = 24 * 60 * 60 * 1000;

export type StoredComposerSession = {
  active_map_view_state?: Partial<ComposerMapState> | null;
  composer_session_id: string;
  created_at?: string;
  has_extent?: boolean;
  has_layers?: boolean;
  has_map_payload?: boolean;
  layers?: ComposerLayerEdit[];
  map_subtitle?: string;
  map_title?: string;
  notes?: string;
  original_prompt?: string;
  print_options?: LivePrintOptions;
  response: ComposerResponse;
  saved_at: string;
  schema_version?: number;
  updated_at?: string;
};

function canUseStorage(): boolean {
  return typeof window !== "undefined" && Boolean(window.localStorage);
}

function expired(savedAt?: string): boolean {
  const time = savedAt ? Date.parse(savedAt) : NaN;
  return !Number.isFinite(time) || Date.now() - time > TTL_MS;
}

function previewConfig(response?: ComposerResponse | null) {
  return response?.preview_config || response?.composer_map_state?.preview_config || null;
}

function hasRenderableMapPayload(response?: ComposerResponse | null): boolean {
  const preview = previewConfig(response);
  return Boolean(
    response?.can_preview &&
      (response.packet_id ||
        response.packet_path ||
        preview?.focus_extent ||
        preview?.initial_extent ||
        preview?.derived_overlays?.length ||
        preview?.context_layers?.length ||
        preview?.operational_layers?.length ||
        response.proximity_result?.derived_overlays?.length),
  );
}

function hasRenderableLayers(session: StoredComposerSession): boolean {
  const preview = previewConfig(session.response);
  return Boolean(
    session.layers?.length ||
      preview?.derived_overlays?.length ||
      preview?.context_layers?.length ||
      preview?.operational_layers?.length ||
      session.response.proximity_result?.derived_overlays?.length ||
      session.response.packet_id ||
      session.response.packet_path,
  );
}

function hasUsableExtent(response?: ComposerResponse | null): boolean {
  const preview = previewConfig(response);
  return Boolean(preview?.focus_extent || preview?.initial_extent || response?.composer_map_state?.map_extent);
}

function isUsableSession(session: StoredComposerSession | null): session is StoredComposerSession {
  return Boolean(
    session &&
      session.schema_version === SCHEMA_VERSION &&
      !expired(session.updated_at || session.saved_at) &&
      session.composer_session_id &&
      session.response?.composer_session_id === session.composer_session_id &&
      session.has_extent &&
      session.has_map_payload &&
      session.has_layers &&
      hasUsableExtent(session.response) &&
      hasRenderableMapPayload(session.response) &&
      hasRenderableLayers(session),
  );
}

function safeJson<T>(value: T): T {
  return JSON.parse(
    JSON.stringify(value, (key, nested) => {
      const lowered = String(key).toLowerCase();
      if (
        lowered.includes("password") ||
        lowered.includes("secret") ||
        lowered.includes("token") ||
        lowered === "database_url" ||
        lowered === "owner" ||
        lowered === "owner_name"
      ) {
        return undefined;
      }
      if (lowered === "debug_details") return undefined;
      return nested;
    }),
  ) as T;
}

function readJson<T>(key: string): T | null {
  if (!canUseStorage()) return null;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function writeJson(key: string, value: unknown): void {
  if (!canUseStorage()) return;
  try {
    window.localStorage.setItem(key, JSON.stringify(safeJson(value)));
  } catch {
    // Storage is a best-effort safety net; live React state remains primary.
  }
}

export function saveComposerSession(session: Omit<StoredComposerSession, "saved_at"> & { saved_at?: string }): void {
  if (!session.composer_session_id) return;
  const existing = readJson<StoredComposerSession>(`${SESSION_PREFIX}${session.composer_session_id}`);
  const now = new Date().toISOString();
  const saved = {
    ...session,
    created_at: session.created_at || existing?.created_at || now,
    has_extent: hasUsableExtent(session.response),
    has_layers: hasRenderableLayers(session as StoredComposerSession),
    has_map_payload: hasRenderableMapPayload(session.response),
    saved_at: session.saved_at || now,
    schema_version: SCHEMA_VERSION,
    updated_at: now,
  };
  if (!isUsableSession(saved)) return;
  writeJson(`${SESSION_PREFIX}${session.composer_session_id}`, saved);
  writeJson(MOST_RECENT_KEY, { composer_session_id: session.composer_session_id, saved_at: saved.updated_at });
}

export function loadComposerSession(composerSessionId: string): StoredComposerSession | null {
  const key = `${SESSION_PREFIX}${composerSessionId}`;
  const session = readJson<StoredComposerSession>(`${SESSION_PREFIX}${composerSessionId}`);
  if (!isUsableSession(session)) {
    if (canUseStorage()) window.localStorage.removeItem(key);
    return null;
  }
  return session;
}

export function loadMostRecentComposerSession(): StoredComposerSession | null {
  const pointer = readJson<{ composer_session_id?: string; saved_at?: string }>(MOST_RECENT_KEY);
  if (!pointer?.composer_session_id || expired(pointer.saved_at)) return null;
  return loadComposerSession(pointer.composer_session_id);
}

export function saveLockedMapState(composerSessionId: string | undefined, state: ComposerMapState | null | undefined): void {
  if (!composerSessionId || !state) return;
  if (!state.preview_config && !state.map_extent && !state.derived_overlays?.length) return;
  writeJson(`${LOCKED_STATE_PREFIX}${composerSessionId}`, {
    composer_session_id: composerSessionId,
    saved_at: new Date().toISOString(),
    schema_version: SCHEMA_VERSION,
    state,
  });
}

export function loadLockedMapState(composerSessionId: string): ComposerMapState | null {
  const payload = readJson<{ saved_at?: string; schema_version?: number; state?: ComposerMapState }>(`${LOCKED_STATE_PREFIX}${composerSessionId}`);
  if (!payload || payload.schema_version !== SCHEMA_VERSION || expired(payload.saved_at)) return null;
  return payload.state || null;
}

export function savePrintSnapshot(composerSessionId: string | undefined, dataUrl: string | null | undefined): void {
  if (!composerSessionId || !dataUrl?.startsWith("data:image/")) return;
  writeJson(`${PRINT_SNAPSHOT_PREFIX}${composerSessionId}`, {
    composer_session_id: composerSessionId,
    data_url: dataUrl,
    saved_at: new Date().toISOString(),
    schema_version: SCHEMA_VERSION,
  });
}

export function loadPrintSnapshot(composerSessionId: string): string | null {
  const payload = readJson<{ data_url?: string; saved_at?: string; schema_version?: number }>(`${PRINT_SNAPSHOT_PREFIX}${composerSessionId}`);
  if (!payload || payload.schema_version !== SCHEMA_VERSION || expired(payload.saved_at) || !payload.data_url?.startsWith("data:image/")) return null;
  return payload.data_url;
}

export function clearExpiredSessions(): void {
  if (!canUseStorage()) return;
  try {
    Object.keys(window.localStorage).forEach((key) => {
      if (!key.startsWith(SESSION_PREFIX) && !key.startsWith(LOCKED_STATE_PREFIX) && !key.startsWith(PRINT_SNAPSHOT_PREFIX)) return;
      const payload = readJson<{ saved_at?: string; schema_version?: number; updated_at?: string }>(key);
      if (!payload || payload.schema_version !== SCHEMA_VERSION || expired(payload.updated_at || payload.saved_at)) window.localStorage.removeItem(key);
    });
    const pointer = readJson<{ saved_at?: string }>(MOST_RECENT_KEY);
    if (pointer && expired(pointer.saved_at)) window.localStorage.removeItem(MOST_RECENT_KEY);
  } catch {
    // Best effort cleanup only.
  }
}
