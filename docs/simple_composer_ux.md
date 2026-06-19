# Simple Composer UX

AutoMap v3.5 keeps the normal map-making flow focused on four steps:

1. Request
2. Preview
3. Adjust
4. Print / Export

The composer hides internal recipe, WebMap, review-packet, approval, and publish terminology from the normal user flow. Those internal artifacts can still be created behind the scenes when needed, but the main interface behaves like a simple map tool.

## Clean Layout

The Map Composer page uses a different layout for each step:

- Request: prompt box, examples, and Generate Draft Map
- Preview: large map, compact summary, selected layers, and warnings
- Adjust: map on the left with controls on the right
- Print / Export: print/exhibit preview and output actions

The System Snapshot remains on System Status, not the normal composer.

The full prompt panel belongs to Request. Preview, Adjust, and Print / Export only show a compact original-request summary so the map and task-specific controls have room to breathe.

AutoMap v4.4 removes the messy nested-scroll feel from desktop composer screens. Preview and Adjust use a viewport workbench with the map filling the left side. The map frame itself does not scroll; the right summary or control panel scrolls only when its content is taller than the available space. On smaller screens, the layout stacks and uses normal page scrolling.

## Blocked Preview UX

Blocked focused previews show one clear blocker:

- `Address not found` for unmatched address origins
- `Parcel not matched` for parcel/PIN/PIN14 origins

AutoMap explains what it tried, shows candidate or unmatched records when available, and asks the user to try a corrected address/PIN.

## Proximity Drafts

Nearest-facility prompts route through the proximity workflow. Straight-line distance is supported as a draft reference. Road-network routing remains unavailable unless an approved routing/network service is added later.

AutoMap v3.6 renders proximity-derived GeoJSON directly in the composer preview. When an address and nearest facility are matched, the preview shows an origin marker, target marker, and straight-line distance line using the local files written under `outputs/proximity/`.

If an address is matched but no related parcel can be resolved from verified fields, the composer still previews the address and proximity line and warns that the parcel outline is not available. It does not show the full Tax Parcels layer as the selected property.

Nothing is published from the composer, no ArcGIS login is required, and CFS remains untouched.
