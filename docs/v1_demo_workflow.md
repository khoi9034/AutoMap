# AutoMap v1 Demo Workflow

AutoMap v1.0 is a local demo application for turning plain-English county GIS requests into draft map recipes, local review packets, and browser previews.

## Start The Local UI

```bash
python -m app.main --serve-ui --ui-port 8001
```

Open:

```text
http://127.0.0.1:8001
```

## Main Demo Prompt

```text
Show parcels in Concord that are in the 100-year floodplain.
```

Recommended sequence:

1. Open the home page.
2. Create a recipe from the prompt.
3. Generate a review packet.
4. Preview the map locally.
5. Create an adjustment template.
6. Apply the adjustment template.
7. Run dry-run publishing.
8. Review the generated receipt.

## CLI Demo

```bash
python -m app.main --run-demo-workflow
```

This command creates local ignored artifacts, applies the generated adjustment template, validates the adjusted packet, runs publisher dry-run mode, and prints a preview URL.

It does not publish anything to ArcGIS Online, Enterprise, or Portal.

## Demo Pages

- `/demo` lists approved sample prompts.
- `/status` shows sanitized system status.
- `/history` shows recent local request history.
- `/preview` opens the latest local map preview.

## Safety Notes

AutoMap does not ingest full geometries, does not require ArcGIS login, does not use an external LLM API, and does not create public prediction or publishing endpoints.
