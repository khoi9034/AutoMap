# Map Composer Step Layouts

AutoMap v4.3 gives each normal Map Composer step its own layout instead of keeping one large prompt/debug-style panel on screen for the entire workflow. AutoMap v4.4 refines those layouts into a fixed enterprise workbench so the map stays visible and scroll behavior is predictable. AutoMap v4.9 adds step-specific map interaction modes.

## Request

The Request step is for the prompt:

- large prompt input
- sample prompts
- Generate Draft Map
- short explanation of what AutoMap will do

It does not show adjustment or export controls.

## Preview

The Preview step is for reviewing the generated map:

- large map preview
- compact original-request summary
- selected layers
- warnings and source notes
- route/distance summary when relevant
- Continue to Adjust, Regenerate Draft, and Print / Export actions

The full prompt panel is not shown in this step. On desktop, the map column fills the available height and the summary panel scrolls only if needed.

Preview maps are locked and read-only. Users can inspect the draft result without accidentally panning or zooming away from the generated view.

## Adjust

The Adjust step is an enterprise side-by-side workbench:

- map preview on the left
- adjustment controls on the right

Controls include title, subtitle, layer visibility, opacity, order, display name, optional definition expression, route visibility/style, origin/target symbol visibility, reviewer notes, view reset buttons, Apply Adjustments, Lock Final Map, and Reset adjustments.

The prompt appears only as a compact original-request note so reviewers can keep their eyes on the map while tuning it. On desktop, the map does not scroll internally; only the controls panel scrolls when the control list is taller than the viewport.

Adjust is the only step where the map can pan or zoom. Applying adjustments or locking the final map captures the current extent, center, zoom, and scale for print/export.

## Print / Export

The Print / Export step focuses on local outputs:

- print/exhibit preview
- Open Print Layout
- Generate Exhibit Package
- Generate Review Report
- Export WebMap JSON
- Export Layer Source CSV
- Export Warning Summary

Outputs are local draft files only. AutoMap does not publish ArcGIS items, does not require ArcGIS login, and keeps generated folders ignored by Git.

Print / Export maps are locked and read-only. The preview document can scroll, but the map inside the document cannot move.

## Safety

Preview, Adjust, and Print / Export remain disabled until a draft exists and the preview is ready. Blocked address or parcel requests show a blocker and ask for a corrected address/PIN instead of showing a broad county map as a successful focused preview.

CFS remains separate and `cfs_dev` is not touched.
