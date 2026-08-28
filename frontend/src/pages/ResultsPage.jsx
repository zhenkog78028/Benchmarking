import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { getBenchmark } from '../api';

export default function ResultsPage() {
  const { id } = useParams();
  const nav = useNavigate();

  const [report, setReport] = useState(null);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    getBenchmark(id).then((j) =>
      j.report ? setReport(j.report) : nav(`/running/${id}`)
    );
  }, [id, nav]);

  if (!report) {
    return <main className="center">Loading results…</main>;
  }

  // IMPORTANT:
  // Use the originally selected models, not successful benchmarks/results.
  const assessors = report.assessors ?? [];
  const assessees = report.assessees ?? [];

  const byPair = new Map(
    report.results.map((r) => [
      `${r.assessee}|||${r.assessor}`,
      r,
    ])
  );

  const getAverage = (model) => {
    const scores = assessors
      .map((assessor) => {
        const result = byPair.get(`${model}|||${assessor}`);
        return result?.final_score;
      })
      .filter(
        (score) =>
          typeof score === 'number' &&
          Number.isFinite(score)
      );
  
    if (scores.length === 0) {
      return null;
    }
  
    return (
      scores.reduce((sum, score) => sum + score, 0) /
      scores.length
    );
  };

  const rankings = assessees
    .map((model) => {
      const average = getAverage(model);

      const successfulEvaluations = assessors.filter((assessor) => {
        const result = byPair.get(`${model}|||${assessor}`);

        return (
          typeof result?.final_score === 'number' &&
          Number.isFinite(result.final_score)
        );
      }).length;

      return {
        model,
        final_score: average,
        successful_evaluations: successfulEvaluations,
      };
    })
    .sort((a, b) => {
      if (a.final_score === null) return 1;
      if (b.final_score === null) return -1;

      return b.final_score - a.final_score;
    });

  // Make scores easy to look up by assessee.
  const scoresByModel = new Map(
    rankings.map((s) => [s.model, s])
  );

  const formatAverage = (score) => {
    if (score === null || score === undefined) {
      return '—';
    }

    return Number(score).toFixed(2);
  };

  return (
    <main className="shell">
      <div className="resultsHead">
        <div>
          <p className="eyebrow">RESULTS</p>

          <h1>Benchmark results</h1>

          <p className="lede">
            Scores shown exactly as returned by the evaluator.
            Click on individual scores for details.
          </p>
        </div>

        <button
          className="secondary"
          onClick={() => nav('/')}
        >
          New benchmark
        </button>
      </div>

      <div className="scoreCards">
        {rankings.map((s, i) => (
          <div className="scoreCard" key={s.model}>
            <span>#{i + 1}</span>

            <strong>
              {formatAverage(s.final_score)}
            </strong>

            <p>{s.model}</p>

            <small>
              {s.successful_evaluations} / {assessors.length} successful evaluations
            </small>
          </div>
        ))}
      </div>

      <div className="tableWrap">
        <table>
          <thead>
            <tr>
              <th>Assessee</th>

              {assessors.map((a) => (
                <th key={a}>{a}</th>
              ))}

              <th>Average</th>
            </tr>
          </thead>

          <tbody>
            {assessees.map((model) => {
              const summary = scoresByModel.get(model);

              return (
                <tr key={model}>
                  <th>{model}</th>

                  {assessors.map((assessor) => {
                    const result = byPair.get(
                      `${model}|||${assessor}`
                    );

                    const hasResult = Boolean(result);

                    return (
                      <td key={assessor}>
                        {hasResult ? (
                          <button
                            className="score"
                            onClick={() => setOpen(result)}
                          >
                            {result.final_score ?? 'Failed'}
                          </button>
                        ) : (
                          <span className="missingScore">—</span>
                        )}
                      </td>
                    );
                  })}

                  <td className="avg">
                    {formatAverage(getAverage(model))}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {open && (
        <div
          className="modalBackdrop"
          onClick={() => setOpen(null)}
        >
          <div
            className="modal"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="close"
              onClick={() => setOpen(null)}
            >
              ×
            </button>

            <p className="eyebrow">
              EVALUATION DETAIL
            </p>

            <h2>{open.assessee}</h2>

            <p>
              <b>Assessor:</b> {open.assessor}
            </p>

            <p>
              <b>Score:</b>{' '}
              {open.final_score ?? 'Failed'}
            </p>

            {open.error ? (
              <pre>{open.error}</pre>
            ) : (
              <>
                <h3>Rationale</h3>
                <p>
                  {open.evaluation?.rationale}
                </p>

                <h3>Criterion scores</h3>

                {open.evaluation?.criterion_scores?.map((c) => (
                  <div
                    className="criterion"
                    key={c.id}
                  >
                    <b>
                      {c.id}: {c.score}
                    </b>

                    <p>{c.evidence}</p>
                  </div>
                ))}

                <h3>Response</h3>
                <pre>{open.response}</pre>
              </>
            )}
          </div>
        </div>
      )}
    </main>
  );
}