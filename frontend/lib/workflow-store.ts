import type {
  WorkflowState,
  WorkflowStepDefinition,
  WorkflowStepId,
  WorkflowStepState,
} from "@/types/workflow";

export const WORKFLOW_STORAGE_KEY = "automap:workflow:v1.5";
export const WORKFLOW_EVENT = "automap:workflow-updated";

export type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export const workflowSteps: WorkflowStepDefinition[] = [
  { id: "request", label: "Request", href: "/map-request" },
  { id: "clarify", label: "Clarify", href: "/clarify" },
  { id: "recipe", label: "Recipe", href: "/recipe-review" },
  { id: "webmap", label: "WebMap Draft", href: "/recipe-review" },
  { id: "review_packet", label: "Review Packet", href: "/recipe-review" },
  { id: "preview", label: "Preview", href: "/map-preview" },
  { id: "adjustments", label: "Adjustments", href: "/adjustments" },
  { id: "approval", label: "Approval", href: "/approval" },
  { id: "publish", label: "Dry-Run Publish", href: "/publish-center" },
];

const PROTECTED_MARKERS = [
  ".env",
  "arcgis_password",
  "arcgis_username",
  "cfs_dev",
  "database_url",
  "password",
  "postgres_admin_url",
  "secret",
  "token",
];

function hasProtectedMarker(value: string): boolean {
  const lowered = value.toLowerCase();
  return PROTECTED_MARKERS.some((marker) => lowered.includes(marker));
}

function sanitizeWorkflowValue<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeWorkflowValue(item)) as T;
  }
  if (value && typeof value === "object") {
    const safe: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value)) {
      if (!hasProtectedMarker(key)) {
        safe[key] = sanitizeWorkflowValue(item);
      }
    }
    return safe as T;
  }
  if (typeof value === "string" && hasProtectedMarker(value)) {
    return "[redacted]" as T;
  }
  return value;
}

export function createInitialWorkflowState(): WorkflowState {
  return {
    rawPrompt: "",
    recipe: null,
    initialRecipe: null,
    refinedRecipe: null,
    clarificationSessionId: "",
    clarificationSession: null,
    clarificationQuestions: [],
    clarificationAnswers: [],
    appliedRefinements: null,
    remainingQuestions: [],
    webmapDraft: null,
    reviewPacket: null,
    adjustmentTemplate: null,
    adjustedPacket: null,
    approvalTemplate: null,
    approvedPacket: null,
    dryRunReceipt: null,
    portalSmokeTestReceipt: null,
    activeStep: "request",
    warnings: [],
    missingData: [],
    selectedPacketId: "",
    selectedPacketPath: "",
    selectedAdjustedPacketId: "",
    selectedAdjustedPacketPath: "",
    selectedApprovedPacketId: "",
    selectedApprovedPacketPath: "",
    updatedAt: null,
  };
}

function browserStorage(): StorageLike | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function notifyWorkflowUpdated(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(WORKFLOW_EVENT));
  }
}

export function loadWorkflowState(storage: StorageLike | null = browserStorage()): WorkflowState {
  const fallback = createInitialWorkflowState();
  if (!storage) {
    return fallback;
  }
  const raw = storage.getItem(WORKFLOW_STORAGE_KEY);
  if (!raw) {
    return fallback;
  }
  try {
    const parsed = JSON.parse(raw) as Partial<WorkflowState>;
    return { ...fallback, ...sanitizeWorkflowValue(parsed) };
  } catch {
    return fallback;
  }
}

export function saveWorkflowState(
  state: WorkflowState,
  storage: StorageLike | null = browserStorage(),
): WorkflowState {
  const safeState = sanitizeWorkflowValue({
    ...state,
    updatedAt: new Date().toISOString(),
  }) as WorkflowState;
  if (storage) {
    storage.setItem(WORKFLOW_STORAGE_KEY, JSON.stringify(safeState));
  }
  notifyWorkflowUpdated();
  return safeState;
}

export function mergeWorkflowState(
  patch: Partial<WorkflowState>,
  storage: StorageLike | null = browserStorage(),
): WorkflowState {
  return saveWorkflowState({ ...loadWorkflowState(storage), ...patch }, storage);
}

export function clearWorkflowState(storage: StorageLike | null = browserStorage()): WorkflowState {
  if (storage) {
    storage.removeItem(WORKFLOW_STORAGE_KEY);
  }
  const reset = createInitialWorkflowState();
  notifyWorkflowUpdated();
  return reset;
}

