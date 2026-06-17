# Real Composer Map Preview

AutoMap v3.7 renders Map Composer proximity/address results with a real ArcGIS Maps SDK `MapView`.

The composer preview uses:

- a real ArcGIS basemap such as `streets-vector`
- verified ArcGIS REST context layers from the preview config
- local derived GeoJSON overlays served by AutoMap
- a focused extent based on origin, target, and straight-line output geometry

The previous schematic/grid preview is not used as a success state. If the ArcGIS map cannot load, the frontend shows `Map preview failed to load` instead of pretending a fake diagram is a real GIS map.

## Derived Overlays

Preview configs may include `derived_overlays`:

- `Origin Address`
- `Nearest Fire Station` or `Nearest Fire/EMS Station`
- `Straight-Line Distance`
- `Selected Parcel`, only when the related parcel is truly resolved

The frontend fetches the local GeoJSON from `/api/local-outputs/geojson/...` and converts it into ArcGIS graphics. This avoids CORS fragility with local GeoJSONLayer URLs while keeping the output local and review-only.

## Focus Extent

For proximity and address requests, AutoMap computes the preview extent from the local origin point, target point, and line geometry. It does not use the full Tax Parcels extent or countywide service extent for focused previews.

If the address is matched but the parcel is not resolved, the map still focuses on the address and nearest facility line. It also shows a warning that the parcel was not resolved.

## Safety

The composer preview does not publish, upload, or share local GeoJSON. It does not require ArcGIS login. CFS remains separate and untouched.
