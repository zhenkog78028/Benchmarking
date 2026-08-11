# LLM Benchmark Web UI

React (Vite) frontend + FastAPI backend for the supplied benchmark workflow.

## Add your existing Python files
Place these in `backend/`:
- `config.py`
- `benchmark_workflow.py`
- `generation.py`

Keep your validator unchanged. The UI displays evaluator scores exactly as produced by the workflow.

## Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
# Create backend/.env containing OPENROUTER_API_KEY=...
uvicorn main:app --reload
```

## Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Notes
The job store is intentionally in-memory for simplicity. Restarting FastAPI clears completed/running jobs. For production, replace it with Redis/database-backed jobs and a worker queue.
