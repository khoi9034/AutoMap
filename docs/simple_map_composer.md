# Simple Map Composer

AutoMap v3.4 makes `/map-composer` the primary local workflow for normal map requests.

The intended path is:

1. Request
2. Preview
3. Adjust
4. Print / Export

The composer runs request intelligence, builds the technical map artifacts, creates local preview files when preview is valid, and returns one clean response to the frontend. It does not run analysis by default, publish to ArcGIS, require ArcGIS login, or create public items.

AutoMap v4.3 makes those steps layout-specific. The prompt and examples live in Request, the generated map dominates Preview, Adjust uses a side-by-side map/control workspace, and Print / Export focuses on local output actions.

AutoMap v4.4 refines the desktop composer into a fixed workbench: the app shell fills the viewport, the map canvas stays visible, and the right-side control panel is the only composer area that scrolls when controls exceed the available height.

AutoMap v4.5 saves the exact composer map state before print/export. The saved state includes title, subtitle, extent, basemap, visible/hidden layers, opacity, order, route styling, symbols, legend, scale bar, north arrow, warnings, and reviewer notes.

## Simple Adjustments

Reviewers can adjust the map without editing YAML:

- map title
- subtitle
- layer visibility
- opacity
- draw order
- display name
- route style and symbol visibility where relevant
- definition expression text
- reviewer notes

The Adjust step keeps the map on the left and controls on the right so reviewers can see changes while tuning the draft. On desktop, the page itself should not jump while the controls panel scrolls.

The older YAML adjustment workflow remains available under Advanced tools.

## Print / Export

The composer can generate local draft exhibit/export links:

- print-oriented staff report layout
- local exhibit package
- WebMap JSON
- layer source CSV
- warning summary JSON

These are draft review outputs, not official print maps. Exhibit packages are written under ignored `outputs/exhibits/` folders and include HTML, JSON, CSV, warning, and manifest files.

The Print / Export step also lets reviewers choose report sections such as map summary, selected layer table, source notes, warnings, proximity summary, parcel summary, and safe statistics. Permit/planning/development statistics remain marked unavailable when verified bounded data is not present.

## Internal Workflow Tools

Normal users should start with Map Composer. Legacy internal routes such as `/recipe-review`, `/map-preview`, `/adjustments`, `/approval`, and `/publish-center` redirect to `/map-composer` by default so the normal app does not expose the old 10-step workflow.

Support pages for catalog review, data gaps, external sources, history, and system status remain visible in the sidebar. Deeper internal recipe, approval, and dry-run tooling can be reintroduced later behind an explicit advanced mode.

## Safety

Map Composer does not publish, does not require ArcGIS credentials, does not bulk-ingest parcels, and does not use CFS ports or the CFS database.
