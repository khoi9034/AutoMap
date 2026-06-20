"use client";

import type { CSSProperties, ReactNode } from "react";

import { MapFrameTitle } from "@/components/map-frame-title";

export type MapFrameMode = "preview" | "adjust" | "print" | "exhibit";

type MapFrameProps = {
  aspectRatio?: string;
  badge?: string;
  children: ReactNode;
  locked?: boolean;
  maxHeight?: string;
  minHeight?: string;
  mode: MapFrameMode;
  subtitle?: string | null;
  title: string;
};

export function MapFrame({
  aspectRatio,
  badge,
  children,
  locked = false,
  maxHeight,
  minHeight,
  mode,
  subtitle,
  title,
}: MapFrameProps) {
  const style = {
    ...(aspectRatio ? { "--map-frame-aspect-ratio": aspectRatio } : {}),
    ...(minHeight ? { "--map-frame-min-height": minHeight } : {}),
    ...(maxHeight ? { "--map-frame-max-height": maxHeight } : {}),
  } as CSSProperties;

  return (
    <section
      className={`enterprise-map-frame map-frame map-frame-${mode} ${locked ? "map-frame-locked" : "map-frame-interactive"}`}
      data-map-frame-mode={mode}
      data-map-locked={locked ? "true" : "false"}
      style={style}
    >
      <MapFrameTitle title={title} subtitle={subtitle} badge={badge} />
      {children}
    </section>
  );
}
