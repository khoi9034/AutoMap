# AutoMap Frontend UX Design

AutoMap v1.6 presents the product as a county GIS operations dashboard for internal draft map workflows.

## Design Direction

- Light, calm, government-friendly interface
- Blue, gray, and white palette with restrained success/warning states
- Compact cards and tables built for scanning
- Clear draft-only labels wherever publishing or previewing could be misread
- Workflow context visible from every page

## Workflow Guidance

Each workflow page should show:

- current step
- completed work
- blocked state, if any
- next action
- safety boundary for the page

The workflow stepper and right-side context panel are intentionally plain. They should help GIS staff recover context after refreshes and avoid guessing what to do next.

## State Handling

Frontend pages should handle:

- backend offline
- API timeout
- no packet selected
- no preview config
- invalid packet
- blocked publish readiness
- empty history, packet, and data gap states

Error states should explain what is missing without implying that AutoMap invented or lost data.

## Publishing Boundary

The frontend only exposes dry-run publish and dry-run portal smoke-test actions. Real publish remains CLI-only, requires explicit confirmation, and is outside the frontend UI.

The frontend must not show ArcGIS credentials, database URLs, `.env` values, or protected external-project references.

## Port Boundary

AutoMap uses:

- frontend: `http://localhost:3010`
- backend/API: `http://127.0.0.1:8010`

Cabarrus FutureScape keeps ports `3000` and `8000`. AutoMap must not bind to those ports.
