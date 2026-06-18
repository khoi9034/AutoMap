# Table Request Engine

AutoMap v4.6 adds a bounded table/data request workflow alongside map generation. Prompts that ask for a table, list, CSV, spreadsheet, export, records, attribute table, fields, columns, parcel list, permit list, or historical records are classified as table requests.

Table recipes use verified `automap.layer_catalog` metadata and field profiles. AutoMap does not invent layers or fields, and table workflows default to `returnGeometry=false`.

## Table Recipe

A table recipe includes:

- table title and intent
- verified source layers
- selected fields
- geography and time filters
- historical year when requested
- estimated row count
- safety status
- missing data and warnings
- preview rows
- export readiness and blocked reasons

## Safety Rules

AutoMap plans tables count-first and bounded:

- preview rows are capped at 100
- exports are allowed up to 2,000 estimated rows
- exports above 5,000 estimated rows are blocked
- selected fields are capped at 50
- geometry is excluded unless a future explicit geometry workflow is reviewed

If a request is too broad, AutoMap recommends refinements such as smaller geography, a specific year, a specific layer/type, or selected parcels only.

## Historical Data

Historical table prompts such as `Show historical permits from 2014` can use verified legacy/historical layers when available. Current permit requests do not use historical layers as a substitute for unresolved official current permit data.

## Current Permit Gap

The `current_permits` gap remains unresolved unless an official verified current permit source exists. AutoMap will not fabricate current permit tables from proxy, plan review, or legacy sources.

## CFS Boundary

Table requests use AutoMap's own `automap` database schema only. They do not connect to `cfs_dev`, do not touch the CFS repository, and do not publish ArcGIS items.
