"use client";

import { useState } from "react";

import { StatusChip } from "@/components/status-chip";

const TARGET_OPTIONS = [
  { value: "nearest_school", label: "Nearest school" },
  { value: "nearest_elementary_school", label: "Nearest elementary school" },
  { value: "nearest_middle_school", label: "Nearest middle school" },
  { value: "nearest_high_school", label: "Nearest high school" },
  { value: "nearest_fire_station", label: "Nearest fire station" },
  { value: "containing_fire_district", label: "Containing fire district" },
  { value: "nearest_library", label: "Nearest library" },
  { value: "nearest_county_facility", label: "Nearest county facility" },
  { value: "nearest_polling_place", label: "Nearest polling place" },
  { value: "route_to_address", label: "Route draft to address" },
];

type ProximityFormProps = {
  loading?: boolean;
  onNearest: (originInput: string, targetType: string) => void;
  onRouteDraft: (originInput: string, destinationInput: string) => void;
  onPrompt: (prompt: string) => void;
};

export function ProximityForm({ loading, onNearest, onRouteDraft, onPrompt }: ProximityFormProps) {
  const [originInput, setOriginInput] = useState("parcel 5528-12-3456");
  const [destinationInput, setDestinationInput] = useState("123 Main St");
  const [targetType, setTargetType] = useState("nearest_school");
  const [prompt, setPrompt] = useState("How far is parcel 5528-12-3456 from the nearest school?");

  const isRoute = targetType === "route_to_address";

  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Proximity request</h3>
          <p className="muted">Use a parcel/PIN/address origin and a verified catalog destination layer.</p>
        </div>
        <StatusChip tone="warning">Straight-line only</StatusChip>
      </div>
      <label className="form-label">
        Origin parcel, PIN, or address
        <input className="text-input" value={originInput} onChange={(event) => setOriginInput(event.target.value)} />
      </label>
      <label className="form-label">
        Target
        <select className="text-input" value={targetType} onChange={(event) => setTargetType(event.target.value)}>
          {TARGET_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      {isRoute ? (
        <label className="form-label">
          Destination address
          <input className="text-input" value={destinationInput} onChange={(event) => setDestinationInput(event.target.value)} />
        </label>
      ) : null}
      <div className="button-row">
        <button
          className="button"
          type="button"
          disabled={loading}
          onClick={() => (isRoute ? onRouteDraft(originInput, destinationInput) : onNearest(originInput, targetType))}
        >
          {loading ? "Running..." : isRoute ? "Create Route Draft" : "Find Nearest"}
        </button>
      </div>
      <label className="form-label">
        Or run a prompt
        <textarea className="textarea" value={prompt} onChange={(event) => setPrompt(event.target.value)} />
      </label>
      <button className="button button-secondary" type="button" disabled={loading} onClick={() => onPrompt(prompt)}>
        Run Proximity Prompt
      </button>
    </section>
  );
}
