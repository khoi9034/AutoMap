"use client";

import { ComposerMapPreview } from "@/components/composer-map-preview";
import type { ComposerMapState, ComposerResponse, ProximityResult } from "@/types/automap";

export type SharedMapRendererMode = "preview_locked" | "adjust_interactive" | "print_locked" | "exhibit_locked";
export type MapViewCommandType = "reset_generated" | "reset_feature_extent" | "center_origin" | "center_target";
export type MapViewCommand = {
  id: number;
  type: MapViewCommandType;
};

type SharedMapRendererProps = {
  mapState?: ComposerMapState | null;
  response?: ComposerResponse | null;
  packetId?: string;
  mode?: SharedMapRendererMode;
  mapOnly?: boolean;
  showControls?: boolean;
  showLayerPanel?: boolean;
  showMapFurniture?: boolean;
  viewCommand?: MapViewCommand | null;
  onViewStateChange?: (state: Partial<ComposerMapState>) => void;
  onSnapshotReady?: (dataUrl: string) => void;
};

function responseFromMapState(response: ComposerResponse | null | undefined, mapState: ComposerMapState | null | undefined): ComposerResponse | null {
  if (!response && !mapState) return null;
  if (!mapState) return response || null;
  return {
    ...(response || {}),
    composer_session_id: mapState.composer_session_id || response?.composer_session_id,
    raw_prompt: mapState.raw_prompt || response?.raw_prompt,
    prompt: mapState.raw_prompt || response?.prompt,
    request_type: mapState.request_type || response?.request_type,
    map_title: mapState.map_title || response?.map_title,
    map_layout: mapState.preview_config?.map_layout || response?.map_layout,
    preview_config: mapState.preview_config || response?.preview_config,
    proximity_result: (mapState.proximity_summary as ProximityResult | undefined) || response?.proximity_result,
    parcel_context: response?.parcel_context || (mapState.parcel_context as ComposerResponse["parcel_context"]),
    warnings: mapState.warnings || response?.warnings,
    missing_data: mapState.missing_data || response?.missing_data,
    composer_map_state: mapState,
    can_preview: response?.can_preview ?? true,
    draft_only: true,
    published: false,
  };
}

export function SharedMapRenderer({
  mapState,
  response,
  packetId,
  mode = "preview_locked",
  mapOnly = false,
  showControls = false,
  showLayerPanel,
  viewCommand,
  onViewStateChange,
  onSnapshotReady,
}: SharedMapRendererProps) {
  const rendererResponse = responseFromMapState(response, mapState);
  if (!rendererResponse) {
    return (
      <div className="preview-error">
        <strong>Map state unavailable.</strong>
        <p>Generate a composer draft before rendering the map.</p>
      </div>
    );
  }
  return (
    <div className={`shared-map-renderer shared-map-renderer-${mode}`}>
      <ComposerMapPreview
        interactionMode={mode}
        mapOnly={mapOnly}
        onSnapshotReady={onSnapshotReady}
        onViewStateChange={onViewStateChange}
        packetId={packetId}
        response={rendererResponse}
        showLayerPanel={showLayerPanel ?? showControls}
        viewCommand={viewCommand}
      />
    </div>
  );
}
