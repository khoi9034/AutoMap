# Simple Composer UX

AutoMap v3.5 keeps the normal map-making flow focused on four steps:

1. Request
2. Preview
3. Adjust
4. Print / Export

The composer hides internal recipe, WebMap, review-packet, approval, and publish terminology from the normal user flow. Those internal artifacts can still be created behind the scenes when needed, but the main interface behaves like a simple map tool.

## Clean Layout

The Map Composer page shows:

- one title and subtitle from the page header
- a prompt box with examples
- a four-step progress bar
- a map preview or a clear blocker
- selected layers and warnings
- adjustment controls only after preview is available
- print/export controls only after preview is available

The System Snapshot remains on System Status, not the normal composer.

## Blocked Preview UX

Blocked focused previews show one clear blocker:

- `Address not matched` for address origins
- `Parcel not matched` for parcel/PIN/PIN14 origins

AutoMap explains what it tried, shows candidate or unmatched records when available, and asks the user to try a corrected address/PIN.

## Proximity Drafts

Nearest-facility prompts route through the proximity workflow. Straight-line distance is supported as a draft reference. Road-network routing remains unavailable unless an approved routing/network service is added later.

AutoMap v3.6 renders proximity-derived GeoJSON directly in the composer preview. When an address and nearest facility are matched, the preview shows an origin marker, target marker, and straight-line distance line using the local files written under `outputs/proximity/`.

If an address is matched but no related parcel can be resolved from verified fields, the composer still previews the address and proximity line and warns that the parcel outline is not available. It does not show the full Tax Parcels layer as the selected property.

Nothing is published from the composer, no ArcGIS login is required, and CFS remains untouched.
