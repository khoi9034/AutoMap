# Map Composer Step Layouts

AutoMap v4.3 gives each normal Map Composer step its own layout instead of keeping one large prompt/debug-style panel on screen for the entire workflow.

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

The full prompt panel is not shown in this step.

## Adjust

The Adjust step is side-by-side:

- map preview on the left
- adjustment controls on the right

Controls include title, subtitle, layer visibility, opacity, order, display name, optional definition expression, route visibility/style, origin/target symbol visibility, reviewer notes, Apply Adjustments, and Reset adjustments.

The prompt appears only as a compact original-request note so reviewers can keep their eyes on the map while tuning it.

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

## Safety

Preview, Adjust, and Print / Export remain disabled until a draft exists and the preview is ready. Blocked address or parcel requests show a blocker and ask for a corrected address/PIN instead of showing a broad county map as a successful focused preview.

CFS remains separate and `cfs_dev` is not touched.
