"use client";

import { samplePrompts } from "@/components/navigation";
import { ToastMessage } from "@/components/toast";
import type { WorkflowToast } from "@/types/workflow";

type RequestStepProps = {
  error?: string | null;
  loading?: boolean;
  onGenerate: () => void;
  prompt: string;
  setPrompt: (prompt: string) => void;
  toast?: WorkflowToast | null;
};

export function RequestStep({ error, loading = false, onGenerate, prompt, setPrompt, toast }: RequestStepProps) {
  return (
    <section className="composer-request-layout">
      <div className="panel composer-request-card">
        <div>
          <p className="eyebrow">Request</p>
          <h3>Tell AutoMap what map you need.</h3>
          <p className="muted">
            AutoMap will parse the request, choose verified layers, create a draft preview, and keep publishing disabled.
          </p>
        </div>
        <textarea
          className="textarea composer-textarea composer-request-textarea"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Describe the draft map..."
        />
        <button className="button composer-generate-button" type="button" onClick={onGenerate} disabled={loading || !prompt.trim()}>
          {loading ? "Generating Draft Map..." : "Generate Draft Map"}
        </button>
        {loading ? <p className="muted">AutoMap is checking catalog layers, origin matching, and preview readiness...</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
        <ToastMessage toast={toast || null} />
      </div>

      <aside className="panel composer-request-explainer">
        <p className="eyebrow">Sample prompts</p>
        <div className="sample-grid composer-request-samples">
          {samplePrompts.slice(0, 8).map((sample) => (
            <button className="sample-button" key={sample} type="button" onClick={() => setPrompt(sample)}>
              {sample}
            </button>
          ))}
        </div>
        <div className="definition-box">
          <strong>What happens next</strong>
          <p>Preview opens only after AutoMap can safely focus the map. Analysis, publishing, and ArcGIS login are not automatic.</p>
        </div>
      </aside>
    </section>
  );
}
