"""ArcGIS WebMap draft JSON builder for AutoMap recipes."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.layer_catalog_store import load_catalog_records
from app.layer_semantics import slugify
from app.source_usage_intelligence import display_label_for_layer, source_warnings
from app.ui_models import output_file_url


WEBMAP_VERSION = "2.31"
AUTHORING_APP = "AutoMap"
AUTHORING_APP_VERSION = "0.4"
LOW_CONFIDENCE_THRESHOLD = 0.65

POINT_GEOMETRIES = {"esrigeometrypoint", "esrigeometrymultipoint"}
LINE_GEOMETRIES = {"esrigeometrypolyline"}
POLYGON_GEOMETRIES = {"esrigeometrypolygon"}
PROTECTED_TEXT_MARKERS = {"cfs", "cfs_dev"}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _compact_dict(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


def _catalog_lookup() -> dict[str, dict[str, Any]]:
    try:
        records = load_catalog_records()
    except Exception:
        return {}
    return {record["layer_key"]: record for record in records if record.get("layer_key")}


def _merge_catalog_metadata(
    selected_layers: list[dict[str, Any]],
    catalog_records: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    lookup = catalog_records if catalog_records is not None else _catalog_lookup()
    enriched_layers: list[dict[str, Any]] = []
    for layer in selected_layers:
        merged = deepcopy(lookup.get(layer.get("layer_key"), {}))
        for key, value in layer.items():
            if value is not None:
                merged[key] = value
        enriched_layers.append(merged)
    return enriched_layers


def _geometry_type(layer: dict[str, Any]) -> str:
    return str(layer.get("geometry_type") or "").lower()


def _is_point_layer(layer: dict[str, Any]) -> bool:
    return _geometry_type(layer) in POINT_GEOMETRIES


def _is_line_layer(layer: dict[str, Any]) -> bool:
    return _geometry_type(layer) in LINE_GEOMETRIES


def _is_polygon_layer(layer: dict[str, Any]) -> bool:
    return _geometry_type(layer) in POLYGON_GEOMETRIES


def _field_name(field: dict[str, Any]) -> str | None:
    return field.get("name") or field.get("field_name")


def _field_alias(field: dict[str, Any]) -> str | None:
    return field.get("alias") or field.get("field_alias") or _field_name(field)


def _visible_popup_fields(layer: dict[str, Any]) -> list[dict[str, Any]]:
    field_infos: list[dict[str, Any]] = []
    object_id_field = str(layer.get("object_id_field") or "").lower()
    for field in _as_list(layer.get("fields")):
        if not isinstance(field, dict):
            continue
        name = _field_name(field)
        if not name:
            continue
        field_type = str(field.get("type") or "").lower()
        lowered = name.lower()
        if lowered == object_id_field or "geometry" in field_type or lowered in {"shape", "objectid"}:
            continue
        field_infos.append(
            {
                "fieldName": name,
                "label": _field_alias(field),
                "visible": True,
            }
        )
        if len(field_infos) >= 12:
            break
    return field_infos


def _service_url_from_layer_url(layer_url: str | None) -> str | None:
    if not layer_url:
        return None
    parts = layer_url.rstrip("/").split("/")
    if parts and parts[-1].isdigit():
        return "/".join(parts[:-1])
    return layer_url


def _webmap_layer_type(layer: dict[str, Any]) -> str:
    if layer.get("is_group_layer") and not layer.get("is_feature_layer"):
        return "ArcGISMapServiceLayer"
    layer_url = str(layer.get("layer_url") or layer.get("rest_url") or "")
    if "/featureserver/" in layer_url.lower() or "/mapserver/" in layer_url.lower():
        return "ArcGISFeatureLayer"
    return "ArcGISMapServiceLayer"


def _recipe_implies_selected_parcels(recipe_context: dict[str, Any] | None) -> bool:
    recipe = (recipe_context or {}).get("recipe") or {}
    for operation in recipe.get("spatial_operations") or []:
        if operation.get("output") == "affected_parcels" or operation.get("operation") == "intersect":
            return True
    return False


def _display_title(layer: dict[str, Any], recipe_context: dict[str, Any] | None = None) -> str:
    layer_name = display_label_for_layer(layer)
    if layer.get("category") == "parcel" and _recipe_implies_selected_parcels(recipe_context):
        return f"Affected {layer_name}"
    return str(layer_name)


def _simple_fill_renderer(fill: list[int], outline: list[int], width: float = 1.0) -> dict[str, Any]:
    return {
        "type": "simple",
        "symbol": {
            "type": "esriSFS",
            "style": "esriSFSSolid",
            "color": fill,
            "outline": {
                "type": "esriSLS",
                "style": "esriSLSSolid",
                "color": outline,
                "width": width,
            },
        },
    }


def _simple_line_renderer(color: list[int], width: float = 1.5) -> dict[str, Any]:
    return {
        "type": "simple",
        "symbol": {
            "type": "esriSLS",
            "style": "esriSLSSolid",
            "color": color,
            "width": width,
        },
    }


def _simple_marker_renderer(color: list[int], outline: list[int]) -> dict[str, Any]:
    return {
        "type": "simple",
        "symbol": {
            "type": "esriSMS",
            "style": "esriSMSCircle",
            "color": color,
            "size": 8,
            "outline": {
                "type": "esriSLS",
                "style": "esriSLSSolid",
                "color": outline,
                "width": 1,
            },
        },
    }


def _unique_value_renderer(field_name: str, default_fill: list[int], default_outline: list[int]) -> dict[str, Any]:
    return {
        "type": "uniqueValue",
        "field1": field_name,
        "defaultLabel": "Other",
        "defaultSymbol": _simple_fill_renderer(default_fill, default_outline)["symbol"],
        "uniqueValueInfos": [],
    }


def _renderer_with_warnings(
    selected_layer: dict[str, Any],
    recipe_context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    category = selected_layer.get("category")
    filter_plan_entry = (recipe_context or {}).get("filter_plan_entry") or {}
    warnings: list[str] = []
    selected_field = filter_plan_entry.get("selected_field") or selected_layer.get("display_field")

    if category == "flood":
        return _simple_fill_renderer([33, 150, 243, 90], [0, 65, 120, 230], 1.25), warnings
    if category == "parcel":
        return _simple_fill_renderer([255, 193, 7, 35], [255, 193, 7, 255], 2.0), warnings
    if category == "zoning":
        if selected_field:
            if filter_plan_entry.get("needs_review"):
                warnings.append("Zoning code field or selected zoning values need review.")
            return _unique_value_renderer(selected_field, [156, 39, 176, 90], [88, 24, 120, 210]), warnings
        warnings.append("Zoning code field needs review before unique-value styling.")
        return _simple_fill_renderer([156, 39, 176, 70], [88, 24, 120, 210], 1.0), warnings
    if category == "schools":
        if selected_field:
            return _unique_value_renderer(selected_field, [76, 175, 80, 80], [32, 96, 45, 220]), warnings
        return _simple_fill_renderer([76, 175, 80, 55], [32, 96, 45, 220], 1.0), warnings
    if category in {"jurisdiction", "boundary"}:
        return _simple_fill_renderer([255, 255, 255, 0], [40, 40, 40, 230], 2.0), warnings
    if category == "transportation" or _is_line_layer(selected_layer):
        return _simple_line_renderer([69, 90, 100, 230], 1.5), warnings
    if _is_point_layer(selected_layer):
        return _simple_marker_renderer([244, 81, 30, 220], [120, 35, 10, 255]), warnings
    if _is_polygon_layer(selected_layer):
        return _simple_fill_renderer([96, 125, 139, 55], [55, 71, 79, 210], 1.0), warnings
    return _simple_marker_renderer([96, 125, 139, 220], [55, 71, 79, 255]), warnings


def build_renderer(selected_layer: dict[str, Any], recipe_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a conservative renderer from layer category and known fields."""
    renderer, _warnings = _renderer_with_warnings(selected_layer, recipe_context)
    return renderer


