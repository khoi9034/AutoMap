"use client";

import { useEffect, useMemo, useState } from "react";

import { listPackets } from "@/lib/api";
import type { PacketSummary, PacketsResponse } from "@/types/automap";

type PacketPickerProps = {
  label: string;
  packetType: "review" | "adjusted" | "approved";
  value?: string;
  onSelect: (packet: PacketSummary) => void;
};

function packetsForType(response: PacketsResponse | null, packetType: PacketPickerProps["packetType"]): PacketSummary[] {
  if (packetType === "review") {
    return response?.review_packets || [];
  }
  if (packetType === "adjusted") {
    return response?.adjusted_packets || [];
  }
  return response?.approved_packets || [];
}

export function PacketPicker({ label, packetType, value, onSelect }: PacketPickerProps) {
  const [packets, setPackets] = useState<PacketsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listPackets()
      .then((response) => {
        setPackets(response);
        const options = packetsForType(response, packetType);
        if (!value && options[0]) {
          onSelect(options[0]);
        }
      })
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Packet list failed."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [packetType]);

  const options = useMemo(() => packetsForType(packets, packetType), [packets, packetType]);

  return (
    <div className="form-grid">
      <label>
        <strong>{label}</strong>
        <select
          className="select-input"
          value={value || ""}
          onChange={(event) => {
            const packet = options.find((item) => item.packet_path === event.target.value);
            if (packet) {
              onSelect(packet);
            }
          }}
        >
          {!options.length ? <option value="">No {packetType} packets found</option> : null}
          {options.map((packet) => (
            <option key={packet.packet_path || packet.packet_id} value={packet.packet_path}>
              {packet.map_title || packet.packet_id}
            </option>
          ))}
        </select>
      </label>
      {error ? <p className="error-text">{error}</p> : null}
    </div>
  );
}
