"use client";

export function MapScaleBar() {
  return (
    <div className="map-scale-bar" aria-label="Map scale bar">
      <div className="map-scale-bar-rule" aria-hidden="true">
        <span />
        <span />
      </div>
      <div className="map-scale-bar-labels">
        <span>0</span>
        <span>approx.</span>
      </div>
    </div>
  );
}