def _opacity_for_layer(layer: dict[str, Any]) -> float:
    category = layer.get("category")
    if category == "flood":
        return 0.35
    if category == "parcel":
        return 0.8
    if category == "zoning":
        return 0.65
    if category == "schools":
        return 0.55
    if category in {"jurisdiction", "boundary"}:
        return 0.9
    if category == "transportation":
        return 0.9
    if _is_point_layer(layer):
        return 0.85
    return 0.75


def build_definition_expression(filter_plan_entry: dict[str, Any] | None) -> str | None:
    """Return only the definition expression drafted by the v0.3 filter plan."""
    if not filter_plan_entry:
        return None
    expression = filter_plan_entry.get("draft_where_clause")
    if isinstance(expression, str) and expression.strip():
        return expression.strip()
    return None


def build_popup_info(selected_layer: dict[str, Any]) -> dict[str, Any]:
    """Build popup metadata from verified catalog field metadata."""
    field_infos = _visible_popup_fields(selected_layer)
    if not field_infos and selected_layer.get("display_field"):
        field_infos.append(
            {
                "fieldName": selected_layer["display_field"],
                "label": selected_layer["display_field"],
                "visible": True,
            }
        )
    return {
        "title": "{" + str(selected_layer.get("display_field") or "NAME") + "}",
        "description": f"{selected_layer.get('layer_name', 'Layer')} ({selected_layer.get('category', 'general')})",
        "fieldInfos": field_infos,
    }


