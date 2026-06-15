import type { WorkflowToast } from "@/types/workflow";

type ToastMessageProps = {
  toast: WorkflowToast | null;
};

export function ToastMessage({ toast }: ToastMessageProps) {
  if (!toast) {
    return null;
  }
  return <div className={`toast toast-${toast.tone}`}>{toast.message}</div>;
}
