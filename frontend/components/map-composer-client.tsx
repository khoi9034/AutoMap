"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AdjustStep } from "@/components/map-composer/adjust-step";
import { ExportStep } from "@/components/map-composer/export-step";
import { MapComposerShell } from "@/components/map-composer/map-composer-shell";
import { PreviewStep } from "@/components/map-composer/preview-step";
import { RequestStep } from "@/components/map-composer/request-step";
import type { ComposerLayerEdit, ComposerStepDisabled, ComposerStepId, ComposerStepStatuses } from "@/components/map-composer/types";
import {
  composerDisplaySubtitle,
  composerDisplayTitle,
  defaultComposerPrompt,
  layerEditsFromResponse,
  packetIdForPreview,
} from "@/components/map-composer/utils";
import { adjustComposerDraft, exportComposerDraft, exportComposerExhibit, generateComposerDraft, getApiHealth, refineComposerRoute, saveComposerMapState } from "@/lib/api";
import { buildComposerExportPayload } from "@/lib/composer-map-state";
import { staticDemoComposerResponse } from "@/lib/static-demo";
import { mergeWorkflowState } from "@/lib/workflow-store";
import type { ComposerAdjustPayload, ComposerMapState, ComposerResponse, ExhibitPackage, ReportSectionConfig } from "@/types/automap";
import {
  DEFAULT_LIVE_PRINT_OPTIONS,
  backendExportOptionsToPrintOptions,
  printOptionsForMode,
  printOptionsToReportConfig,
  type LivePrintOptions,
} from "@/types/print-options";
import type { WorkflowToast } from "@/types/workflow";

type ComposerLoadingState = "generate" | "adjust" | "export" | "exhibit" | "route-refine" | null;

const defaultReportConfig: ReportSectionConfig = {
  include_map_summary: true,
  include_layer_table: false,
  include_warnings: true,
  include_source_notes: false,
  include_proximity_summary: true,
  include_parcel_summary: false,
  include_statistics: false,
  include_permit_summary: false,
  include_planning_summary: false,
  include_development_proxy_summary: false,
  include_table_preview: false,
  include_table_export_summary: false,
};

function timeoutComposerRequest(): Promise<never> {
  return new Promise((_, reject) => {
    setTimeout(() => reject(new Error("public_demo_timeout")), 90000);
  });
}

function composerStepStatuses(
  activeStep: ComposerStepId,
  response: ComposerResponse | null,
  exported: boolean,
): ComposerStepStatuses {
  const previewBlocked = Boolean(response?.preview_blockers?.length);
  const previewReady = Boolean(response?.can_preview);
  const adjusted = Boolean(response?.adjusted_packet_id || response?.applied_adjustments);
  return {
    request: activeStep === "request" ? "active" : response ? "complete" : "pending",
    preview: previewBlocked ? "blocked" : activeStep === "preview" ? "active" : previewReady ? "complete" : "pending",
    adjust: activeStep === "adjust" ? "active" : adjusted ? "complete" : previewReady ? "pending" : "pending",
    export: activeStep === "export" ? "active" : exported ? "complete" : previewReady ? "pending" : "pending",
  };
}

