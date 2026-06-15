import type {
  ClarificationAnswerModel,
  ClarificationQuestionModel,
  ClarificationSession,
  MapRecipe,
} from "@/types/automap";

export type WorkflowStepId =
  | "request"
  | "clarify"
  | "recipe"
  | "webmap"
  | "review_packet"
  | "preview"
  | "analysis"
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
  initialRecipe: MapRecipe | null;
  refinedRecipe: MapRecipe | null;
  clarificationSessionId: string;
  clarificationSession: ClarificationSession | null;
  clarificationQuestions: ClarificationQuestionModel[];
  clarificationAnswers: ClarificationAnswerModel[];
  appliedRefinements: Record<string, unknown> | null;
  remainingQuestions: ClarificationQuestionModel[];
  webmapDraft: Record<string, unknown> | null;
  reviewPacket: Record<string, unknown> | null;
  analysisPlan: Record<string, unknown> | null;
  analysisRun: Record<string, unknown> | null;
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
