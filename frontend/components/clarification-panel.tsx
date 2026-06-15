"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { ClarificationQuestionCard } from "@/components/clarification-question-card";
import { RequestIntelligencePanel } from "@/components/request-intelligence-panel";
import { RefinementSummary } from "@/components/refinement-summary";
import { StatusChip } from "@/components/status-chip";
import { ToastMessage } from "@/components/toast";
import {
  answerClarificationSession,
  getClarificationSession,
  refineClarificationSession,
  startClarification,
} from "@/lib/api";
import {
  loadWorkflowState,
  mergeWorkflowState,
  workflowMissingDataFromRecipe,
  workflowWarningsFromRecipe,
} from "@/lib/workflow-store";
import type {
  ClarificationAnswerModel,
  ClarificationQuestionModel,
  ClarificationSession,
  JsonValue,
} from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

function defaultValue(question: ClarificationQuestionModel): JsonValue {
  if (question.default_answer !== undefined) {
    return question.default_answer;
  }
  if (question.question_type === "multi_choice") {
    return [];
  }
  return "";
}

function answerLabel(question: ClarificationQuestionModel, value: JsonValue): string {
  const values = Array.isArray(value) ? value : [value];
  const labels = (question.options || [])
    .filter((option) => values.some((item) => JSON.stringify(item) === JSON.stringify(option.value)))
    .map((option) => option.label || String(option.value));
  return labels.length ? labels.join(", ") : String(value);
}

