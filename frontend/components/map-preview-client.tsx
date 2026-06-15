"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ArcGISMapPreview } from "@/components/arcgis-map-preview";
import { StatusChip } from "@/components/status-chip";
import { getPackets } from "@/lib/api";
import {
  loadWorkflowState,
  mergeWorkflowState,
  packetIdFromPath,
  primaryAdjustedPacketPath,
  primaryApprovedPacketPath,
  primaryReviewPacketPath,
} from "@/lib/workflow-store";
import type { PacketSummary, PacketsResponse } from "@/types/automap";

function packetLabel(packet: PacketSummary): string {
  const title = packet.map_title || packet.packet_id || "Untitled packet";
  const type = packet.packet_type ? ` (${packet.packet_type})` : "";
  return `${title}${type}`;
}

export function MapPreviewClient() {
  const [packets, setPackets] = useState<PacketsResponse | null>(null);
  const [selectedPacketId, setSelectedPacketId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const packetOptions = useMemo(
    () => [
      ...(packets?.approved_packets || []),
      ...(packets?.adjusted_packets || []),
      ...(packets?.review_packets || []),
    ],
    [packets],
  );

  useEffect(() => {
    setLoading(true);
    getPackets()
      .then((response) => {
        setPackets(response);
        const workflow = loadWorkflowState();
        const activePath =
          primaryApprovedPacketPath(workflow) ||
          primaryAdjustedPacketPath(workflow) ||
          primaryReviewPacketPath(workflow) ||
          window.localStorage.getItem("automap:lastPacketPath") ||
          "";
        const activeId =
          workflow.selectedApprovedPacketId ||
          workflow.selectedAdjustedPacketId ||
          workflow.selectedPacketId ||
          packetIdFromPath(activePath);
        setSelectedPacketId(activeId || response.latest?.packet_id || "");
      })
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Packet index failed."))
      .finally(() => setLoading(false));
  }, []);

  function onSelect(packetId: string) {
    const packet = packetOptions.find((item) => item.packet_id === packetId);
    setSelectedPacketId(packetId);
    if (packet?.packet_type === "approved") {
      mergeWorkflowState({
        selectedApprovedPacketId: packetId,
        selectedApprovedPacketPath: packet.packet_path || "",
        activeStep: "preview",
      });
    } else if (packet?.packet_type === "adjusted") {
      mergeWorkflowState({
        selectedAdjustedPacketId: packetId,
        selectedAdjustedPacketPath: packet.packet_path || "",
        activeStep: "preview",
      });
    } else {
      mergeWorkflowState({
        selectedPacketId: packetId,
        selectedPacketPath: packet?.packet_path || "",
        activeStep: "preview",
      });
    }
  }

  return (
    <div className="page-stack">
      <section className="notice notice-warning">
        <strong>Draft-only preview</strong>
        <p>No ArcGIS item is created, no ArcGIS login is required, and no layers are published from this page.</p>
      </section>

      <section className="panel form-grid">
        <div className="panel-title-row">
          <div>
            <h3>Preview source</h3>
            <p className="muted">Use an existing review, adjusted, or approved packet from the local packet index.</p>
          </div>
          <div className="chip-row">
            <StatusChip tone="success">Local only</StatusChip>
            <StatusChip tone="success">No ArcGIS login</StatusChip>
          </div>
        </div>
        <label htmlFor="packet-select">
          <strong>Selected packet</strong>
        </label>
        <select
          className="select-input"
          id="packet-select"
          value={selectedPacketId}
          onChange={(event) => onSelect(event.target.value)}
          disabled={loading || !packetOptions.length}
        >
          {packetOptions.map((packet) => (
            <option key={packet.packet_id} value={packet.packet_id}>
              {packetLabel(packet)}
            </option>
          ))}
          {!packetOptions.length ? <option value="">No local packets found</option> : null}
        </select>
        <div className="button-row">
          <Link className="button button-secondary" href="/recipe-review">
            Generate Review Packet
          </Link>
          <Link className="button button-secondary" href="/adjustments">
            Go to Adjustments
          </Link>
          {loadWorkflowState().selectedAdjustedPacketId || loadWorkflowState().adjustedPacket ? (
            <Link className="button button-secondary" href="/approval">
              Go to Approval
            </Link>
          ) : null}
        </div>
        {loading ? <p className="muted">Loading packet index...</p> : null}
        {error ? (
          <div className="inline-error" role="alert">
            <strong>Backend unavailable</strong>
            <p>{error}</p>
          </div>
        ) : null}
      </section>

      {selectedPacketId ? (
        <ArcGISMapPreview packetId={selectedPacketId} />
      ) : (
        <section className="panel empty-state">
          <h3>No preview packet selected</h3>
          <p>Create a review packet from the Recipe Review page, then return here to inspect the draft map.</p>
          <Link className="button" href="/recipe-review">
            Open Recipe Review
          </Link>
        </section>
      )}
    </div>
  );
}
