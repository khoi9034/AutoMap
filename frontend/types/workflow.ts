import type { MapRecipe } from "@/types/automap";

export type WorkflowStepId =
  | "request"
  | "recipe"
  | "webmap"
  | "review_packet"
  | "preview"
  | "adjustments"
  | "approval"
  | "publish";

export type WorkflowStepStatus = "pending" | "active" | "completed" | "blocked";

export type WorkflowStepDefinition = {
  id: WorkflowStepId;
  label: string;
  href: string;
};

export type WorkflowStepState = WorkflowStepDefinition & {
  status: WorkflowStepStatus;
  reason?: string;
};

export type WorkflowState = {
  rawPrompt: string;
  recipe: MapRecipe | null;
  webmapDraft: Record<string, unknown> | null;
  reviewPacket: Record<string, unknown> | null;
  adjustmentTemplate: Record<string, unknown> | null;
  adjustedPacket: Record<string, unknown> | null;
  approvalTemplate: Record<string, unknown> | null;
  approvedPacket: Record<string, unknown> | null;
  dryRunReceipt: Record<string, unknown> | null;
  portalSmokeTestReceipt: Record<string, unknown> | null;
  activeStep: WorkflowStepId;
  warnings: string[];
  missingData: string[];
  selectedPacketId: string;
  selectedPacketPath: string;
  selectedAdjustedPacketId: string;
  selectedAdjustedPacketPath: string;
  selectedApprovedPacketId: string;
  selectedApprovedPacketPath: string;
  updatedAt: string | null;
};

export type WorkflowToastTone = "default" | "success" | "warning" | "danger";

export type WorkflowToast = {
  tone: WorkflowToastTone;
  message: string;
};
