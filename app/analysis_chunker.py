"""Chunk helpers for safe bounded spatial analysis."""

from __future__ import annotations

from typing import Any

from app.analysis_safety import enforce_max_chunks, enforce_max_features_per_chunk


def split_extent_into_tiles(extent: dict[str, Any], max_tiles: int = 25) -> list[dict[str, Any]]:
    """Split an Esri extent into a square-ish grid of Esri envelope tiles."""
    if not extent:
        return []
    xmin = float(extent["xmin"])
    ymin = float(extent["ymin"])
    xmax = float(extent["xmax"])
    ymax = float(extent["ymax"])
    if xmax <= xmin or ymax <= ymin:
        return []
    grid_size = 1
    while grid_size * grid_size < max_tiles:
        grid_size += 1
    tile_count = min(grid_size * grid_size, max_tiles)
    columns = grid_size
    rows = max(1, (tile_count + columns - 1) // columns)
    width = (xmax - xmin) / columns
    height = (ymax - ymin) / rows
    tiles: list[dict[str, Any]] = []
    for row in range(rows):
        for column in range(columns):
            if len(tiles) >= max_tiles:
                break
            tile = {
                "xmin": xmin + (column * width),
                "ymin": ymin + (row * height),
                "xmax": xmin + ((column + 1) * width),
                "ymax": ymin + ((row + 1) * height),
                "spatialReference": extent.get("spatialReference") or {"wkid": 4326},
            }
            tiles.append(tile)
    return tiles


def chunk_constraint_features(
    constraint_features: list[dict[str, Any]],
    max_features_per_chunk: int = 25,
) -> list[list[dict[str, Any]]]:
    """Group constraint features into small deterministic chunks."""
    if max_features_per_chunk < 1:
        raise ValueError("max_features_per_chunk must be positive.")
    return [
        constraint_features[index:index + max_features_per_chunk]
        for index in range(0, len(constraint_features), max_features_per_chunk)
    ]


def build_chunk_receipts(chunks: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Create receipt metadata for analysis chunks."""
    return [
        {
            "chunk_index": index + 1,
            "constraint_feature_count": len(chunk),
            "candidate_object_id_count": 0,
            "deduplicated_candidate_count": 0,
            "request_methods": [],
            "status": "planned",
        }
        for index, chunk in enumerate(chunks)
    ]


def merge_chunk_results(chunk_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge object IDs from chunk results while preserving first-seen order."""
    seen: set[str] = set()
    merged_ids: list[Any] = []
    for result in chunk_results:
        for object_id in result.get("object_ids") or []:
            marker = str(object_id)
            if marker in seen:
                continue
            seen.add(marker)
            merged_ids.append(object_id)
    return {
        "object_ids": merged_ids,
        "object_id_count": len(merged_ids),
        "raw_object_id_count": sum(len(result.get("object_ids") or []) for result in chunk_results),
    }


def enforce_chunk_limits(
    chunks: list[list[dict[str, Any]]],
    *,
    max_chunks: int,
    max_features_per_chunk: int,
) -> list[dict[str, Any]]:
    """Return safety checks for planned chunks."""
    checks = [enforce_max_chunks(len(chunks), max_chunks)]
    for index, chunk in enumerate(chunks):
        checks.append(
            enforce_max_features_per_chunk(
                len(chunk),
                max_features_per_chunk,
                label=f"constraint features in chunk {index + 1}",
            )
        )
    return checks
