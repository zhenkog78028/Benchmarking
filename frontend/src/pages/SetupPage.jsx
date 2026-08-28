import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { getModels, startBenchmark } from '../api';
import ModelSelector from '../components/ModelSelector';

export default function SetupPage() {
  const nav = useNavigate();

  const [models, setModels] = useState({
    assessors: [],
    assessees: [],
  });
  const [assessors, setAssessors] = useState([]);
  const [assessees, setAssessees] = useState([]);
  const [useCase, setUseCase] = useState('');
  const [criteria, setCriteria] = useState('');
  const [attempts, setAttempts] = useState(3);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getModels()
      .then((m) => {
        setModels(m);
        // setAssessors(m.assessors);
        // setAssessees(m.assessees);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function submit(e) {
    e.preventDefault();
    setError('');

    if (!assessors.length || !assessees.length) {
      setError('Select at least one assessor and one assessee.');
      return;
    }

    setBusy(true);

    try {
      const { job_id } = await startBenchmark({
        use_case: useCase,
        criteria,
        assessors,
        assessees,
        attempts,
      });

      nav(`/running/${job_id}`);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <header>
        <p className="eyebrow">LLM EVALUATION</p>

        <h1>Benchmark models against custom use case.</h1>

        <p className="lede">
          Define use case, choose the assessors and assessees, then compare
          model performance.
        </p>
      </header>

      <form className="setup" onSubmit={submit}>
        <div className="formPanel">
          <label>
            Use case
            <textarea
              rows="8"
              value={useCase}
              onChange={(e) => setUseCase(e.target.value)}
              placeholder="Describe the task you want AI to perform..."
              required
            />
          </label>

          <label>
            Evaluation criteria
            <textarea
              rows="6"
              value={criteria}
              onChange={(e) => setCriteria(e.target.value)}
              placeholder="Describe what a strong response must do..."
              required
            />
          </label>

          <label className="attempts">
            Attempts per API call
            <p>Increases runtime but increases chances of getting response (max 10)</p>
            <input
              type="number"
              min="1"
              max="5"
              value={attempts}
              onChange={(e) => setAttempts(Number(e.target.value))}
            />
          </label>

          {error && <div className="error">{error}</div>}

          <button className="primary" disabled={busy}>
            {busy ? 'Starting…' : 'Run benchmark'}
          </button>
        </div>

        <aside>
          <ModelSelector
            title="Assessors"
            models={models.assessors}
            selected={assessors}
            setSelected={setAssessors}
          />

          <ModelSelector
            title="Assessees"
            models={models.assessees}
            selected={assessees}
            setSelected={setAssessees}
          />
        </aside>
      </form>
    </main>
  );
}