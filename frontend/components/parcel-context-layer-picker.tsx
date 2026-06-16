"use client";

type ParcelContextLayerPickerProps = {
  selectedTopics: string[];
  onChange: (topics: string[]) => void;
};

const OVERLAY_OPTIONS = [
  { key: "zoning", label: "Zoning" },
  { key: "flood", label: "Flood" },
  { key: "schools", label: "Schools" },
  { key: "transportation", label: "Roads" },
  { key: "traffic", label: "AADT" },
  { key: "transportation_projects", label: "STIP" },
  { key: "development", label: "planning/development proxy" },
  { key: "addresses", label: "Addresses" },
];

export function ParcelContextLayerPicker({
  selectedTopics,
  onChange,
}: ParcelContextLayerPickerProps) {
  function toggleTopic(topic: string) {
    if (selectedTopics.includes(topic)) {
      onChange(selectedTopics.filter((item) => item !== topic));
    } else {
      onChange([...selectedTopics, topic]);
    }
  }

  return (
    <section className="panel">
      <h3>Context overlays</h3>
      <p className="muted">Choose review layers to add around the parcel set. Proxy layers stay labeled as proxy/context.</p>
      <div className="checkbox-grid">
        {OVERLAY_OPTIONS.map((option) => (
          <label key={option.key}>
            <input
              type="checkbox"
              checked={selectedTopics.includes(option.key)}
              onChange={() => toggleTopic(option.key)}
            />
            {option.label}
          </label>
        ))}
      </div>
    </section>
  );
}
