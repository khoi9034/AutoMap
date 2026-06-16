"""External source registry for reviewable AutoMap data gap connectors."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.arcgis_rest_inspector import ArcGISRestError
from app.arcgis_service_search import inspect_candidate_layer, inspect_candidate_service
from app.db import _quote_identifier, get_engine
from app.layer_catalog_store import upsert_layer_records
from app.layer_semantics import date_fields_from_fields, slugify
from app.source_candidate_evaluator import classify_source_limitations, recommend_catalog_category
from app.source_usage_intelligence import catalog_semantics_for_category
from app.ui_models import repo_root


SEED_PATH = Path("data/external_rest_sources.seed.json")
SOURCE_TYPES = {"arcgis_mapserver", "arcgis_featureserver", "arcgis_layer", "external_reference"}
APPROVAL_STATUSES = {"approved", "candidate", "needs_review"}
SOURCE_STATUSES = {"active", "proxy", "reference", "legacy"}
JSON_COLUMNS = {"categories", "intended_gaps", "inspected_metadata"}


def _table(schema_name: str, table_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.{table_name}"


def _json_value(value: Any) -> str:
    return json.dumps(value if value is not None else [])


def init_external_source_tables(schema_name: str = "automap") -> None:
    """Create additive external-source and resolution-log tables."""
    registry = _table(schema_name, "external_source_registry")
    resolution = _table(schema_name, "data_gap_resolution_log")
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(schema_name)};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {registry} (
                    id serial PRIMARY KEY,
                    source_key text UNIQUE,
                    source_name text,
                    source_type text,
                    base_url text,
                    layer_url text,
                    priority integer,
                    approval_status text,
                    source_status text,
                    categories jsonb DEFAULT '[]'::jsonb,
                    intended_gaps jsonb DEFAULT '[]'::jsonb,
                    inspected_metadata jsonb DEFAULT '{{}}'::jsonb,
                    limitations text,
                    is_active boolean DEFAULT true,
                    created_at timestamptz DEFAULT now(),
                    updated_at timestamptz DEFAULT now()
                );
                """
            )
        )
        for column, column_type in {
            "source_key": "text UNIQUE",
            "source_name": "text",
            "source_type": "text",
            "base_url": "text",
            "layer_url": "text",
            "priority": "integer",
            "approval_status": "text",
            "source_status": "text",
            "categories": "jsonb DEFAULT '[]'::jsonb",
            "intended_gaps": "jsonb DEFAULT '[]'::jsonb",
            "inspected_metadata": "jsonb DEFAULT '{}'::jsonb",
            "limitations": "text",
            "is_active": "boolean DEFAULT true",
            "created_at": "timestamptz DEFAULT now()",
            "updated_at": "timestamptz DEFAULT now()",
        }.items():
            connection.execute(text(f"ALTER TABLE {registry} ADD COLUMN IF NOT EXISTS {column} {column_type};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {resolution} (
                    id serial PRIMARY KEY,
                    gap_key text,
                    source_key text,
                    resolution_status text,
                    resolution_notes text,
                    source_score numeric,
                    inspected_metadata jsonb DEFAULT '{{}}'::jsonb,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
        )
        for column, column_type in {
            "gap_key": "text",
            "source_key": "text",
            "resolution_status": "text",
            "resolution_notes": "text",
            "source_score": "numeric",
            "inspected_metadata": "jsonb DEFAULT '{}'::jsonb",
            "created_at": "timestamptz DEFAULT now()",
        }.items():
            connection.execute(text(f"ALTER TABLE {resolution} ADD COLUMN IF NOT EXISTS {column} {column_type};"))


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def validate_external_source_record(record: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize one external source seed/registry record."""
    errors: list[str] = []
    normalized = {
        "source_key": str(record.get("source_key") or "").strip(),
        "source_name": str(record.get("source_name") or "").strip(),
        "source_type": str(record.get("source_type") or "").strip(),
        "base_url": record.get("base_url") or None,
        "layer_url": record.get("layer_url") or None,
        "priority": int(record.get("priority") or 999),
        "approval_status": str(record.get("approval_status") or "needs_review").strip(),
        "source_status": str(record.get("source_status") or "reference").strip(),
        "categories": _as_string_list(record.get("categories")),
        "intended_gaps": _as_string_list(record.get("intended_gaps")),
        "notes": str(record.get("notes") or "").strip(),
        "limitations": str(record.get("limitations") or "").strip(),
        "inspected_metadata": record.get("inspected_metadata") if isinstance(record.get("inspected_metadata"), dict) else {},
        "is_active": bool(record.get("is_active", True)),
    }
    if not normalized["source_key"]:
        errors.append("source_key is required.")
    if not normalized["source_name"]:
        errors.append("source_name is required.")
    if normalized["source_type"] not in SOURCE_TYPES:
        errors.append(f"source_type must be one of {sorted(SOURCE_TYPES)}.")
    if normalized["approval_status"] not in APPROVAL_STATUSES:
        errors.append(f"approval_status must be one of {sorted(APPROVAL_STATUSES)}.")
    if normalized["source_status"] not in SOURCE_STATUSES:
        errors.append(f"source_status must be one of {sorted(SOURCE_STATUSES)}.")
    if normalized["source_type"] in {"arcgis_mapserver", "arcgis_featureserver"} and not normalized["base_url"]:
        errors.append("base_url is required for ArcGIS service sources.")
    if normalized["source_type"] == "arcgis_layer" and not normalized["layer_url"]:
        errors.append("layer_url is required for ArcGIS layer sources.")
    if errors:
        raise ValueError("; ".join(errors))
    return normalized


def load_external_sources(path: str | Path = SEED_PATH) -> list[dict[str, Any]]:
    """Load and validate seed external source records."""
    seed_path = Path(path)
    if not seed_path.is_absolute():
        seed_path = repo_root() / seed_path
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("External source seed file must contain a JSON list.")
    return [validate_external_source_record(record) for record in data]


def upsert_external_sources(records: list[dict[str, Any]], schema_name: str = "automap") -> int:
    """Upsert external source records into automap.external_source_registry."""
    init_external_source_tables(schema_name)
    if not records:
        return 0
    registry = _table(schema_name, "external_source_registry")
    sql = text(
        f"""
        INSERT INTO {registry} AS target (
            source_key, source_name, source_type, base_url, layer_url, priority,
            approval_status, source_status, categories, intended_gaps,
            inspected_metadata, limitations, is_active, created_at, updated_at
        )
        VALUES (
            :source_key, :source_name, :source_type, :base_url, :layer_url, :priority,
            :approval_status, :source_status, CAST(:categories AS jsonb), CAST(:intended_gaps AS jsonb),
            CAST(:inspected_metadata AS jsonb), :limitations, :is_active, :created_at, :updated_at
        )
        ON CONFLICT (source_key) DO UPDATE SET
            source_name = EXCLUDED.source_name,
            source_type = EXCLUDED.source_type,
            base_url = EXCLUDED.base_url,
            layer_url = EXCLUDED.layer_url,
            priority = EXCLUDED.priority,
            approval_status = EXCLUDED.approval_status,
            source_status = EXCLUDED.source_status,
            categories = EXCLUDED.categories,
            intended_gaps = EXCLUDED.intended_gaps,
            inspected_metadata = CASE
                WHEN EXCLUDED.inspected_metadata = '{{}}'::jsonb THEN target.inspected_metadata
                ELSE EXCLUDED.inspected_metadata
            END,
            limitations = EXCLUDED.limitations,
            is_active = EXCLUDED.is_active,
            updated_at = now();
        """
    )
    now = datetime.now(UTC)
    engine = get_engine()
    with engine.begin() as connection:
        for record in records:
            normalized = validate_external_source_record(record)
            connection.execute(
                sql,
                {
                    **normalized,
                    "categories": _json_value(normalized["categories"]),
                    "intended_gaps": _json_value(normalized["intended_gaps"]),
                    "inspected_metadata": json.dumps(normalized.get("inspected_metadata") or {}),
                    "created_at": now,
                    "updated_at": now,
                },
            )
    return len(records)


def list_external_sources(schema_name: str = "automap") -> list[dict[str, Any]]:
    """List external source registry records."""
    init_external_source_tables(schema_name)
    registry = _table(schema_name, "external_source_registry")
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT source_key, source_name, source_type, base_url, layer_url, priority,
                       approval_status, source_status, categories, intended_gaps,
                       inspected_metadata, limitations, is_active, created_at, updated_at
                FROM {registry}
                WHERE is_active = true
                ORDER BY priority NULLS LAST, source_key;
                """
            )
        ).mappings()
        return [dict(row) for row in rows]


