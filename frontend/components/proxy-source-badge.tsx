import { StatusChip } from "@/components/status-chip";

type ProxySourceBadgeProps = {
  role?: string;
  status?: string;
  approval?: string;
};

function toneForRole(role?: string, status?: string, approval?: string): "default" | "success" | "warning" | "danger" {
  if (role === "official" || (approval === "approved" && status === "active")) {
    return "success";
  }
  if (role === "proxy" || role === "limited_coverage" || status === "proxy" || approval === "candidate") {
    return "warning";
  }
  if (role === "reference" || status === "reference") {
    return "default";
  }
  if (role === "needs_review" || approval === "needs_review") {
    return "danger";
  }
  return "default";
}

function labelForRole(role?: string, status?: string): string {
  if (role === "official") {
    return "Official";
  }
  if (role === "proxy") {
    return "Proxy";
  }
  if (role === "limited_coverage") {
    return "Limited coverage";
  }
  if (role === "reference") {
    return "Reference";
  }
  if (role === "historical_fallback") {
    return "Historical";
  }
  return role || status || "Review";
}

export function ProxySourceBadge({ role, status, approval }: ProxySourceBadgeProps) {
  return <StatusChip tone={toneForRole(role, status, approval)}>{labelForRole(role, status)}</StatusChip>;
}
