# Simple Map Composer

AutoMap v3.4 makes `/map-composer` the primary local workflow for normal map requests.

The intended path is:

1. Request
2. Preview
3. Adjust
4. Print / Export

The composer runs request intelligence, builds the technical map artifacts, creates local preview files when preview is valid, and returns one clean response to the frontend. It does not run analysis by default, publish to ArcGIS, require ArcGIS login, or create public items.

## Simple Adjustments

Reviewers can adjust the map without editing YAML:

- map title
- layer visibility
- opacity
- draw order
- definition expression text
- reviewer notes

The older YAML adjustment workflow remains available under Advanced tools.

## Print / Export

The composer can generate local draft report/export links:

- review summary HTML
- review summary Markdown
- WebMap JSON
- layer list CSV
- browser print page

These are draft review outputs, not official print maps.

## Advanced Pages

The advanced pages remain available for recipe review, analysis, approval, dry-run publish checks, learning, catalog review, data gaps, external sources, history, and system status. Normal users should start with Map Composer.

## Safety

Map Composer does not publish, does not require ArcGIS credentials, does not bulk-ingest parcels, and does not use CFS ports or the CFS database.
