"use client";

const sampleTablePrompts = [
  "Give me a table of parcels in Concord.",
  "Export parcels in the 100-year floodplain.",
  "Give planning a parcel list with zoning, flood, and school district context.",
  "Show historical permits from 2014.",
  "Create a table of 2014 parcels and zoning.",
  "Give me an attribute table, not a map.",
];

type Props = {
  prompt: string;
  setPrompt: (value: string) => void;
  loading?: boolean;
  onPlan: () => void;
};

export function TableRequestPanel({ prompt, setPrompt, loading, onPlan }: Props) {
  return (
    <section className="panel">
      <p className="eyebrow">Table Center</p>
      <h3>Plan a bounded table export</h3>
      <p className="muted">AutoMap uses verified catalog layers, returnGeometry=false previews, and count-first safety limits.</p>
      <textarea className="large-prompt-input" value={prompt} onChange={(event) => setPrompt(event.target.value)} />
      <div className="button-row">
        <button className="button" type="button" onClick={onPlan} disabled={loading}>
          {loading ? "Planning..." : "Plan Table"}
        </button>
      </div>
      <div className="sample-grid">
        {sampleTablePrompts.map((sample) => (
          <button className="sample-button" key={sample} type="button" onClick={() => setPrompt(sample)}>
            {sample}
          </button>
        ))}
      </div>
    </section>
  );
}