export function packetIdFromPath(value: unknown): string {
  if (typeof value !== "string" || !value.trim()) {
    return "";
  }
  const parts = value.split(/[\\/]/).filter(Boolean);
  return parts.at(-1) || value;
}

export function stringField(value: Record<string, unknown> | null | undefined, keys: string[]): string {
  if (!value) {
    return "";
  }
  for (const key of keys) {
    const candidate = value[key];
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate;
    }
  }
  return "";
}

export function workflowWarningsFromRecipe(recipe: WorkflowState["recipe"]): string[] {
  return (recipe?.review_reasons || []).map((item) => String(item));
}

export function workflowMissingDataFromRecipe(recipe: WorkflowState["recipe"]): string[] {
  return (recipe?.missing_data_needed || []).map((item) => String(item));
}

function approvalReceipt(state: WorkflowState): Record<string, unknown> {
  const approved = state.approvedPacket || {};
  const receipt = approved.approval_receipt;
  return receipt && typeof receipt === "object" ? (receipt as Record<string, unknown>) : {};
}

function adjustedWarnings(state: WorkflowState): Record<string, unknown> {
  const adjusted = state.adjustedPacket || {};
  const warnings = adjusted.adjusted_warnings;
  return warnings && typeof warnings === "object" ? (warnings as Record<string, unknown>) : {};
}

function blockedReasonForStep(step: WorkflowStepId, state: WorkflowState): string | undefined {
  if (step === "review_packet" && state.recipe && state.missingData.length && !state.reviewPacket) {
    return "Missing data requires review before packet creation.";
  }
  if (step === "recipe" && state.clarificationQuestions.length && !state.refinedRecipe && state.activeStep === "clarify") {
    return "Clarifying questions can improve this recipe.";
  }
  if (step === "approval" && state.adjustedPacket && adjustedWarnings(state).publish_ready === false) {
    return "Adjusted packet publish_ready is false.";
  }
  if (step === "publish") {
    const receipt = approvalReceipt(state);
    if (state.approvedPacket && receipt.final_publish_ready === false) {
      return "Approved packet final_publish_ready is false.";
    }
    if (!state.approvedPacket && state.adjustedPacket) {
      return "Reviewer approval is required before dry-run publishing.";
    }
  }
  return undefined;
}

function isStepCompleted(step: WorkflowStepId, state: WorkflowState): boolean {
  if (step === "request") {
    return Boolean(state.rawPrompt);
  }
  if (step === "clarify") {
    return Boolean(state.clarificationSessionId || state.refinedRecipe);
  }
  if (step === "recipe") {
    return Boolean(state.recipe || state.refinedRecipe);
  }
  if (step === "webmap") {
    return Boolean(state.webmapDraft);
  }
  if (step === "review_packet") {
    return Boolean(state.reviewPacket || state.selectedPacketId || state.selectedPacketPath);
  }
  if (step === "preview") {
    return Boolean(state.selectedPacketId || state.selectedAdjustedPacketId || state.selectedApprovedPacketId);
  }
  if (step === "adjustments") {
    return Boolean(state.adjustedPacket || state.selectedAdjustedPacketId || state.selectedAdjustedPacketPath);
  }
  if (step === "approval") {
    return Boolean(state.approvedPacket || state.selectedApprovedPacketId || state.selectedApprovedPacketPath);
  }
  if (step === "publish") {
    return Boolean(state.dryRunReceipt || state.portalSmokeTestReceipt);
  }
  return false;
}

export function getWorkflowStepStates(state: WorkflowState): WorkflowStepState[] {
  return workflowSteps.map((step) => {
    const reason = blockedReasonForStep(step.id, state);
    if (reason) {
      return { ...step, status: "blocked", reason };
    }
    if (state.activeStep === step.id) {
      return { ...step, status: "active" };
    }
    if (isStepCompleted(step.id, state)) {
      return { ...step, status: "completed" };
    }
    return { ...step, status: "pending" };
  });
}

export function primaryReviewPacketPath(state: WorkflowState): string {
  return state.selectedPacketPath || stringField(state.reviewPacket, ["packet_path"]);
}

export function primaryAdjustedPacketPath(state: WorkflowState): string {
  return state.selectedAdjustedPacketPath || stringField(state.adjustedPacket, ["adjusted_path", "adjusted_packet_path"]);
}

export function primaryApprovedPacketPath(state: WorkflowState): string {
  return state.selectedApprovedPacketPath || stringField(state.approvedPacket, ["approved_path", "approved_packet_path"]);
}