export function MapComposerClient() {
  const searchParams = useSearchParams();
  const [prompt, setPrompt] = useState(searchParams.get("prompt") || defaultComposerPrompt);
  const [response, setResponse] = useState<ComposerResponse | null>(null);
  const [layers, setLayers] = useState<ComposerLayerEdit[]>([]);
  const [mapTitle, setMapTitle] = useState("");
  const [mapSubtitle, setMapSubtitle] = useState("");
  const [notes, setNotes] = useState("");
  const [reportConfig, setReportConfig] = useState<ReportSectionConfig>(defaultReportConfig);
  const [printOptions, setPrintOptionsState] = useState<LivePrintOptions>(DEFAULT_LIVE_PRINT_OPTIONS);
  const [activeMapViewState, setActiveMapViewState] = useState<Partial<ComposerMapState> | null>(null);
  const [exhibitPackage, setExhibitPackage] = useState<ExhibitPackage | null>(null);
  const [activeStep, setActiveStep] = useState<ComposerStepId>("request");
  const [loading, setLoading] = useState<ComposerLoadingState>(null);
  const [error, setError] = useState<string | null>(null);
  const [generateElapsedSeconds, setGenerateElapsedSeconds] = useState(0);
  const [showStaticDemoFallback, setShowStaticDemoFallback] = useState(false);
  const [composerProgressMessage, setComposerProgressMessage] = useState<string | null>(null);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  const previewPacketId = useMemo(() => packetIdForPreview(response), [response]);
  const previewReady = Boolean(response?.can_preview && previewPacketId);
  const exported = Boolean(response?.export || response?.exhibit || exhibitPackage);
  const statuses = composerStepStatuses(activeStep, response, exported);
  const disabled: ComposerStepDisabled = {
    preview: !response,
    adjust: !previewReady,
    export: !previewReady,
  };

  useEffect(() => {
    if (loading !== "generate") {
      setGenerateElapsedSeconds(0);
      return;
    }
    const startedAt = Date.now();
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      setGenerateElapsedSeconds(elapsed);
      if (elapsed >= 45) setShowStaticDemoFallback(true);
    }, 1000);
    return () => clearInterval(timer);
  }, [loading]);

  function resetAdjustments(nextResponse = response) {
    if (!nextResponse) return;
    setLayers(layerEditsFromResponse(nextResponse));
    setMapTitle(composerDisplayTitle(nextResponse));
    setMapSubtitle(composerDisplaySubtitle(nextResponse));
    setNotes("");
    setActiveMapViewState(null);
  }

  function currentComposerPayload(): ComposerAdjustPayload | null {
    if (!response?.composer_session_id) return null;
    return buildComposerExportPayload({
      response,
      layers,
      mapTitle,
      mapSubtitle,
      notes,
      reportConfig,
      exportMode: printOptions.exportMode,
      printOptions,
      activeMapViewState,
    });
  }

  function currentLockedMapState(): ComposerMapState | null {
    return currentComposerPayload()?.map_state || response?.composer_map_state || null;
  }

  const handleMapViewStateChange = useCallback((state: Partial<ComposerMapState>) => {
    setActiveMapViewState(state);
  }, []);

  function setPrintOptions(nextOptions: LivePrintOptions) {
    const normalized = printOptionsForMode(nextOptions.exportMode, nextOptions);
    setPrintOptionsState(normalized);
    setReportConfig(printOptionsToReportConfig(normalized));
  }

  function changeStep(step: ComposerStepId) {
    if (disabled[step]) return;
    setActiveStep(step);
  }

  async function generateDraft() {
    setLoading("generate");
    setError(null);
    setShowStaticDemoFallback(false);
    setComposerProgressMessage("Starting live demo...");
    try {
      try {
        await getApiHealth();
      } catch {
        setComposerProgressMessage("Live backend is warming up.");
      }
      const attemptGenerate = async () => {
        setComposerProgressMessage("Matching address, finding nearby fire stations, and calculating road route...");
        return generateComposerDraft(prompt);
      };
      const liveRequest = async () => {
        try {
          return await attemptGenerate();
        } catch (firstError) {
          setComposerProgressMessage("Still working on the live result. Retrying once...");
          await new Promise((resolve) => setTimeout(resolve, 10000));
          try {
            return await attemptGenerate();
          } catch {
            throw firstError;
          }
        }
      };
      const result = await Promise.race([liveRequest(), timeoutComposerRequest()]);
      setResponse(result);
      setExhibitPackage(null);
      setLayers(layerEditsFromResponse(result));
      setMapTitle(composerDisplayTitle(result));
      setMapSubtitle(composerDisplaySubtitle(result));
      setNotes("");
      setActiveMapViewState(null);
      const nextPrintOptions = backendExportOptionsToPrintOptions(
        result.composer_map_state?.export_options,
        result.composer_map_state?.report_section_config || defaultReportConfig,
      );
      setPrintOptions(nextPrintOptions);
      setActiveStep("preview");
      mergeWorkflowState({
        rawPrompt: prompt,
        recipe: result.recipe,
        reviewPacket: result.packet_path ? { packet_path: result.packet_path, packet_id: result.packet_id } : undefined,
        selectedPacketPath: result.packet_path || undefined,
        selectedPacketId: result.packet_id || undefined,
        warnings: result.warnings || [],
        missingData: result.missing_data || [],
        activeStep: result.can_preview ? "preview" : "recipe",
      });
      setToast({
        tone: result.can_preview ? "success" : "warning",
        message: result.can_preview
          ? "Draft map and preview are ready."
          : "Draft created, but preview is blocked until the address or parcel matches.",
      });
    } catch {
      setShowStaticDemoFallback(true);
      setError(
        "The live backend is waking up or the composer request is taking too long. You can retry the live demo, view the static demo, or open the project summary.",
      );
    } finally {
      setLoading(null);
      setComposerProgressMessage(null);
    }
  }

  function viewStaticDemoResult() {
    setResponse(staticDemoComposerResponse);
    setExhibitPackage(null);
    setLayers(layerEditsFromResponse(staticDemoComposerResponse));
    setMapTitle(composerDisplayTitle(staticDemoComposerResponse));
    setMapSubtitle(composerDisplaySubtitle(staticDemoComposerResponse));
    setNotes("Static demo fallback. Live backend unavailable.");
    setActiveMapViewState(null);
    setError(null);
    setShowStaticDemoFallback(true);
    setActiveStep("request");
    setToast({ tone: "warning", message: "Showing a static demo fallback. Retry the live request when the backend is awake." });
  }

  async function applyAdjustments() {
    if (!response?.composer_session_id) return;
    setLoading("adjust");
    setError(null);
    try {
      const payload = currentComposerPayload();
      if (!payload) return;
      const result = await adjustComposerDraft(payload);
      setResponse(result);
      setExhibitPackage(null);
      setLayers(layerEditsFromResponse(result));
      setMapTitle(composerDisplayTitle(result));
      setMapSubtitle(composerDisplaySubtitle(result));
      setActiveMapViewState(null);
      mergeWorkflowState({
        rawPrompt: prompt,
        recipe: result.recipe,
        adjustedPacket: result.adjusted_packet_path ? { adjusted_packet_path: result.adjusted_packet_path } : undefined,
        selectedAdjustedPacketPath: result.adjusted_packet_path || undefined,
        selectedAdjustedPacketId: result.adjusted_packet_id || undefined,
        activeStep: "adjustments",
      });
      setToast({ tone: "success", message: "Adjustments applied and adjusted preview is ready." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Adjustment failed.");
    } finally {
      setLoading(null);
    }
  }

  async function tryRouteRefinement() {
    if (!response?.composer_session_id) return;
    setLoading("route-refine");
    setError(null);
    try {
      const result = await refineComposerRoute(response.composer_session_id);
      setResponse(result);
      setLayers(layerEditsFromResponse(result));
      setMapTitle(composerDisplayTitle(result));
      setMapSubtitle(composerDisplaySubtitle(result));
      setToast({ tone: "success", message: "Route refinement finished. The straight-line reference remains available if refinement was not possible." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Route refinement failed.");
    } finally {
      setLoading(null);
    }
  }

  async function generateReportExport() {
    if (!response?.composer_session_id) return;
    setLoading("export");
    setError(null);
    try {
      const payload = currentComposerPayload();
      if (!payload) return;
      const result = await exportComposerDraft(payload);
      setResponse(result);
      setToast({ tone: "success", message: "Draft review report/export created locally." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Report/export generation failed.");
    } finally {
      setLoading(null);
    }
  }

  async function openPrintLayout() {
    if (!response?.composer_session_id) return;
    setLoading("export");
    setError(null);
    try {
      const payload = currentComposerPayload();
      if (!payload) return;
      const saved = await saveComposerMapState(payload);
      setResponse({ ...response, composer_map_state: saved.composer_map_state || response.composer_map_state });
      setExhibitPackage(null);
      window.open(`/map-composer/${response.composer_session_id}/print`, "_blank", "noopener,noreferrer");
      setToast({ tone: "success", message: "Current map state saved for the print layout." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Print layout preparation failed.");
    } finally {
      setLoading(null);
    }
  }

  async function generateExhibit() {
    if (!response?.composer_session_id) return;
    setLoading("exhibit");
    setError(null);
    try {
      const payload = currentComposerPayload();
      if (!payload) return;
      const exhibit = await exportComposerExhibit(payload);
      setExhibitPackage(exhibit);
      setResponse({ ...response, exhibit });
      setToast({ tone: "success", message: "County exhibit package generated under outputs/exhibits." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Exhibit package generation failed.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <MapComposerShell activeStep={activeStep} disabled={disabled} onStepChange={changeStep} statuses={statuses}>
      {activeStep === "request" ? (
        <RequestStep
          elapsedSeconds={generateElapsedSeconds}
          error={error}
          loading={loading === "generate"}
          onGenerate={generateDraft}
          onUseStaticDemo={viewStaticDemoResult}
          progressMessage={composerProgressMessage}
          prompt={prompt}
          setPrompt={setPrompt}
          showStaticDemoFallback={showStaticDemoFallback}
          staticDemoResponse={response?.composer_session_id === staticDemoComposerResponse.composer_session_id ? staticDemoComposerResponse : null}
          toast={toast}
        />
      ) : null}
      {activeStep === "preview" ? (
        <PreviewStep
          loading={loading === "generate"}
          onGoToAdjust={() => setActiveStep("adjust")}
          onGoToExport={() => setActiveStep("export")}
          onGoToRequest={() => setActiveStep("request")}
          onRegenerate={generateDraft}
          onRouteRefine={tryRouteRefinement}
          previewPacketId={previewPacketId}
          response={response}
          routeRefineLoading={loading === "route-refine"}
        />
      ) : null}
      {activeStep === "adjust" ? (
        <AdjustStep
          layers={layers}
          loading={loading === "adjust"}
          mapSubtitle={mapSubtitle}
          mapTitle={mapTitle}
          notes={notes}
          onApply={applyAdjustments}
          onGoToPreview={() => setActiveStep("preview")}
          onMapViewStateChange={handleMapViewStateChange}
          onReset={() => resetAdjustments()}
          previewPacketId={previewPacketId}
          response={response}
          setLayers={setLayers}
          setMapSubtitle={setMapSubtitle}
          setMapTitle={setMapTitle}
          setNotes={setNotes}
        />
      ) : null}
      {activeStep === "export" ? (
        <ExportStep
          exhibitPackage={exhibitPackage}
          loadingExhibit={loading === "exhibit"}
          loadingReport={loading === "export"}
          onGenerateExhibit={generateExhibit}
          onGenerateReport={generateReportExport}
          onGoToAdjust={() => setActiveStep("adjust")}
          onOpenPrintLayout={openPrintLayout}
          previewPacketId={previewPacketId}
          response={response}
          lockedMapState={currentLockedMapState()}
          printOptions={printOptions}
          setPrintOptions={setPrintOptions}
        />
      ) : null}
    </MapComposerShell>
  );
}
