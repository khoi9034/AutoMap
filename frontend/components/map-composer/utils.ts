"use client";

import { API_BASE_URL } from "@/lib/api";
import { isRoadRouteMode } from "@/lib/map-symbols";
import { packetIdFromPath } from "@/lib/workflow-store";
import type { ComposerResponse, DerivedOverlay, PreviewLayer } from "@/types/automap";

import type { ComposerLayerEdit } from "./types";

export const defaultComposerPrompt = "make a map of my address 793 bartram ave and include nearest line to the nearest fire station";

export function localFileUrl(path?: string | null): string {
  return path ? `${API_BASE_URL}/local-file?path=${encodeURIComponent(path)}` : "#";
}

export function actionLabel(action?: string): string {
  if (action === "correct_address") return "Correct address";
  if (action === "correct_parcel_identifier") return "Correct parcel/PIN/address";
  if (action === "context_preview") return "Context map available";
  if (action === "preview_map") return "Preview Map";
  if (action === "preview_adjusted_map") return "Preview Adjusted Map";
  if (action === "print_or_export") return "Print / Export";
  return "Review Draft";
}

export type ComposerResultState = "ready" | "partial" | "blocked" | "no_matches" | "unsupported";

function hasMapPayload(response: ComposerResponse | null): boolean {
  const preview = response?.preview_config || response?.composer_map_state?.preview_config;
  return Boolean(
    packetIdForPreview(response) ||
      preview?.derived_overlays?.length ||
      preview?.context_layers?.length ||
      preview?.operational_layers?.length ||
      preview?.focus_extent ||
      preview?.initial_extent ||
      response?.proximity_result?.derived_overlays?.length,
  );
}

export function composerResultState(response: ComposerResponse | null): ComposerResultState {
  const explicit = String(response?.result_state || "").toLowerCase();
  if (["ready", "partial", "blocked", "no_matches", "unsupported"].includes(explicit)) return explicit as ComposerResultState;
  const screening = response?.floodplain_screening;
  if (screening) {
    const status = String(screening.status || response?.analysis_status || response?.preview_quality || "");
    const affectedCount =
      typeof response?.affected_feature_count === "number"
        ? response.affected_feature_count
        : typeof screening.affected_feature_count === "number"
          ? screening.affected_feature_count
          : 0;
    if (status === "completed" && affectedCount > 0) return "ready";
    if (status === "no_matches" || response?.analysis_status === "no_matching_parcels") return "no_matches";
    return "partial";
  }
  if (response?.origin_match_status === "unsupported_area" || response?.parcel_context?.match_status === "unsupported_area") return "unsupported";
  if (response?.preview_blockers?.length) return "blocked";
  return response?.can_preview ? "ready" : "blocked";
}

export function isAddressFocused(response: ComposerResponse): boolean {
  const blockerText = (response.preview_blockers || []).join(" ").toLowerCase();
  return (
    response.origin_type === "address" ||
    response.request_type === "address_context" ||
    blockerText.includes("address not matched") ||
    response.recipe?.origin_context?.origin_type === "address" ||
    response.parcel_context?.origin_type === "address" ||
    response.parcel_context?.input_type === "address"
  );
}

export function identifierText(value: unknown): string {
  if (!value || typeof value !== "object") return String(value || "");
  const item = value as {
    address?: string;
    city?: string;
    display_address?: string;
    identifier_type?: string;
    normalized_value?: string;
    parcel_id?: string;
    pin?: string;
    pin14?: string;
    value?: string;
    zip?: string;
  };
  const address = item.display_address || item.address || item.value || item.normalized_value || item.identifier_type || "";
  const locality = [item.city, item.zip].filter(Boolean).join(" ");
  const parcel = item.pin14 || item.pin || item.parcel_id;
  return [address, locality, parcel ? `Parcel/PIN ${parcel}` : ""].filter(Boolean).join(" - ") || JSON.stringify(item);
}

