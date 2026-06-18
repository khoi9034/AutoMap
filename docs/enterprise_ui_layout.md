# Enterprise UI Layout

AutoMap v4.4 refines the Map Composer into a fixed GIS workbench instead of a stack of independently scrolling web panels.

## Desktop Scroll Model

The normal desktop composer uses one predictable shell:

- the app shell fills the viewport
- the sidebar stays fixed within the viewport
- the top header stays at the top of the main column
- the active composer step fills the remaining space
- the map canvas does not scroll internally
- the right-side panel scrolls only when controls exceed the available height

This keeps the map visible while a reviewer adjusts title, layer visibility, opacity, layer order, route style, symbol visibility, and notes.

## Step Layouts

Request can use normal page scrolling because it is a prompt entry screen.

Preview uses a map-dominant two-column layout. The map fills the left side and compact summary, warnings, and layer notes sit on the right.

Adjust uses a side-by-side workbench. The map remains fixed on the left while the controls panel scrolls on the right.

Print / Export focuses on output actions and may scroll when output links are long.

## Normal UI

Normal Map Composer screens hide debug-style JSON and internal workflow terms by default. Advanced recipe, packet, approval, and publish tooling remains outside the normal composer.

## Safety

The layout change does not alter data access or publishing behavior. AutoMap does not publish ArcGIS items, does not require ArcGIS login, does not bulk-ingest datasets, and does not connect to CFS or `cfs_dev`.
