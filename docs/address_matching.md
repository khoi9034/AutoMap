# Address Matching

AutoMap treats street-address prompts as address origins, not parcel IDs.

Live address and parcel workflows currently support Cabarrus County, NC only. AutoMap does not perform nationwide
geocoding and does not use paid external geocoders. Recruiter/demo users should try a Cabarrus County address,
parcel/PIN, or county planning request.

For an input such as `793 bartram ave`, AutoMap normalizes casing, punctuation, repeated spaces, street suffixes, and directional text. It generates safe variants such as `793 bartram ave` and `793 bartram avenue`, parses the house number and street core, and then queries only verified public address or parcel-address fields.

## Progressive Matching

Address matching is bounded and count-first:

1. Exact normalized full-address variants against verified full/site/situs address fields.
2. House number plus street-name/core fields when the address layer exposes split fields.
3. Full-address `contains` matching for the house number and street core.
4. Street-only candidate fallback, capped to a small candidate list.
5. Verified Tax Parcels address/site/situs fields if the Addresses layer does not match.

AutoMap uses `returnGeometry=false` for counts and candidate rows. Geometry is fetched only after a strong single match is found.

If multiple records match, AutoMap returns candidates and waits for reviewer selection. If no candidates are found, it
shows `Address not found in Cabarrus County records` and reminds the user that live address lookup is limited to
Cabarrus County, NC. Obvious out-of-county address inputs return `unsupported_area` without querying parcel geometry.

## Privacy And Safety

Owner/name fields are not searched by default. If a prompt includes owner language, AutoMap strips it from address matching and treats any owner search as a separate review-sensitive request.

AutoMap does not bulk-ingest or download countywide address or parcel datasets. CFS remains untouched, and AutoMap does not connect to `cfs_dev`.
