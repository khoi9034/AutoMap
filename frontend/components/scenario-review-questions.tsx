type ScenarioReviewQuestionsProps = {
  questions?: string[];
  assumptions?: string[];
};

export function ScenarioReviewQuestions({ questions = [], assumptions = [] }: ScenarioReviewQuestionsProps) {
  return (
    <section className="panel">
      <h3>Review questions</h3>
      <div className="two-column">
        <div>
          <h4>Questions</h4>
          <ul className="plain-list">
            {questions.length ? questions.map((question) => <li key={question}>{question}</li>) : <li>No review questions generated yet.</li>}
          </ul>
        </div>
        <div>
          <h4>Assumptions</h4>
          <ul className="plain-list">
            {assumptions.length ? assumptions.map((assumption) => <li key={assumption}>{assumption}</li>) : <li>No assumptions recorded yet.</li>}
          </ul>
        </div>
      </div>
    </section>
  );
}
