# Address-to-Parcel Resolver

AutoMap v3.5 treats address prompts as user-supplied map origins, not as parcel IDs.

Examples parsed as address origins:

- `address 793 bartram ave`
- `my address 793 bartram ave`
- `my home 793 bartram ave`
- `793 bartram ave`

Examples parsed as parcel/PIN origins:

- `parcel 5528-12-3456`
- `PIN 5528-12-3456`
- `PIN14 55281234567890`

## Resolution Rules

The resolver uses verified public catalog fields only:

- verified Addresses layer fields
- verified Tax Parcels address/PIN/PIN14/parcel fields
- verified public crosswalk fields if they are already in the AutoMap catalog
- bounded address-point spatial lookup against Tax Parcels after an address point is matched

It does not use owner/name fields by default. If a user explicitly asks for owner search, AutoMap marks the request as privacy-sensitive and needs review.

Matching uses `returnGeometry=false` first. Geometry is fetched only after a safe single or small match count. AutoMap does not download countywide parcel, address, deed, permit, or planning datasets.

Address matching is progressive. AutoMap first tries exact normalized address variants such as `ave` and `avenue`, then house number plus street core, then bounded full-address and street-only candidate searches. If the address remains ambiguous, candidates are returned for reviewer selection instead of guessing.

If address fields do not expose a parcel/PIN relationship, AutoMap can safely test whether the matched address point intersects exactly one parcel. It runs a count-only parcel query first. If the count is exactly one, it fetches only that parcel geometry and may render `Selected Parcel`. If the count is zero, the property remains `not_resolved`. If the count is greater than one, the property match is `ambiguous` and candidates are returned for review.

## Composer Behavior

If an address matches, AutoMap can focus the map on the address or related parcel and may add proximity outputs such as a straight-line draft to the nearest fire station.

If an address matches but no related parcel is resolved, the composer can still preview the address point, nearest facility point, and straight-line distance. It must not show the full Tax Parcels layer as the selected property.

If an address does not match, the composer shows `Address not found` guidance and blocks preview. It asks for city, ZIP, or a directional suffix such as `SW`. It does not show a broad county map as a successful address-focused map.

CFS remains separate. AutoMap does not connect to `cfs_dev`.
