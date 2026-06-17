# Address Proximity Preview

Address and nearest-facility requests are previewed as focused local result maps.

For a prompt such as:

`make a map of my address 793 bartram ave and include nearest line to the nearest fire station`

AutoMap treats the address as the origin. If the address is matched, the proximity workflow writes:

- `origin_point.geojson`
- `target_feature.geojson`
- `proximity_line.geojson`
- `proximity_result.json`
- proximity report files

The composer preview uses those derived outputs to show the origin marker, nearest facility marker, and straight-line distance line. The map extent is computed from the origin, target, and line with a buffer instead of falling back to a full county or service extent.

If the address is matched but a related parcel cannot be resolved from verified public fields, AutoMap still previews the address point and nearest-facility line. It also warns:

`Address matched, but related parcel was not resolved from verified fields.`

The selected parcel outline is shown only when a parcel is truly resolved and its geometry was fetched under safe match-count limits.

If the address is unmatched, the preview is blocked and AutoMap asks for a corrected address. It does not show a broad county map as a successful address-focused result.

Straight-line proximity is not a driving route. Road-network routing remains unavailable unless an approved routing or network service is added later.
