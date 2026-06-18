import json
from pathlib import Path

import pytest

from app import exhibit_exporter
from app.exhibit_exporter import (
    build_layer_source_rows,
    generate_exhibit_package_from_session,
    get_exhibit,
    list_exhibits,
)
from app.exhibit_models import REQUIRED_EXHIBIT_FILES


def sample_composer_session() -> dict:
    return {
        "composer_session_id": "composer_test_123",
        "raw_prompt": "make a map of my address 793 bartram ave and include nearest line to the nearest fire station",
        "request_type": "proximity",
        "map_title": "Nearest Fire Station from 793 Bartram Ave",
        "can_preview": True,
        "can_report": True,
        "created_at": "2026-06-18T10:00:00Z",
        "map_layout": {
            "title": "Nearest Fire Station from 793 Bartram Ave",
            "subtitle": "Road-following draft route.",
            "route_mode_label": "Road-following draft route",
            "legend_items": [{"label": "Origin Address"}, {"label": "Nearest Fire Station"}],
            "print_ready": True,
        },
        "preview_config": {
            "derived_overlays": [
                {
                    "id": "origin_address",
                    "title": "Origin Address",
                    "role": "origin",
                    "path": "outputs/proximity/test/origin_point.geojson",
                },
                {
                    "id": "nearest_fire_station",
                    "title": "Nearest Fire Station",
                    "role": "target",
                    "path": "outputs/proximity/test/target_feature.geojson",
                },
                {
                    "id": "route_line",
                    "title": "Road-following Draft Route",
                    "role": "route",
                    "route_warning": "Not official driving navigation.",
                    "path": "outputs/proximity/test/route_line.geojson",
                },
            ],
            "context_layers": [
                {
                    "layer_key": "roads",
                    "title": "Roads Context",
                    "role": "context",
                    "source_status": "active",
                    "layer_url": "https://example.test/roads/0",
                    "review_warnings": ["Reference roads only."],
                }
            ],
        },
        "composer_map_state": {
            "composer_session_id": "composer_test_123",
            "map_title": "Nearest Fire Station from 793 Bartram Ave",
            "map_subtitle": "Road-following draft route.",
            "raw_prompt": "make a map of my address 793 bartram ave and include nearest line to the nearest fire station",
            "request_type": "proximity",
            "preview_config": {
                "map_layout": {
                    "title": "Nearest Fire Station from 793 Bartram Ave",
                    "subtitle": "Road-following draft route.",
                    "legend_items": [{"label": "Origin Address"}, {"label": "Nearest Fire Station"}],
                },
                "derived_overlays": [
                    {"id": "origin_address", "title": "Origin Address", "role": "origin", "path": "outputs/proximity/test/origin_point.geojson"},
                    {"id": "nearest_fire_station", "title": "Nearest Fire Station", "role": "target", "path": "outputs/proximity/test/target_feature.geojson"},
                ],
                "context_layers": [
                    {
                        "layer_key": "roads",
                        "title": "Roads Context",
                        "role": "context",
                        "source_status": "active",
                        "layer_url": "https://example.test/roads/0",
                    }
                ],
            },
            "visible_layers": [{"layer_key": "roads", "title": "Roads Context", "source_status": "active"}],
            "hidden_layers": [],
            "derived_overlays": [
                {"id": "origin_address", "title": "Origin Address", "role": "origin", "local_output": True},
                {"id": "nearest_fire_station", "title": "Nearest Fire Station", "role": "target", "local_output": True},
            ],
            "warnings": ["Related parcel was not resolved from verified fields."],
            "proximity_summary": {
                "distance_value": 1.22,
                "distance_unit": "miles",
                "route_label": "Road-following draft route",
                "route_warning": "Not official driving navigation.",
                "target_name": "ALLEN FS",
                "property_match_status": "not_resolved",
            },
            "report_section_config": {"include_statistics": True, "include_layer_table": True},
        },
        "proximity_result": {
            "status": "ok",
            "origin_input": "793 bartram ave",
            "target_type": "nearest_fire_station",
            "target_name": "ALLEN FS",
            "distance_value": 1.22,
            "distance_unit": "miles",
            "route_label": "Road-following draft route",
            "route_warning": "Not official driving navigation.",
            "property_match_status": "not_resolved",
        },
        "warnings": ["Related parcel was not resolved from verified fields."],
        "missing_data": [],
    }


def all_text(folder: Path) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in folder.glob("*") if path.is_file())


def test_exhibit_package_creates_required_files(monkeypatch, tmp_path):
    monkeypatch.setattr(exhibit_exporter, "OUTPUTS_ROOT", tmp_path)

    package = generate_exhibit_package_from_session(sample_composer_session())

    assert package.validation["is_valid"] is True
    for file_name in REQUIRED_EXHIBIT_FILES:
        assert (package.exhibit_folder / file_name).exists()
    assert package.exhibit_type == "proximity_exhibit"