export function ClarificationPanel() {
  const [prompt, setPrompt] = useState("");
  const [session, setSession] = useState<ClarificationSession | null>(null);
  const [answers, setAnswers] = useState<Record<string, { value: JsonValue; label?: string }>>({});
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  useEffect(() => {
    const workflow = loadWorkflowState();
    setPrompt(workflow.rawPrompt || workflow.recipe?.user_intent || "");
    if (workflow.clarificationSessionId) {
      setLoading("load");
      getClarificationSession(workflow.clarificationSessionId)
        .then((loaded) => {
          setSession(loaded);
          const loadedAnswers: Record<string, { value: JsonValue; label?: string }> = {};
          for (const answer of loaded.answers || []) {
            if (answer.question_id) {
              loadedAnswers[answer.question_id] = {
                value: answer.answer_value ?? "",
                label: answer.answer_label || undefined,
              };
            }
          }
          setAnswers(loadedAnswers);
        })
        .catch(() => setSession(workflow.clarificationSession || null))
        .finally(() => setLoading(null));
    } else if (workflow.recipe && (workflow.recipe.request_intelligence?.clarifying_questions?.length || workflow.recipe.analysis_plan?.review_questions?.length)) {
      setSession({
        raw_prompt: workflow.rawPrompt || workflow.recipe.user_intent,
        initial_recipe: workflow.recipe,
        questions: workflow.clarificationQuestions,
        answers: workflow.clarificationAnswers,
        status: "local_recipe_questions",
      });
    }
  }, []);

  const questions = useMemo(() => session?.questions || [], [session]);
  const answeredList = useMemo<ClarificationAnswerModel[]>(() => {
    return questions
      .filter((question) => question.question_id)
      .map((question) => {
        const questionId = question.question_id || "";
        const stored = answers[questionId];
        const value = stored?.value ?? defaultValue(question);
        return {
          question_id: questionId,
          answer_value: value,
          answer_label: stored?.label || answerLabel(question, value),
          answered_by: "frontend_reviewer",
        };
      });
  }, [answers, questions]);

  function updateAnswer(questionId: string, value: JsonValue, label?: string) {
    setAnswers((current) => ({ ...current, [questionId]: { value, label } }));
  }

  async function startSession() {
    if (!prompt.trim()) {
      setError("Enter or generate a prompt before starting clarification.");
      return;
    }
    setLoading("start");
    setError(null);
    try {
      const created = await startClarification(prompt);
      setSession(created);
      mergeWorkflowState({
        rawPrompt: prompt,
        initialRecipe: created.initial_recipe || null,
        recipe: created.initial_recipe || null,
        clarificationSessionId: created.session_id || "",
        clarificationSession: created,
        clarificationQuestions: created.questions || [],
        clarificationAnswers: [],
        activeStep: "clarify",
        warnings: workflowWarningsFromRecipe(created.initial_recipe || null),
        missingData: workflowMissingDataFromRecipe(created.initial_recipe || null),
      });
      setToast({ tone: "success", message: "Clarification session started." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not start clarification.");
    } finally {
      setLoading(null);
    }
  }

  async function submitAnswers() {
    if (!session?.session_id) {
      setError("Start a clarification session before submitting answers.");
      return;
    }
    setLoading("answer");
    setError(null);
    try {
      const answered = await answerClarificationSession(session.session_id, answeredList);
      setSession(answered);
      mergeWorkflowState({
        clarificationSession: answered,
        clarificationAnswers: answered.answers || [],
        activeStep: "clarify",
      });
      setToast({ tone: "success", message: "Answers saved." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not save answers.");
    } finally {
      setLoading(null);
    }
  }

  async function refineRecipe() {
    if (!session?.session_id) {
      setError("Start a clarification session before refining.");
      return;
    }
    setLoading("refine");
    setError(null);
    try {
      let readySession = session;
      if (!session.answers?.length) {
        readySession = await answerClarificationSession(session.session_id, answeredList);
      }
      const refined = await refineClarificationSession(readySession.session_id || session.session_id);
      setSession(refined);
      const refinedRecipe = refined.refined_recipe || null;
      mergeWorkflowState({
        rawPrompt: refined.raw_prompt || prompt,
        initialRecipe: refined.initial_recipe || null,
        recipe: refinedRecipe,
        refinedRecipe,
        clarificationSessionId: refined.session_id || "",
        clarificationSession: refined,
        clarificationQuestions: refined.questions || [],
        clarificationAnswers: refined.answers || [],
        appliedRefinements: refined.refined_request_context || null,
        remainingQuestions: refinedRecipe?.clarification?.remaining_questions || [],
        activeStep: "recipe",
        warnings: workflowWarningsFromRecipe(refinedRecipe),
        missingData: workflowMissingDataFromRecipe(refinedRecipe),
      });
      setToast({ tone: "success", message: "Refined recipe is ready for review." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not refine recipe.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="page-stack">
      <section className="panel prompt-box">
        <div className="panel-title-row">
          <div>
            <h3>Clarify request</h3>
            <p className="muted">Answers refine the local recipe and analysis plan without calling an external LLM.</p>
          </div>
          <StatusChip tone={session?.status === "refined" ? "success" : "warning"}>{session?.status || "not started"}</StatusChip>
        </div>
        <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} aria-label="Clarification prompt" />
        <div className="button-row">
          <button className="button" type="button" onClick={startSession} disabled={!!loading || !prompt.trim()}>
            {loading === "start" ? "Starting..." : "Start Clarification"}
          </button>
          {session?.refined_recipe ? (
            <Link className="button button-secondary" href="/recipe-review">
              Continue with Refined Recipe
            </Link>
          ) : null}
        </div>
        {error ? <p className="error-text">{error}</p> : null}
        <ToastMessage toast={toast} />
      </section>

      {session?.initial_recipe ? <RequestIntelligencePanel recipe={session.initial_recipe} /> : null}

      {questions.length ? (
        <section className="page-stack">
          {questions.map((question) => (
            <ClarificationQuestionCard
              key={question.question_id}
              question={question}
              value={answers[question.question_id || ""]?.value ?? defaultValue(question)}
              onChange={updateAnswer}
            />
          ))}
          <div className="button-row">
            <button className="button button-secondary" type="button" onClick={submitAnswers} disabled={!!loading}>
              {loading === "answer" ? "Saving..." : "Submit Answers"}
            </button>
            <button className="button" type="button" onClick={refineRecipe} disabled={!!loading}>
              {loading === "refine" ? "Refining..." : "Refine Recipe"}
            </button>
          </div>
        </section>
      ) : session ? (
        <section className="panel">
          <h3>No clarification questions</h3>
          <p className="muted">AutoMap did not identify required clarification questions for this request.</p>
        </section>
      ) : null}

      {session?.refined_recipe ? (
        <>
          <section className="panel">
            <div className="panel-title-row">
              <div>
                <h3>{session.refined_recipe.map_title || "Refined recipe"}</h3>
                <p className="muted">Selected layers: {session.refined_recipe.selected_layers?.length || 0}</p>
              </div>
              <StatusChip tone={session.refined_recipe.needs_review ? "warning" : "success"}>
                {session.refined_recipe.needs_review ? "Needs review" : "Ready for review"}
              </StatusChip>
            </div>
          </section>
          <RefinementSummary changes={session.changes_summary || session.refined_recipe.clarification?.changes_from_initial_recipe} />
        </>
      ) : null}
    </div>
  );
}
