"""Safe serving helpers for local derived AutoMap GeoJSON outputs."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.geometry_utils import compute_basic_stats, load_geojson_features
from app.ui_models import repo_root


APPROVED_OUTPUT_DIRS = {
    "proximity": Path("outputs/proximity"),
    "parcel_context": Path("outputs/parcel_context"),
    "analysis": Path("outputs/analysis"),
}

PROTECTED_MARKERS = {
    ".env",
    "arcgis_password",
    "arcgis_username",
    "database_url",
    "password",
    "postgres_admin_url",
    "secret",
    "token",
}

local_output_router = APIRouter(prefix="/local-outputs", tags=["local-outputs"])


def _repo_relative(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def _approved_root(output_type: str) -> Path:
    try:
        root = APPROVED_OUTPUT_DIRS[output_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported local output type: {output_type}") from exc
    return (repo_root() / root).resolve()


def _encode_relative_path(path: str | Path) -> str:
    relative = _repo_relative(path)
    encoded = base64.urlsafe_b64encode(relative.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def _decode_file_id(file_id: str) -> str:
    padding = "=" * (-len(file_id) % 4)
    try:
        return base64.urlsafe_b64decode(f"{file_id}{padding}").decode("utf-8")
    except Exception as exc:
        raise ValueError("Invalid local output file id.") from exc


def resolve_local_output_path(output_type: str, file_id: str, *, require_geojson: bool = False) -> Path:
    """Resolve a signed-by-path file id into an approved local output path."""
    root = _approved_root(output_type)
    relative = _decode_file_id(file_id)
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ValueError("Local output ids must be repository-relative.")
    resolved = (repo_root() / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("Local output path is outside approved output folders.") from exc
    if require_geojson and resolved.suffix.lower() != ".geojson":
        raise ValueError("Only GeoJSON files can be served by this route.")
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError("Local output file not found.")
    return resolved


def make_local_output_file_id(path: str | Path, *, output_type: str | None = None) -> str:
    """Return a URL-safe id for an approved local output path."""
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = repo_root() / resolved
    resolved = resolved.resolve()
    if output_type:
        resolved.relative_to(_approved_root(output_type))
    else:
        if not any(_is_relative_to(resolved, _approved_root(kind)) for kind in APPROVED_OUTPUT_DIRS):
            raise ValueError("Path is not in an approved local output folder.")
    return _encode_relative_path(resolved)


def local_geojson_url(path: str | Path, *, output_type: str) -> str:
    """Build the safe API URL for a local derived GeoJSON output."""
    return f"/api/local-outputs/geojson/{output_type}/{make_local_output_file_id(path, output_type=output_type)}"


def local_output_metadata_url(path: str | Path, *, output_type: str) -> str:
    """Build the safe API URL for local derived output metadata."""
    return f"/api/local-outputs/metadata/{output_type}/{make_local_output_file_id(path, output_type=output_type)}"


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _contains_protected_marker(value: Any) -> str | None:
    serialized = json.dumps(value, default=str).lower()
    for marker in sorted(PROTECTED_MARKERS):
        if marker in serialized:
            return marker
    return None


def _geojson_metadata(path: Path, output_type: str, file_id: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    marker = _contains_protected_marker(data)
    if marker:
        raise ValueError(f"Local output contains protected marker: {marker}")
    features = load_geojson_features(data)
    stats = compute_basic_stats(features)
    return {
        "output_type": output_type,
        "file_id": file_id,
        "file_name": path.name,
        "path": _repo_relative(path),
        "feature_count": stats.get("feature_count"),
        "geometry_types": stats.get("geometry_types") or {},
        "bounds": stats.get("bounds"),
        "draft_only": True,
        "published": False,
    }


@local_output_router.get("/geojson/{output_type}/{file_id}")
def local_output_geojson(output_type: str, file_id: str) -> Response:
    """Serve approved local GeoJSON outputs without exposing arbitrary files."""
    try:
        path = resolve_local_output_path(output_type, file_id, require_geojson=True)
        data = json.loads(path.read_text(encoding="utf-8"))
        marker = _contains_protected_marker(data)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if marker:
        raise HTTPException(status_code=404, detail="Local GeoJSON output is not safe to serve.")
    return Response(content=json.dumps(data, default=str), media_type="application/geo+json")


@local_output_router.get("/metadata/{output_type}/{file_id}")
def local_output_metadata(output_type: str, file_id: str) -> dict[str, Any]:
    """Return safe metadata for an approved local derived output."""
    try:
        path = resolve_local_output_path(output_type, file_id, require_geojson=True)
        return _geojson_metadata(path, output_type, file_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
