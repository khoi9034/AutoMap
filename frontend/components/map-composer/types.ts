"use client";

export type ComposerStepId = "request" | "preview" | "adjust" | "export";

export type ComposerStepStatus = "pending" | "active" | "complete" | "blocked";

export type ComposerStepStatuses = Record<ComposerStepId, ComposerStepStatus>;

export type ComposerStepDisabled = Partial<Record<ComposerStepId, boolean>>;

export type ComposerLayerEdit = {
  layer_key: string;
  title: string;
  visibility: boolean;
  opacity: number;
  role?: string;
  definition_expression?: string;
  is_derived?: boolean;
  line_thickness?: number;
  line_style?: "solid" | "dashed";
};
