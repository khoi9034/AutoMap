"""Typed models and constants for safe AutoMap spatial analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


DEFAULT_MAX_FEATURES = 2000
HARD_MAX_FEATURES = 5000


class AnalysisOperationType(StrEnum):
    """Supported analysis operation identifiers."""

    FILTER_BY_GEOGRAPHY = "filter_by_geography"
    SELECT_BY_INTERSECTION = "select_by_intersection"
    SELECT_BY_DISTANCE = "select_by_distance"
    EXCLUDE_BY_INTERSECTION = "exclude_by_intersection"
    SUMMARIZE_BY_BOUNDARY = "summarize_by_boundary"
    ATTRIBUTE_FILTER_ONLY = "attribute_filter_only"
    UNSUPPORTED_OPERATION = "unsupported_operation"


@dataclass
class AnalysisLayerRef:
    """A trusted catalog layer participating in an analysis plan."""

    layer_key: str
    layer_name: str
    category: str | None = None
    role: str | None = None
    layer_url: str | None = None
    service_url: str | None = None
    layer_id: int | None = None
    object_id_field: str | None = None
    geometry_type: str | None = None
    source_status: str | None = None
    is_historical: bool = False

    @classmethod
    def from_layer(cls, layer: dict[str, Any]) -> "AnalysisLayerRef":
        """Create a layer reference from a selected recipe/catalog layer."""
        layer_id = layer.get("layer_id")
        try:
            layer_id = int(layer_id) if layer_id is not None else None
        except (TypeError, ValueError):
            layer_id = None
        return cls(
            layer_key=str(layer.get("layer_key") or ""),
            layer_name=str(layer.get("layer_name") or layer.get("title") or ""),
            category=layer.get("category"),
            role=layer.get("role"),
            layer_url=layer.get("layer_url") or layer.get("rest_url"),
            service_url=layer.get("service_url"),
            layer_id=layer_id,
            object_id_field=layer.get("object_id_field"),
            geometry_type=layer.get("geometry_type"),
            source_status=layer.get("source_status"),
            is_historical=bool(layer.get("is_historical")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable layer reference data."""
        return {
            "layer_key": self.layer_key,
            "layer_name": self.layer_name,
            "category": self.category,
            "role": self.role,
            "layer_url": self.layer_url,
            "service_url": self.service_url,
            "layer_id": self.layer_id,
            "object_id_field": self.object_id_field,
            "geometry_type": self.geometry_type,
            "source_status": self.source_status,
            "is_historical": self.is_historical,
        }


@dataclass
class AnalysisPlanResult:
    """A safe execution feasibility plan."""

    raw_prompt: str
    operation_type: AnalysisOperationType
    executable: bool
    supported_operations: list[str]
    blocked_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    estimated_query_counts: dict[str, Any] = field(default_factory=dict)
    recommended_execution_plan: list[str] = field(default_factory=list)
    target_layer: AnalysisLayerRef | None = None
    geography_layer: AnalysisLayerRef | None = None
    constraint_layer: AnalysisLayerRef | None = None
    attribute_layer: AnalysisLayerRef | None = None
    max_features: int = DEFAULT_MAX_FEATURES
    hard_max_features: int = HARD_MAX_FEATURES

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable plan data."""
        return {
            "raw_prompt": self.raw_prompt,
            "operation_type": str(self.operation_type),
            "executable": self.executable,
            "supported_operations": self.supported_operations,
            "blocked_reasons": self.blocked_reasons,
            "warnings": self.warnings,
            "estimated_query_counts": self.estimated_query_counts,
            "recommended_execution_plan": self.recommended_execution_plan,
            "target_layer": self.target_layer.to_dict() if self.target_layer else None,
            "geography_layer": self.geography_layer.to_dict() if self.geography_layer else None,
            "constraint_layer": self.constraint_layer.to_dict() if self.constraint_layer else None,
            "attribute_layer": self.attribute_layer.to_dict() if self.attribute_layer else None,
            "max_features": self.max_features,
            "hard_max_features": self.hard_max_features,
        }


@dataclass
class AnalysisExecutionResult:
    """Result metadata for one local analysis execution."""

    analysis_run_id: str
    raw_prompt: str
    operation_type: AnalysisOperationType
    status: str
    recipe_json: dict[str, Any]
    selected_layer_keys: list[str]
    input_counts: dict[str, Any] = field(default_factory=dict)
    output_count: int = 0
    output_geojson_path: str | None = None
    analysis_receipt: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    blocked_reasons: list[str] = field(default_factory=list)
    output_folder: str | None = None
    derived_layer: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable execution data."""
        return {
            "analysis_run_id": self.analysis_run_id,
            "raw_prompt": self.raw_prompt,
            "operation_type": str(self.operation_type),
            "status": self.status,
            "recipe_json": self.recipe_json,
            "selected_layer_keys": self.selected_layer_keys,
            "input_counts": self.input_counts,
            "output_count": self.output_count,
            "output_geojson_path": self.output_geojson_path,
            "analysis_receipt": self.analysis_receipt,
            "warnings": self.warnings,
            "blocked_reasons": self.blocked_reasons,
            "output_folder": self.output_folder,
            "derived_layer": self.derived_layer,
        }
