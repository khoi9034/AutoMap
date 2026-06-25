"use client";

import type { ComposerLayerEdit } from "@/components/map-composer/types";
import type { ComposerMapState, ComposerResponse } from "@/types/automap";
import type { LivePrintOptions } from "@/types/print-options";

const SESSION_PREFIX = "automap-composer-session:";
const LOCKED_STATE_PREFIX = "automap-locked-map-state:";
const MOST_RECENT_KEY = "automap-composer-most-recent-session";
const TTL_MS = 24 * 60 * 60 * 1000;

export type StoredComposerSession = {
  active_map_view_state?: Partial<ComposerMapState> | null;
  composer_session_id: string;
  layers?: ComposerLayerEdit[];
  map_subtitle?: string;
  map_title?: string;
  notes?: string;
  original_prompt?: string;
  print_options?: LivePrintOptions;
  response: ComposerResponse;
  saved_at: string;
};

function canUseStorage(): boolean {
  return typeof window !== "undefined" && Boolean(window.localStorage);
}

function expired(savedAt?: string): boolean {
  const time = savedAt ? Date.parse(savedAt) : NaN;
  return !Number.isFinite(time) || Date.now() - time > TTL_MS;
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
  const saved = { ...session, saved_at: session.saved_at || new Date().toISOString() };
  writeJson(`${SESSION_PREFIX}${session.composer_session_id}`, saved);
  writeJson(MOST_RECENT_KEY, { composer_session_id: session.composer_session_id, saved_at: saved.saved_at });
}

export function loadComposerSession(composerSessionId: string): StoredComposerSession | null {
  const session = readJson<StoredComposerSession>(`${SESSION_PREFIX}${composerSessionId}`);
  if (!session || expired(session.saved_at)) return null;
  return session;
}

export function loadMostRecentComposerSession(): StoredComposerSession | null {
  const pointer = readJson<{ composer_session_id?: string; saved_at?: string }>(MOST_RECENT_KEY);
  if (!pointer?.composer_session_id || expired(pointer.saved_at)) return null;
  return loadComposerSession(pointer.composer_session_id);
}

export function saveLockedMapState(composerSessionId: string | undefined, state: ComposerMapState | null | undefined): void {
  if (!composerSessionId || !state) return;
  writeJson(`${LOCKED_STATE_PREFIX}${composerSessionId}`, { composer_session_id: composerSessionId, saved_at: new Date().toISOString(), state });
}

export function loadLockedMapState(composerSessionId: string): ComposerMapState | null {
  const payload = readJson<{ saved_at?: string; state?: ComposerMapState }>(`${LOCKED_STATE_PREFIX}${composerSessionId}`);
  if (!payload || expired(payload.saved_at)) return null;
  return payload.state || null;
}

export function clearExpiredSessions(): void {
  if (!canUseStorage()) return;
  try {
    Object.keys(window.localStorage).forEach((key) => {
      if (!key.startsWith(SESSION_PREFIX) && !key.startsWith(LOCKED_STATE_PREFIX)) return;
      const payload = readJson<{ saved_at?: string }>(key);
      if (!payload || expired(payload.saved_at)) window.localStorage.removeItem(key);
    });
    const pointer = readJson<{ saved_at?: string }>(MOST_RECENT_KEY);
    if (pointer && expired(pointer.saved_at)) window.localStorage.removeItem(MOST_RECENT_KEY);
  } catch {
    // Best effort cleanup only.
  }
}
