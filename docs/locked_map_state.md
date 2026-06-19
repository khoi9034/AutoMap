# Locked Map State

AutoMap v4.9 makes map interaction step-specific.

Only the Adjust step is interactive. Reviewers can pan, zoom, reset the generated view, center on the origin or target, and then lock the final map for print/export.

The Preview step, Print / Export step, live print preview, and print/exhibit pages use locked map modes. Locked modes hide zoom controls, disable map navigation, and render an interaction blocker over the map canvas so the preview cannot drift accidentally.

## Captured State

When the reviewer applies adjustments or locks the final map, AutoMap captures:

- map extent
- map center
- zoom
- scale
- rotation
- visible/hidden layers
- layer opacity
- layer order
- title/subtitle
- route and symbol state
- notes and warnings

Print/export uses this saved state instead of regenerating the map from the original prompt.

## Map Frame Title

The concise map title and subtitle render directly inside the map frame. The page title remains `Map Composer`, while the map frame title describes the actual map, such as `Nearest Fire Station from 793 Bartram Ave`.

## Safety

Locked state is local draft state only. AutoMap does not publish ArcGIS items, does not require ArcGIS login, does not bulk-download datasets, and does not touch CFS or `cfs_dev`.
