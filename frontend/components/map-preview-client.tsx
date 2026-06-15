"use client";

import { useEffect, useMemo, useState } from "react";

import { API_BASE_URL, getPackets, getPreviewConfig } from "@/lib/api";
import type { PacketsResponse, PreviewConfig } from "@/types/automap";

export function MapPreviewClient() {
  const [packets, setPackets] = useState<PacketsResponse | null>(null);
  const [selectedPacketId, setSelectedPacketId] = useState("latest");
  const [preview, setPreview] = useState<PreviewConfig | null>(null);
  const [error, setError] = useState<string | null>(null);

  const packetOptions = useMemo(
    () => [
      ...(packets?.approved_packets || []),
      ...(packets?.adjusted_packets || []),
      ...(packets?.review_packets || []),
    ],
    [packets],
  );

  useEffect(() => {
    getPackets()
      .then((response) => {
        setPackets(response);
        setSelectedPacketId(response.latest?.packet_id || "latest");
      })
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Packet index failed."));
  }, []);

  useEffect(() => {
    if (!selectedPacketId) {
      return;
    }
    getPreviewConfig(selectedPacketId)
      .then(setPreview)
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Preview config failed."));
  }, [selectedPacketId]);

  const previewUrl = `${API_BASE_URL}/preview/${encodeURIComponent(selectedPacketId || "latest")}`;

  return (
    <div className="page-stack">
      <section className="panel form-grid">
        <label htmlFor="packet-select">
          <strong>Selected packet</strong>
        </label>
        <select
          className="select-input"
          id="packet-select"
          value={selectedPacketId}
          onChange={(event) => setSelectedPacketId(event.target.value)}
        >
          {packetOptions.map((packet) => (
            <option key={packet.packet_id} value={packet.packet_id}>
              {packet.map_title || packet.packet_id}
            </option>
          ))}
          {!packetOptions.length ? <option value="latest">Latest packet</option> : null}
        </select>
        <p className="muted">Draft-only preview. This iframe uses the existing backend preview page and does not publish.</p>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="panel">
        <iframe className="preview-frame" title="AutoMap draft preview" src={previewUrl} />
      </section>

      <section className="panel">
        <h3>Selected layers</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Layer</th>
                <th>Role</th>
                <th>Visibility</th>
                <th>Opacity</th>
                <th>Definition</th>
              </tr>
            </thead>
            <tbody>
              {(preview?.operational_layers || []).map((layer) => (
                <tr key={layer.id || layer.title}>
                  <td>{layer.title}</td>
                  <td>{layer.role}</td>
                  <td>{String(layer.visibility)}</td>
                  <td>{layer.opacity}</td>
                  <td>{layer.definition_expression || "None"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
