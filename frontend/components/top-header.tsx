"use client";

import { useEffect, useMemo, useState } from "react";

import { getApiRuntimeInfo, getStatusOrFallback } from "@/lib/api";
import type { SystemStatus } from "@/types/automap";

type TopHeaderProps = {
  status: SystemStatus;
};

export function TopHeader({ status }: TopHeaderProps) {
  const [liveStatus, setLiveStatus] = useState(status);
  const [statusChecked, setStatusChecked] = useState(false);
  const apiInfo = useMemo(() => getApiRuntimeInfo(), []);
  const isProduction = apiInfo.isProduction && !apiInfo.isLocal;

  useEffect(() => {
    let cancelled = false;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const refreshStatus = () => {
      getStatusOrFallback()
        .then((nextStatus) => {
          if (!cancelled) {
            setLiveStatus(nextStatus);
            setStatusChecked(true);
            if (nextStatus.errors?.length) {
              retryTimer = setTimeout(refreshStatus, 15000);
            }
          }
        })
        .catch(() => {
          if (!cancelled) {
            setStatusChecked(true);
            retryTimer = setTimeout(refreshStatus, 15000);
          }
        });
    };

    refreshStatus();
    return () => {
      cancelled = true;
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, []);

  const frontendLabel = isProduction ? "Vercel" : liveStatus.ports?.frontend || 3010;
  const backendUnavailable = Boolean(
    liveStatus.errors?.some((error) => error.toLowerCase().includes("backend api is not reachable")),
  );
  const publicStatusDelay = Boolean(liveStatus.errors?.length);
  const apiLabel = isProduction
    ? backendUnavailable
      ? "Demo Mode"
      : !statusChecked || publicStatusDelay
        ? "Waking"
        : "Live"
    : liveStatus.ports?.backend_api || 8010;
  const apiChipClass = isProduction
    ? backendUnavailable || !statusChecked || publicStatusDelay
      ? "chip chip-warning"
      : "chip chip-success"
    : "chip";

  return (
    <header className="top-header">
      <div>
        <p className="eyebrow">AutoMap: County GIS Request Engine</p>
        <h2>Map Composer</h2>
        <p className="header-subtitle">
          Describe the map you need. AutoMap drafts it, previews it, lets you adjust it, then exports a review report.
        </p>
      </div>
      <div className="header-actions">
        <span className="chip">FE {frontendLabel}</span>
        <span className={apiChipClass} title={apiInfo.apiBaseUrl}>
          API {apiLabel}
        </span>
        <span className="chip chip-success">Scope: Cabarrus County, NC</span>
        <span className={liveStatus.real_publish_enabled ? "chip chip-warning" : "chip chip-success"}>
          Real publish {liveStatus.real_publish_enabled ? "enabled" : "disabled"}
        </span>
      </div>
    </header>
  );
}
