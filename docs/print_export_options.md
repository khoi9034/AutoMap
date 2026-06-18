# Print Export Options

AutoMap print/export options are stored with the locked composer map state.

## Export Modes

- `map_exhibit_only`: Map only. This is the default map exhibit mode.
- `map_plus_summary`: Map + summary. Adds concise findings below the map.
- `full_report`: Full report. Turns on common appendix sections by default.

## Section Options

Supported options include:

- map summary
- key findings
- proximity / distance summary
- parcel summary
- statistics
- layer source table
- warnings and limitations
- source notes
- permit summary
- planning summary
- development proxy summary
- appendix
- draft disclaimer

Users can toggle these sections before printing. The live preview updates immediately, and selected options are sent to the backend when saving map state or generating an exhibit package.

Unavailable permit, planning, or development sections must say unavailable with a reason. AutoMap does not invent missing statistics.

## Export Manifest

Local exhibit packages record:

- `exportMode`
- `includedSections`
- `lockedMapStateUsed`
- `generatedAt`

These fields make it clear which print options were used and whether the final saved composer state drove the export.
