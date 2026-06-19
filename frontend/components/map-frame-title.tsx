"use client";

type MapFrameTitleProps = {
  title: string;
  subtitle?: string | null;
  badge?: string;
};

export function MapFrameTitle({ title, subtitle, badge }: MapFrameTitleProps) {
  return (
    <div className="map-frame-title" data-testid="map-frame-title">
      <div>
        <h3>{title}</h3>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {badge ? <span>{badge}</span> : null}
    </div>
  );
}