def test_exhibit_data_json_contains_title_prompt_layers_and_warnings(monkeypatch, tmp_path):
    monkeypatch.setattr(exhibit_exporter, "OUTPUTS_ROOT", tmp_path)

    package = generate_exhibit_package_from_session(sample_composer_session())
    data = json.loads((package.exhibit_folder / "exhibit_data.json").read_text(encoding="utf-8"))

    assert data["title_block"]["title"] == "Nearest Fire Station from 793 Bartram Ave"
    assert data["title_block"]["original_prompt"].startswith("make a map")
    assert data["layer_sources"]
    assert data["warnings"]
    assert data["published"] is False
    assert data["map_state_json"]["map_title"] == "Nearest Fire Station from 793 Bartram Ave"
    assert data["report_sections"]["sections"]
    assert data["statistics_sections"]["proximity"]["distance"]["value"] == 1.22
    assert data["export_mode"] == "map_exhibit_only"
    assert data["included_sections"]
    assert data["locked_map_state_used"] is True


def test_default_exhibit_html_is_map_first_without_forced_layer_table(monkeypatch, tmp_path):
    monkeypatch.setattr(exhibit_exporter, "OUTPUTS_ROOT", tmp_path)

    package = generate_exhibit_package_from_session(sample_composer_session())
    html = (package.exhibit_folder / "exhibit.html").read_text(encoding="utf-8")
    manifest = json.loads((package.exhibit_folder / "export_manifest.json").read_text(encoding="utf-8"))

    assert "Exhibit map frame" in html
    assert "Layer Source Table" not in html
    assert manifest["exportMode"] == "map_exhibit_only"
    assert manifest["lockedMapStateUsed"] is True
    assert any(section["section_id"] == "key_findings" for section in manifest["includedSections"])


def test_full_report_exhibit_html_includes_appendix_table(monkeypatch, tmp_path):
    monkeypatch.setattr(exhibit_exporter, "OUTPUTS_ROOT", tmp_path)
    session = sample_composer_session()
    session["composer_map_state"]["export_mode"] = "full_report"
    session["composer_map_state"]["export_options"] = {"export_mode": "full_report", "include_appendix": True}

    package = generate_exhibit_package_from_session(session)
    html = (package.exhibit_folder / "exhibit.html").read_text(encoding="utf-8")
    manifest = json.loads((package.exhibit_folder / "export_manifest.json").read_text(encoding="utf-8"))

    assert "Layer Source Table" in html
    assert 'class="appendix"' in html
    assert manifest["exportMode"] == "full_report"
    assert any(section["section_id"] == "statistics" for section in manifest["includedSections"])


def test_layer_sources_csv_contains_source_table(monkeypatch, tmp_path):
    monkeypatch.setattr(exhibit_exporter, "OUTPUTS_ROOT", tmp_path)

    package = generate_exhibit_package_from_session(sample_composer_session())
    csv_text = (package.exhibit_folder / "layer_sources.csv").read_text(encoding="utf-8")

    assert "Display name" in csv_text
    assert "Origin Address" in csv_text
    assert "Roads Context" in csv_text
    assert "derived local" in csv_text
    assert "https://example.test/roads/0" in csv_text


def test_warning_summary_preserves_limitations(monkeypatch, tmp_path):
    monkeypatch.setattr(exhibit_exporter, "OUTPUTS_ROOT", tmp_path)

    package = generate_exhibit_package_from_session(sample_composer_session())
    warning_json = json.loads((package.exhibit_folder / "warnings.json").read_text(encoding="utf-8"))

    serialized = json.dumps(warning_json)
    assert "Related parcel was not resolved" in serialized
    assert "Not official driving navigation" in serialized
    assert "No ArcGIS item was published" in serialized


def test_exhibit_files_do_not_include_secrets_or_cfs_references(monkeypatch, tmp_path):
    monkeypatch.setattr(exhibit_exporter, "OUTPUTS_ROOT", tmp_path)

    package = generate_exhibit_package_from_session(sample_composer_session())
    text = all_text(package.exhibit_folder).lower()

    assert ".env" not in text
    assert "secret" not in text
    assert "database_url" not in text
    assert "cfs" not in text


def test_list_and_get_exhibits(monkeypatch, tmp_path):
    monkeypatch.setattr(exhibit_exporter, "OUTPUTS_ROOT", tmp_path)
    package = generate_exhibit_package_from_session(sample_composer_session())

    exhibits = list_exhibits()
    detail = get_exhibit(package.exhibit_id)

    assert exhibits[0]["exhibit_id"] == package.exhibit_id
    assert detail["exhibit_data"]["title_block"]["title"] == "Nearest Fire Station from 793 Bartram Ave"


def test_unsupported_or_missing_session_returns_safe_error(monkeypatch, tmp_path):
    monkeypatch.setattr(exhibit_exporter, "OUTPUTS_ROOT", tmp_path)

    with pytest.raises(ValueError):
        generate_exhibit_package_from_session({})
    with pytest.raises(FileNotFoundError):
        get_exhibit("missing-exhibit")


def test_layer_source_rows_preserve_derived_and_reference_roles():
    rows = build_layer_source_rows(sample_composer_session())
    roles = {row["Display name"]: row["Official / proxy / reference / derived local"] for row in rows}

    assert roles["Origin Address"] == "derived local"
    assert roles["Roads Context"] == "official"