def _review_warnings(
    selected_layer: dict[str, Any],
    filter_plan_entry: dict[str, Any] | None,
    renderer_warnings: list[str],
) -> list[str]:
    warnings = list(renderer_warnings)
    confidence = float(selected_layer.get("confidence_score") or 0)
    if confidence and confidence < LOW_CONFIDENCE_THRESHOLD:
        warnings.append("Layer match confidence is below the review threshold.")
    if filter_plan_entry:
        filter_confidence = float(filter_plan_entry.get("confidence_score") or 0)
        if build_definition_expression(filter_plan_entry) and filter_confidence and filter_confidence < LOW_CONFIDENCE_THRESHOLD:
            warnings.append("Filter expression confidence is below the review threshold.")
        if filter_plan_entry.get("needs_review"):
            warnings.append(filter_plan_entry.get("review_reason") or "Filter plan needs review.")
    if not (selected_layer.get("layer_url") or selected_layer.get("rest_url")):
        warnings.append("Layer URL is missing.")
    warnings.extend(source_warnings(selected_layer))
    return sorted({warning for warning in warnings if warning})


def build_operational_layer(
    selected_layer: dict[str, Any],
    filter_plan: dict[str, Any] | None = None,
    recipe_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one draft ArcGIS operational layer from a selected recipe layer."""
    layer_key = selected_layer.get("layer_key") or slugify(selected_layer.get("layer_name"))
    layer_url = selected_layer.get("layer_url") or selected_layer.get("rest_url")
    service_url = selected_layer.get("service_url") or _service_url_from_layer_url(layer_url)
    layer_id = selected_layer.get("layer_id")
    context = {**(recipe_context or {}), "filter_plan_entry": filter_plan or {}}
    renderer, renderer_warnings = _renderer_with_warnings(selected_layer, context)
    definition_expression = build_definition_expression(filter_plan)
    layer_definition: dict[str, Any] = {"drawingInfo": {"renderer": renderer}}
    if definition_expression:
        layer_definition["definitionExpression"] = definition_expression

    review_warnings = _review_warnings(selected_layer, filter_plan, renderer_warnings)
    operational_layer = _compact_dict(
        {
            "id": f"automap_{slugify(layer_key)}",
            "title": _display_title(selected_layer, recipe_context),
            "url": layer_url or service_url,
            "serviceUrl": service_url,
            "layerUrl": layer_url,
            "layerType": _webmap_layer_type(selected_layer),
            "visibility": True,
            "opacity": _opacity_for_layer(selected_layer),
            "itemId": selected_layer.get("service_item_id"),
            "layerId": layer_id,
            "layerDefinition": layer_definition,
            "popupInfo": build_popup_info(selected_layer),
            "showLegend": True,
            "autoMapRole": selected_layer.get("role"),
            "autoMapLayerKey": layer_key,
            "autoMapConfidence": selected_layer.get("confidence_score"),
            "autoMapNeedsReview": bool(review_warnings),
            "autoMapReviewWarnings": review_warnings,
            "autoMapSourceKey": selected_layer.get("source_key"),
            "autoMapSourceStatus": selected_layer.get("source_status"),
            "autoMapApprovalStatus": selected_layer.get("approval_status"),
            "autoMapSourceRole": selected_layer.get("source_role"),
            "autoMapCoverageGeography": selected_layer.get("coverage_geography"),
            "autoMapGapSupport": selected_layer.get("gap_support"),
            "autoMapSourcePriority": selected_layer.get("source_priority"),
        }
    )
    if definition_expression:
        operational_layer["autoMapDefinitionSource"] = "filter_plan"
        operational_layer["autoMapFilterPlanLayerKey"] = layer_key
    return operational_layer


def _layer_order_weight(layer: dict[str, Any]) -> tuple[int, int, str]:
    category = layer.get("category")
    role = layer.get("role")
    if role == "jurisdiction_filter" or category in {"jurisdiction", "boundary"}:
        weight = 10
    elif category in {"parcel", "cadastral"}:
        weight = 20
    elif category in {"zoning", "schools", "environmental", "terrain"}:
        weight = 30
    elif category == "flood" or role == "constraint_overlay":
        weight = 40
    elif category == "transportation" or role == "transportation_layer":
        weight = 50
    elif _is_point_layer(layer):
        weight = 60
    else:
        weight = 45
    return (weight, int(layer.get("source_priority") or 999), str(layer.get("layer_name") or ""))


def order_layers(selected_layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Order layers from bottom to top for WebMap drawing."""
    return sorted(selected_layers, key=_layer_order_weight)


def build_derived_analysis_layer(output: dict[str, Any], index: int = 0) -> dict[str, Any] | None:
    """Build a local-only derived GeoJSON layer metadata item."""
    path = output.get("output_geojson_path") or output.get("path")
    layer = output.get("derived_layer") if isinstance(output.get("derived_layer"), dict) else {}
    url = layer.get("url") or output.get("url") or output.get("layer_url") or (output_file_url(path) if path else None)
    title = layer.get("title") or output.get("title") or "Derived Local Analysis Result"
    if not url:
        return None
    return {
        "id": layer.get("id") or f"automap_derived_analysis_{index}",
        "title": title,
        "url": url,
        "layerUrl": url,
        "layerType": "GeoJSONLayer",
        "visibility": True,
        "opacity": layer.get("opacity", 0.85),
        "showLegend": True,
        "autoMapRole": "derived_analysis_result",
        "autoMapLayerKey": layer.get("layer_key") or output.get("layer_key") or f"derived_analysis_{index}",
        "autoMapSourceStatus": "derived_local",
        "autoMapSourcePriority": 0,
        "autoMapNeedsReview": True,
        "autoMapReviewWarnings": [
            "Derived local analysis result. Review before official use.",
            "This GeoJSON was not published or uploaded to ArcGIS.",
        ],
        "autoMapDerivedAnalysis": True,
        "autoMapAnalysisRunId": output.get("analysis_run_id"),
    }


def _normalize_extent(extent: Any) -> dict[str, Any] | None:
    if not isinstance(extent, dict):
        return None
    try:
        normalized = {
            "xmin": float(extent["xmin"]),
            "ymin": float(extent["ymin"]),
            "xmax": float(extent["xmax"]),
            "ymax": float(extent["ymax"]),
        }
    except (KeyError, TypeError, ValueError):
        return None
    spatial_reference = extent.get("spatialReference") or extent.get("spatial_reference")
    if isinstance(spatial_reference, dict):
        normalized["spatialReference"] = spatial_reference
    return normalized


def _extent_from_layers(layers: list[dict[str, Any]], *, prefer_boundary: bool = False) -> dict[str, Any] | None:
    candidates = layers
    if prefer_boundary:
        boundary_layers = [
            layer
            for layer in layers
            if layer.get("role") == "jurisdiction_filter" or layer.get("category") in {"jurisdiction", "boundary"}
        ]
        candidates = boundary_layers or layers
    for layer in candidates:
        normalized = _normalize_extent(layer.get("extent"))
        if normalized:
            return normalized
    return None


def _catalog_extent_for_requested_geography(recipe: dict[str, Any]) -> dict[str, Any] | None:
    geographies = recipe.get("parsed_request", {}).get("geography_terms") or []
    if not geographies:
        return None
    names = [str(geo.get("name") or "").lower() for geo in geographies]
    for record in _catalog_lookup().values():
        if record.get("category") not in {"jurisdiction", "boundary"}:
            continue
        text = f"{record.get('layer_name', '')} {record.get('service_name', '')}".lower()
        if any(name and name in text for name in names):
            normalized = _normalize_extent(record.get("extent"))
            if normalized:
                return normalized
    return None


def build_initial_extent(recipe: dict[str, Any]) -> dict[str, Any]:
    """Choose an initial map extent from metadata only, never feature geometry."""
    selected_layers = recipe.get("selected_layers") or []
    geographies = recipe.get("parsed_request", {}).get("geography_terms") or []
    prefer_boundary = bool(geographies)

    extent = _extent_from_layers(selected_layers, prefer_boundary=prefer_boundary)
    if extent:
        return extent

    extent = _catalog_extent_for_requested_geography(recipe)
    if extent:
        return extent

    extent = _extent_from_layers(selected_layers, prefer_boundary=False)
    return extent or {}


def _first_spatial_reference(layers: list[dict[str, Any]], extent: dict[str, Any]) -> dict[str, Any]:
    if isinstance(extent.get("spatialReference"), dict):
        return extent["spatialReference"]
    for layer in layers:
        spatial_reference = layer.get("spatial_reference") or layer.get("spatialReference")
        if isinstance(spatial_reference, dict):
            return spatial_reference
        layer_extent = _normalize_extent(layer.get("extent"))
        if layer_extent and isinstance(layer_extent.get("spatialReference"), dict):
            return layer_extent["spatialReference"]
    return {}


def _base_map() -> dict[str, Any]:
    return {
        "title": "Light Gray Canvas",
        "baseMapLayers": [
            {
                "id": "World_Light_Gray_Base",
                "layerType": "ArcGISTiledMapServiceLayer",
                "url": "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer",
                "visibility": True,
                "opacity": 1,
                "title": "Light Gray Base",
            }
        ],
    }


def build_webmap_json(recipe: dict[str, Any]) -> dict[str, Any]:
    """Build a local-only draft ArcGIS WebMap JSON object from a map recipe."""
    enriched_layers = _merge_catalog_metadata(recipe.get("selected_layers") or [])
    ordered_layers = order_layers(enriched_layers)
    filter_plan = recipe.get("filter_plan") or {}
    context = {"recipe": recipe, "filter_plan": filter_plan}
    operational_layers = [
        build_operational_layer(layer, filter_plan.get(layer.get("layer_key")), context)
        for layer in ordered_layers
    ]
    for index, output in enumerate((recipe.get("analysis_execution") or {}).get("derived_outputs") or []):
        if isinstance(output, dict):
            derived_layer = build_derived_analysis_layer(output, index=index)
            if derived_layer:
                operational_layers.append(derived_layer)
    extent_recipe = {**recipe, "selected_layers": ordered_layers}
    initial_extent = build_initial_extent(extent_recipe)
    spatial_reference = _first_spatial_reference(ordered_layers, initial_extent)

    webmap_json = {
        "title": recipe.get("map_title") or "AutoMap Draft WebMap",
        "description": "Draft WebMap JSON generated from verified AutoMap catalog metadata. No ArcGIS item was created.",
        "operationalLayers": operational_layers,
        "baseMap": _base_map(),
        "spatialReference": spatial_reference,
        "version": WEBMAP_VERSION,
        "authoringApp": AUTHORING_APP,
        "authoringAppVersion": AUTHORING_APP_VERSION,
        "applicationProperties": {
            "viewing": {
                "search": {"enabled": False},
                "routing": {"enabled": False},
            }
        },
        "initialState": {"viewpoint": {"targetGeometry": initial_extent}},
        "autoMapPublicationStatus": "draft_only_not_published",
        "autoMapGeneratedAt": datetime.now(UTC).isoformat(),
        "autoMapRecipeSummary": {
            "user_intent": recipe.get("user_intent"),
            "confidence_score": recipe.get("confidence_score"),
            "needs_review": recipe.get("needs_review"),
            "review_reasons": recipe.get("review_reasons") or [],
            "missing_data_needed": recipe.get("missing_data_needed") or [],
            "suggested_extent": recipe.get("suggested_extent") or {},
            "source_coverage": recipe.get("source_coverage") or {},
        },
        "autoMapWarnings": list(recipe.get("review_reasons") or []),
    }

    validation = validate_webmap_json(webmap_json)
    webmap_json["autoMapValidation"] = validation
    webmap_json["autoMapWarnings"] = sorted(
        {
            *webmap_json["autoMapWarnings"],
            *validation.get("warnings", []),
            *validation.get("errors", []),
        }
    )
    return webmap_json


def _iter_strings(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            strings.extend(_iter_strings(item))
    elif isinstance(value, list):
        for item in value:
            strings.extend(_iter_strings(item))
    elif isinstance(value, str):
        strings.append(value)
    return strings


def _has_protected_reference(value: Any) -> bool:
    for text in _iter_strings(value):
        lowered = text.lower()
        if any(marker in lowered for marker in PROTECTED_TEXT_MARKERS):
            return True
    return False


def validate_webmap_json(webmap_json: dict[str, Any]) -> dict[str, Any]:
    """Validate AutoMap's draft WebMap JSON without contacting ArcGIS."""
    errors: list[str] = []
    warnings: list[str] = []
    required_keys = {
        "operationalLayers",
        "baseMap",
        "spatialReference",
        "version",
        "authoringApp",
        "authoringAppVersion",
        "applicationProperties",
        "initialState",
    }
    missing_keys = sorted(required_keys - set(webmap_json))
    if missing_keys:
        errors.append(f"Missing required WebMap keys: {', '.join(missing_keys)}")

    operational_layers = webmap_json.get("operationalLayers")
    if not isinstance(operational_layers, list):
        errors.append("operationalLayers must be a list.")
        operational_layers = []
    if not operational_layers:
        warnings.append("Draft contains no operational layers.")

    if _has_protected_reference(webmap_json):
        errors.append("Draft WebMap JSON contains a protected CFS reference.")

    blocked_publish_keys = {"portalItem", "portalUrl", "token", "username", "password"}
    present_publish_keys = sorted(blocked_publish_keys & set(webmap_json))
    if present_publish_keys:
        errors.append(f"Draft includes publishing or login keys: {', '.join(present_publish_keys)}")

    for index, layer in enumerate(operational_layers):
        title = layer.get("title")
        url = layer.get("url")
        layer_key = layer.get("autoMapLayerKey")
        if not title:
            errors.append(f"Layer {index} is missing title.")
        elif str(title).lower() in {"layer", "unknown", "untitled layer", "fake layer"}:
            errors.append(f"Layer {index} has a placeholder title.")
        if not url:
            errors.append(f"{title or f'Layer {index}'} is missing url.")
        if not layer_key:
            errors.append(f"{title or f'Layer {index}'} is missing autoMapLayerKey.")
        if layer.get("autoMapNeedsReview") and not layer.get("autoMapReviewWarnings"):
            warnings.append(f"{title or f'Layer {index}'} is marked for review without warnings.")

        layer_definition = layer.get("layerDefinition") or {}
        definition_expression = layer_definition.get("definitionExpression")
        if definition_expression:
            definition_source = layer.get("autoMapDefinitionSource")
            if definition_source not in {"filter_plan", "human_adjustment"}:
                errors.append(f"{title or f'Layer {index}'} definitionExpression is not marked as filter_plan or human_adjustment sourced.")
            if definition_source == "filter_plan" and layer.get("autoMapFilterPlanLayerKey") != layer_key:
                errors.append(f"{title or f'Layer {index}'} definitionExpression is missing its filter plan layer key.")

    return {
        "is_valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "operational_layer_count": len(operational_layers),
    }
