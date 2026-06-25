import type { ComposerMapState, ComposerResponse } from "@/types/automap";
import type { LivePrintOptions } from "@/types/print-options";

export type PrintJobPayload = {
  composer_session_id?: string;
  createdAt: string;
  export_mode: LivePrintOptions["exportMode"];
  jobId: string;
  locked_map_state: ComposerMapState;
  map_snapshot_data_url: string;
  print_options: LivePrintOptions;
  response: ComposerResponse;
};

export function printJobStorageKey(jobId: string): string {
  return `automap-print-job:${jobId}`;
}