def get_external_source(source_key: str, schema_name: str = "automap") -> dict[str, Any]:
    """Return one external source registry record."""
    init_external_source_tables(schema_name)
    registry = _table(schema_name, "external_source_registry")
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(
            text(
                f"""
                SELECT source_key, source_name, source_type, base_url, layer_url, priority,
                       approval_status, source_status, categories, intended_gaps,
                       inspected_metadata, limitations, is_active, created_at, updated_at
                FROM {registry}
                WHERE source_key = :source_key AND is_active = true;
                """
            ),
            {"source_key": source_key},
        ).mappings().first()
    if not row:
        raise FileNotFoundError(f"External source not found: {source_key}")
    return dict(row)


def _inspect_arcgis_layer(layer_url: str) -> dict[str, Any]:
    return inspect_candidate_layer(layer_url)


def inspect_external_source(source: dict[str, Any] | str) -> dict[str, Any]:
    """Inspect one external source with metadata/count-only behavior."""
    record = get_external_source(source) if isinstance(source, str) else validate_external_source_record(source)
    source_type = record["source_type"]
    metadata: dict[str, Any]
    if source_type == "external_reference":
        metadata = {
            "inspection_status": "reference_only",
            "is_verified": False,
            "verification_status": "needs_review",
            "record_count": None,
            "downloaded_geometry": False,
            "notes": "External reference has no ArcGIS REST layer URL configured for metadata inspection.",
        }
    elif source_type == "arcgis_layer":
        try:
            metadata = _inspect_arcgis_layer(str(record["layer_url"]))
        except ArcGISRestError as exc:
            metadata = {
                "inspection_status": "failed",
                "is_verified": False,
                "verification_status": "failed",
                "verification_error": str(exc),
                "downloaded_geometry": False,
            }
    else:
        service_url = str(record.get("base_url") or "").rstrip("/")
        try:
            metadata = inspect_candidate_service(service_url)
        except ArcGISRestError as exc:
            metadata = {
                "inspection_status": "failed",
                "is_verified": False,
                "verification_status": "failed",
                "verification_error": str(exc),
                "downloaded_geometry": False,
            }
    metadata["classified_limitations"] = classify_source_limitations({**record, "inspected_metadata": metadata})
    return {**record, "inspected_metadata": metadata}


