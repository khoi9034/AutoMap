import json
from pathlib import Path

from app.recipe_engine import build_recipe
from app.report_generator import build_report_data
from app.report_models import ReportSource
from app.review_packet_builder import build_review_summary, build_warning_report
from app.source_usage_intelligence import catalog_semantics_for_category, source_role_for_layer
from app.webmap_builder import build_webmap_json
from tests.test_recipe_engine import record, sample_catalog


def external_catalog():
    catalog = sample_catalog() + [
        record(
            "roads",
            "Cabarrus County Centerlines",
            "transportation",
            aliases=["roads", "streets", "centerlines", "road access"],
            service_name="Cabarrus_County_Centerlines",
        ),
        record(
            "aadt",
            "NCDOT 2024 AADT Stations",
            "transportation",
            aliases=["traffic", "aadt", "traffic count", "high traffic", "road volume"],
            service_name="NCDOT_AADT",
            status="reference",
        ),
        record(
            "stip",
            "2026-2035 STIP Lines",
            "transportation_projects",
            aliases=["stip", "planned road projects", "transportation projects", "road improvements"],
            service_name="NCDOT_STIP",
            status="reference",
        ),
        record(
            "accela",
            "AccelaQuery",
            "development_activity_proxy",
            aliases=["accela", "plan review", "development pipeline", "development activity", "nearby development"],
            service_name="AccelaQuery",
            status="proxy",
        ),
        record(
            "concord_planning",
            "Planning Cases",
            "planning_cases",
            aliases=["planning cases", "rezoning", "development cases"],
            service_name="Concord_Planning_Cases",
            status="active",
        ),
    ]
    for row in catalog:
        if row["layer_key"] == "aadt":
            row.update(
                source_key="external_ncdot_aadt_reference",
                approval_status="approved",
                known_limitations="Reference/context only. Traffic counts are not development approvals.",
            )
        elif row["layer_key"] == "stip":
            row.update(
                source_key="external_ncdot_stip_reference",
                approval_status="approved",
                known_limitations="Reference/context only. STIP projects are not development pipeline sources.",
            )
        elif row["layer_key"] == "accela":
            row.update(
                source_key="external_cabarrus_accela_plan_review_proxy",
                approval_status="approved",
                known_limitations="Proxy/context only; not final permit approval or completed development.",
            )
        elif row["layer_key"] == "concord_planning":
            row.update(
                source_key="external_concord_planning_cases_limited_candidate",
                approval_status="candidate",
                known_limitations="Coverage limited to Concord only.",
            )
    return catalog


def selected_keys(recipe):
    return {layer["layer_key"] for layer in recipe["selected_layers"]}


def source_coverage_keys(recipe, group):
    return {item.get("layer_key") or item.get("gap_key") for item in recipe["source_coverage"].get(group, [])}


def test_external_semantics_classify_aadt_stip_and_accela_roles():
    assert "traffic count" in catalog_semantics_for_category("transportation")["aliases"]
    assert "planned road projects" in catalog_semantics_for_category("transportation_projects")["aliases"]
    assert "plan review" in catalog_semantics_for_category("development_activity_proxy")["aliases"]

    assert source_role_for_layer(external_catalog()[11]) == "reference"
    assert source_role_for_layer(external_catalog()[12]) == "reference"
    assert source_role_for_layer(external_catalog()[13]) == "proxy"
    assert source_role_for_layer(external_catalog()[14]) == "limited_coverage"


def test_high_traffic_prompt_selects_aadt_and_proxy_development_with_warnings():
    recipe = build_recipe(
        "Show high traffic corridors and nearby development activity.",
        external_catalog(),
        include_filter_intelligence=False,
        persist_data_gaps=False,
    )

    assert {"roads", "aadt", "accela"}.issubset(selected_keys(recipe))
    assert "aadt" in source_coverage_keys(recipe, "reference_sources")
    assert "accela" in source_coverage_keys(recipe, "proxy_sources")
    assert "current_permits" in source_coverage_keys(recipe, "missing_official_sources")
    assert "current_development_pipeline" in source_coverage_keys(recipe, "missing_official_sources")
    assert any("proxy/context source only" in warning for warning in recipe["source_coverage"]["warnings"])


def test_planned_road_prompt_selects_stip_and_keeps_proxy_warning():
    recipe = build_recipe(
        "Show planned road projects near development pressure areas.",
        external_catalog(),
        include_filter_intelligence=False,
        persist_data_gaps=False,
    )

    assert {"roads", "stip", "accela"}.issubset(selected_keys(recipe))
    assert "stip" in source_coverage_keys(recipe, "reference_sources")
    assert "accela" in source_coverage_keys(recipe, "proxy_sources")
    assert "current_permits" in source_coverage_keys(recipe, "missing_official_sources")


def test_current_permits_near_kannapolis_keeps_official_gap_open():
    recipe = build_recipe(
        "Show current permits near Kannapolis.",
        external_catalog(),
        include_filter_intelligence=False,
        persist_data_gaps=False,
    )

    assert "accela" not in selected_keys(recipe)
    assert "concord_planning" not in selected_keys(recipe)
    assert "permits" in recipe["missing_data_needed"]
    assert "development" not in recipe["missing_data_needed"]
    assert "current_permits" in source_coverage_keys(recipe, "missing_official_sources")
    assert any("Missing official current permit layer" in warning for warning in recipe["source_coverage"]["warnings"])


def test_planning_cases_around_concord_uses_limited_source_not_countywide_claim():
    recipe = build_recipe(
        "Show planning cases around Concord.",
        external_catalog(),
        include_filter_intelligence=False,
        persist_data_gaps=False,
    )

    assert "concord_planning" in selected_keys(recipe)
    assert "concord_planning" in source_coverage_keys(recipe, "limited_coverage_sources")
    assert "current_planning_cases" not in source_coverage_keys(recipe, "missing_official_sources")
    assert any("do not imply countywide coverage" in warning for warning in recipe["source_coverage"]["warnings"])


def test_review_webmap_and_report_outputs_preserve_source_coverage_warnings():
    recipe = build_recipe(
        "Show high traffic corridors and nearby development activity.",
        external_catalog(),
        include_filter_intelligence=False,
        persist_data_gaps=False,
    )
    webmap = build_webmap_json(recipe)
    warnings = build_warning_report(recipe, webmap)
    summary = build_review_summary(recipe, webmap)
    report_data = build_report_data(
        ReportSource(
            packet_path=Path("outputs/review_packets/mock"),
            packet_type="review",
            recipe=recipe,
            webmap=webmap,
            warnings=warnings,
        )
    )

    serialized = json.dumps({"recipe": recipe, "webmap": webmap, "warnings": warnings, "report": report_data}).lower()
    assert "source_coverage_warnings" in warnings
    assert any("proxy/context source only" in warning for warning in warnings["source_coverage_warnings"])
    assert "Source Coverage" in summary
    assert report_data["source_coverage"]["proxy_sources"]
    assert "cfs_dev" not in serialized
    assert "database_url" not in serialized
