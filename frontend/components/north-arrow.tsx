"use client";

export function NorthArrow() {
  return (
    <div className="north-arrow" aria-label="North arrow">
      <svg viewBox="0 0 42 64" role="img" aria-hidden="true">
        <path className="north-arrow-shadow" d="M21 3l16 38-16-8-16 8L21 3z" />
        <path className="north-arrow-fill" d="M21 6l13 31-13-6.5L8 37 21 6z" />
        <path className="north-arrow-spine" d="M21 9v41" />
      </svg>
      <strong>N</strong>
    </div>
  );
}