def update_external_source_metadata(source_key: str, inspected_metadata: dict[str, Any], schema_name: str = "automap") -> dict[str, Any]:
    """Persist inspected metadata for one source."""
    init_external_source_tables(schema_name)
    registry = _table(schema_name, "external_source_registry")
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                UPDATE {registry}
                SET inspected_metadata = CAST(:metadata AS jsonb),
                    updated_at = now()
                WHERE source_key = :source_key;
                """
            ),
            {"source_key": source_key, "metadata": json.dumps(inspected_metadata, default=str)},
        )
    return get_external_source(source_key, schema_name)


def _catalog_record_from_source(source: dict[str, Any], layer_metadata: dict[str, Any], layer_url: str, layer_id: int = 0) -> dict[str, Any]:
    name = str(layer_metadata.get("layer_name") or layer_metadata.get("name") or source["source_name"])
    category = recommend_catalog_category(source)
    semantics = catalog_semantics_for_category(category, source)
    limitations = source.get("limitations") or ""
    if semantics.get("known_limitations"):
        limitations = f"{limitations} {semantics['known_limitations']}".strip()
    source_status = source.get("source_status") or "reference"
    if source_status == "proxy":
        limitations = f"{limitations} Proxy/context only; not official approval or capacity.".strip()
    layer_key = f"external_{slugify(source['source_key'])}_{layer_id}_{slugify(name)}"
    fields = layer_metadata.get("fields") or []
    return {
        "layer_key": layer_key,
        "layer_name": name,
        "rest_url": layer_url,
        "category": category,
        "aliases": sorted(set([name.lower(), *semantics["aliases"]])),
        "description": source.get("notes"),
        "geometry_type": layer_metadata.get("geometry_type"),
        "date_fields": date_fields_from_fields(fields),
        "common_filters": [],
        "planning_use_cases": sorted(set(semantics["planning_use_cases"])),
        "recommended_symbology": {},
        "known_limitations": limitations,
        "is_public": True,
        "is_active": True,
        "source_key": source["source_key"],
        "source_priority": source.get("priority"),
        "source_status": source_status,
        "approval_status": source.get("approval_status") or "needs_review",
        "service_name": source.get("source_name"),
        "service_url": source.get("base_url") or layer_url.rsplit("/", 1)[0],
        "layer_id": layer_id,
        "layer_url": layer_url,
        "layer_type": layer_metadata.get("layer_type"),
        "parent_layer_id": layer_metadata.get("parent_layer_id"),
        "sublayer_ids": layer_metadata.get("sublayer_ids") or [],
        "is_group_layer": bool(layer_metadata.get("is_group_layer")),
        "is_feature_layer": bool(layer_metadata.get("is_feature_layer")),
        "spatial_reference": (layer_metadata.get("extent") or {}).get("spatialReference"),
        "extent": layer_metadata.get("extent"),
        "supported_query_formats": [],
        "capabilities": layer_metadata.get("capabilities") or [],
        "max_record_count": layer_metadata.get("max_record_count"),
        "object_id_field": layer_metadata.get("object_id_field"),
        "display_field": layer_metadata.get("display_field"),
        "type_id_field": layer_metadata.get("type_id_field"),
        "fields": fields,
        "drawing_info": layer_metadata.get("drawing_info"),
        "service_item_id": None,
        "record_count": layer_metadata.get("record_count") or (source.get("inspected_metadata") or {}).get("record_count"),
        "is_verified": bool(layer_metadata.get("is_verified") or (source.get("inspected_metadata") or {}).get("is_verified")),
        "verification_status": layer_metadata.get("verification_status") or (source.get("inspected_metadata") or {}).get("verification_status"),
        "verification_error": layer_metadata.get("verification_error") or (source.get("inspected_metadata") or {}).get("verification_error"),
        "verified_at": datetime.now(UTC).isoformat(),
        "is_historical": False,
        "historical_year": None,
        "canonical_topic": semantics["canonical_topic"],
        "superseded_by_layer_key": None,
        "source_notes": source.get("notes"),
    }


def upsert_external_source_to_catalog(source_key: str, schema_name: str = "automap") -> int:
    """Add verified inspected external ArcGIS layers to the AutoMap layer catalog."""
    source = get_external_source(source_key, schema_name)
    metadata = source.get("inspected_metadata") or {}
    records: list[dict[str, Any]] = []
    if metadata.get("inspection_status") == "reference_only":
        return 0
    if source.get("source_type") == "arcgis_layer":
        layer_metadata = metadata.get("layer_metadata") or {}
        if metadata.get("is_verified") and source.get("layer_url"):
            records.append(_catalog_record_from_source(source, layer_metadata, source["layer_url"], int(layer_metadata.get("layer_id") or 0)))
    else:
        for layer in metadata.get("layers") or []:
            layer_metadata = layer.get("layer_metadata") or {}
            if layer.get("is_verified") and layer.get("layer_url"):
                records.append(_catalog_record_from_source(source, layer_metadata, layer["layer_url"], int(layer.get("layer_id") or 0)))
    return upsert_layer_records(records, schema_name=schema_name)


def load_seed_external_sources(schema_name: str = "automap") -> dict[str, Any]:
    """Load seed records into the registry."""
    records = load_external_sources()
    count = upsert_external_sources(records, schema_name)
    return {"loaded": count, "sources": records}


def inspect_registered_external_sources(schema_name: str = "automap") -> dict[str, Any]:
    """Inspect all registered external sources and upsert verified layers when possible."""
    sources = list_external_sources(schema_name)
    inspected: list[dict[str, Any]] = []
    catalog_upserts = 0
    for source in sources:
        inspected_source = inspect_external_source(source)
        updated = update_external_source_metadata(source["source_key"], inspected_source["inspected_metadata"], schema_name)
        catalog_upserts += upsert_external_source_to_catalog(source["source_key"], schema_name)
        inspected.append(updated)
    return {"inspected": len(inspected), "catalog_upserts": catalog_upserts, "sources": inspected}
