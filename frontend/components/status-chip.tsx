import type { ReactNode } from "react";

type StatusChipProps = {
  children: ReactNode;
  tone?: "default" | "success" | "warning" | "danger";
};

export function StatusChip({ children, tone = "default" }: StatusChipProps) {
  return <span className={`chip chip-${tone}`}>{children}</span>;
}
