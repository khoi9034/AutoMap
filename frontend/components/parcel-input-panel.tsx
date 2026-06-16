"use client";

import { useState } from "react";

import { matchParcels, parseParcels } from "@/lib/api";
import type { ParcelParseResult, ParcelSet } from "@/types/automap";

type ParcelInputPanelProps = {
  onParsed: (result: ParcelParseResult) => void;
  onParcelSet: (parcelSet: ParcelSet) => void;
  onError: (message: string) => void;
};

const SAMPLE_INPUTS = [
  "5528-12-3456, 5528-12-7890",
  "PIN14: 55281234567890",
  "65 Church St S",
  "Make a map of parcel 5528-12-3456 and show zoning, floodplain, schools, and roads.",
];

export function ParcelInputPanel({ onParsed, onParcelSet, onError }: ParcelInputPanelProps) {
  const [rawInput, setRawInput] = useState(SAMPLE_INPUTS[0]);
  const [loading, setLoading] = useState<string | null>(null);

  async function runParse() {
    setLoading("parse");
    try {
      onParsed(await parseParcels(rawInput));
    } catch (exc) {
      onError(exc instanceof Error ? exc.message : "Parcel parsing failed.");
    } finally {
      setLoading(null);
    }
  }

  async function runCreateSet() {
    setLoading("set");
    try {
      const response = await matchParcels(rawInput);
      onParcelSet(response.parcel_set);
      onParsed({
        raw_input: rawInput,
        input_type: response.parcel_set.input_type,
        parsed_identifiers: response.parcel_set.parsed_identifiers,
      });
    } catch (exc) {
      onError(exc instanceof Error ? exc.message : "Parcel set creation failed.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <section className="panel prompt-box">
      <div className="panel-title-row">
        <div>
          <h3>Parcel input</h3>
          <p className="muted">Paste parcel IDs, PIN/PIN14 values, addresses, or a small parcel list.</p>
        </div>
      </div>
      <textarea
        value={rawInput}
        onChange={(event) => setRawInput(event.target.value)}
        rows={7}
        placeholder="PINs, parcel IDs, addresses, or a parcel-centered prompt"
      />
      <div className="sample-grid">
        {SAMPLE_INPUTS.map((sample) => (
          <button className="sample-button" type="button" key={sample} onClick={() => setRawInput(sample)}>
            {sample}
          </button>
        ))}
      </div>
      <div className="button-row">
        <button className="button" type="button" onClick={runParse} disabled={loading !== null || !rawInput.trim()}>
          {loading === "parse" ? "Parsing..." : "Parse Identifiers"}
        </button>
        <button className="button button-secondary" type="button" onClick={runCreateSet} disabled={loading !== null || !rawInput.trim()}>
          {loading === "set" ? "Matching..." : "Match Parcels"}
        </button>
      </div>
    </section>
  );
}