function derivedRouteStyle(overlay: DerivedOverlay): Pick<ComposerLayerEdit, "line_style" | "line_thickness"> {
  const blob = `${overlay.role || ""} ${overlay.geometry_role || ""} ${overlay.symbol_key || ""} ${overlay.route_mode || ""}`.toLowerCase();
  if (!blob.includes("route") && !blob.includes("distance") && !blob.includes("line")) return {};
  const dashed = !isRoadRouteMode(overlay.route_mode) && (blob.includes("straight") || blob.includes("fallback") || overlay.route_mode === "straight_line_reference");
  return {
    line_style: dashed ? "dashed" : "solid",
    line_thickness: dashed ? 2.4 : 3.2,
  };
}

export function layerEditsFromResponse(response: ComposerResponse): ComposerLayerEdit[] {
  const previewLayers = [...(response.preview_config?.operational_layers || []), ...(response.preview_config?.context_layers || [])];
  const derivedOverlays = response.preview_config?.derived_overlays || response.proximity_result?.derived_overlays || [];
  const derivedEdits: ComposerLayerEdit[] = derivedOverlays.map((overlay, index) => ({
    layer_key: overlay.id || `derived_overlay_${index}`,
    title: overlay.title || overlay.id || `Derived overlay ${index + 1}`,
    visibility: overlay.visible !== false,
    opacity: 1,
    role: overlay.role,
    definition_expression: "",
    is_derived: true,
    ...derivedRouteStyle(overlay),
  }));
  if (previewLayers.length) {
    const contextEdits = previewLayers
      .filter((layer: PreviewLayer) => !layer.derived_local_analysis && !layer.local_output)
      .map((layer: PreviewLayer, index) => ({
        layer_key: layer.layer_key || layer.id || `layer_${index}`,
        title: layer.title || layer.layer_key || `Layer ${index + 1}`,
        visibility: layer.visibility !== false,
        opacity: typeof layer.opacity === "number" ? layer.opacity : 1,
        role: layer.role,
        definition_expression: layer.definition_expression || "",
      }));
    return [...derivedEdits, ...contextEdits];
  }
  return [
    ...derivedEdits,
    ...(response.selected_layers || []).map((layer, index) => ({
      layer_key: layer.layer_key || `layer_${index}`,
      title: layer.layer_name || layer.layer_key || `Layer ${index + 1}`,
      visibility: true,
      opacity: layer.category === "flood" ? 0.35 : layer.category === "zoning" ? 0.65 : 0.85,
      role: layer.role,
      definition_expression: "",
    })),
  ];
}

export function packetIdForPreview(response: ComposerResponse | null): string {
  if (!response?.can_preview) return "";
  return response.adjusted_packet_id || response.packet_id || response.review_packet_id || packetIdFromPath(response.packet_path || "");
}

export function hasPreviewMapPayload(response: ComposerResponse | null): response is ComposerResponse {
  return Boolean(response?.can_preview && composerResultState(response) === "ready" && hasMapPayload(response));
}

export function hasContextMapPayload(response: ComposerResponse | null): response is ComposerResponse {
  return hasMapPayload(response);
}

export function isPartialContextMap(response: ComposerResponse | null): response is ComposerResponse {
  return Boolean(response && composerResultState(response) === "partial" && response.context_map_available !== false && hasContextMapPayload(response));
}

export function canShowComposerMap(response: ComposerResponse | null): response is ComposerResponse {
  return Boolean(hasPreviewMapPayload(response) || isPartialContextMap(response) || (composerResultState(response) === "no_matches" && hasContextMapPayload(response)));
}

export function composerDisplayTitle(response: ComposerResponse | null): string {
  return response?.map_layout?.title || response?.map_title || response?.recipe?.map_title || "AutoMap Draft Map";
}

export function composerDisplaySubtitle(response: ComposerResponse | null): string {
  return response?.map_layout?.subtitle || "Draft preview only. Not an official map.";
}

export function isRouteLayer(layer: ComposerLayerEdit): boolean {
  const blob = `${layer.layer_key} ${layer.title} ${layer.role || ""}`.toLowerCase();
  return blob.includes("route") || blob.includes("distance") || blob.includes("line");
}
