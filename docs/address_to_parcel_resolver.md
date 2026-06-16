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

It does not use owner/name fields by default. If a user explicitly asks for owner search, AutoMap marks the request as privacy-sensitive and needs review.

Matching uses `returnGeometry=false` first. Geometry is fetched only after a safe single or small match count. AutoMap does not download countywide parcel, address, deed, permit, or planning datasets.

## Composer Behavior

If an address matches, AutoMap can focus the map on the address or related parcel and may add proximity outputs such as a straight-line draft to the nearest fire station.

If an address does not match, the composer shows `Address not matched` and blocks preview. It does not show a broad county map as a successful address-focused map.

CFS remains separate. AutoMap does not connect to `cfs_dev`.
