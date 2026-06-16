type ParcelNearbyControlsProps = {
  nearbyDistance: string;
  onDistanceChange: (distance: string) => void;
};

const DISTANCE_PRESETS = ["500 feet", "0.25 miles", "0.5 miles", "1 mile"];

export function ParcelNearbyControls({ nearbyDistance, onDistanceChange }: ParcelNearbyControlsProps) {
  return (
    <section className="panel">
      <h3>Nearby context</h3>
      <p className="muted">Use a reviewed distance before querying nearby roads, AADT, STIP, or activity context.</p>
      <div className="button-row">
        {DISTANCE_PRESETS.map((distance) => (
          <button className="small-button" type="button" key={distance} onClick={() => onDistanceChange(distance)}>
            {distance}
          </button>
        ))}
      </div>
      <label className="field-label" htmlFor="parcel-nearby-distance">
        Reviewed nearby distance
      </label>
      <input
        id="parcel-nearby-distance"
        value={nearbyDistance}
        onChange={(event) => onDistanceChange(event.target.value)}
        placeholder="0.25 miles"
      />
    </section>
  );
}
