"use client";

export type SnapshotValidation = {
  ok: boolean;
  reason?: "missing" | "load_failed" | "blank_or_white" | "canvas_failed";
};

export async function validatePrintSnapshot(dataUrl?: string | null): Promise<SnapshotValidation> {
  if (!dataUrl || !dataUrl.startsWith("data:image/")) return { ok: false, reason: "missing" };
  return new Promise((resolve) => {
    const image = new Image();
    image.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        const width = Math.min(96, image.naturalWidth || image.width);
        const height = Math.min(96, image.naturalHeight || image.height);
        if (!width || !height) {
          resolve({ ok: false, reason: "missing" });
          return;
        }
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d", { willReadFrequently: true });
        if (!ctx) {
          resolve({ ok: false, reason: "canvas_failed" });
          return;
        }
        ctx.drawImage(image, 0, 0, width, height);
        const pixels = ctx.getImageData(0, 0, width, height).data;
        let nonWhite = 0;
        for (let index = 0; index < pixels.length; index += 4) {
          const alpha = pixels[index + 3] ?? 255;
          const red = pixels[index] ?? 255;
          const green = pixels[index + 1] ?? 255;
          const blue = pixels[index + 2] ?? 255;
          if (alpha > 10 && (red < 245 || green < 245 || blue < 245)) nonWhite += 1;
        }
        const ratio = nonWhite / (width * height);
        resolve(ratio >= 0.025 ? { ok: true } : { ok: false, reason: "blank_or_white" });
      } catch {
        resolve({ ok: false, reason: "canvas_failed" });
      }
    };
    image.onerror = () => resolve({ ok: false, reason: "load_failed" });
    image.src = dataUrl;
  });
}
