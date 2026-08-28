from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from benchmark_workflow import (
    WorkflowPrompts,
    create_benchmarks,
    run_benchmark,
    summarise_results,
)
from config import (
    ASSESSORS,
    ASSESSEES,
    CLIENT,
    PROMPT_AUTHOR_SYSTEM_PROMPT,
    PROMPT_AUTHOR_USER_PROMPT,
    RUBRIC_AUTHOR_SYSTEM_PROMPT,
    RUBRIC_AUTHOR_USER_PROMPT,
    ASSESSEE_SYSTEM_PROMPT,
    ASSESSEE_USER_PROMPT,
    RESPONSE_ASSESSOR_SYSTEM_PROMPT,
    RESPONSE_ASSESSOR_USER_PROMPT,
)


app = FastAPI(title="LLM Benchmark API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Number of benchmark jobs that may execute simultaneously.
JOB_WORKERS = 2

# Number of simultaneous LLM requests within a benchmark job.
# Tune according to OpenRouter/provider rate limits.
LLM_WORKERS = 8


job_executor = ThreadPoolExecutor(max_workers=JOB_WORKERS)

jobs: dict[str, dict[str, Any]] = {}
lock = Lock()


PROMPTS = WorkflowPrompts(
    prompt_author_system=PROMPT_AUTHOR_SYSTEM_PROMPT,
    prompt_author_user=PROMPT_AUTHOR_USER_PROMPT,
    rubric_author_system=RUBRIC_AUTHOR_SYSTEM_PROMPT,
    rubric_author_user=RUBRIC_AUTHOR_USER_PROMPT,
    assessee_system=ASSESSEE_SYSTEM_PROMPT,
    assessee_user=ASSESSEE_USER_PROMPT,
    response_assessor_system=RESPONSE_ASSESSOR_SYSTEM_PROMPT,
    response_assessor_user=RESPONSE_ASSESSOR_USER_PROMPT,
)


class BenchmarkRequest(BaseModel):
    use_case: str = Field(min_length=1)
    criteria: str = Field(min_length=1)
    assessors: list[str] = Field(min_length=1)
    assessees: list[str] = Field(min_length=1)
    attempts: int = Field(default=3, ge=1, le=10)


def set_job(job_id: str, **updates: Any) -> None:
    with lock:
        jobs[job_id].update(updates)


def execute_job(
    job_id: str,
    request: BenchmarkRequest,
) -> None:
    try:
        set_job(
            job_id,
            status="running",
            stage="Creating benchmarks",
        )

        benchmarks = create_benchmarks(
            request.use_case,
            request.criteria,
            tuple(request.assessors),
            CLIENT,
            PROMPTS,
            request.attempts,
            max_workers=LLM_WORKERS,
        )

        if not benchmarks:
            raise RuntimeError("No valid benchmarks were created.")

        set_job(
            job_id,
            stage="Running and scoring models",
            benchmarks_created=len(benchmarks),
        )

        results = run_benchmark(
            benchmarks,
            tuple(request.assessees),
            CLIENT,
            PROMPTS,
            request.attempts,
            max_workers=LLM_WORKERS,
        )

        model_scores = summarise_results(results, request.assessees)

        report = {
            "use_case": request.use_case,
            "criteria": request.criteria,
            "benchmarks": benchmarks,
            "assessors": list(request.assessors),
            "assessees": list(request.assessees),
            "results": results,
            "model_scores": model_scores,
        }

        set_job(
            job_id,
            status="completed",
            stage="Complete",
            report=report,
        )

    except Exception as exc:
        set_job(
            job_id,
            status="failed",
            stage="Failed",
            error=str(exc),
        )


@app.get("/api/models")
def get_models():
    return {
        "assessors": list(ASSESSORS),
        "assessees": list(ASSESSEES),
    }


@app.post("/api/benchmarks", status_code=202)
def start_benchmark(request: BenchmarkRequest):
    unknown_assessors = (
        set(request.assessors) - set(ASSESSORS)
    )
    unknown_assessees = (
        set(request.assessees) - set(ASSESSEES)
    )

    if unknown_assessors or unknown_assessees:
        raise HTTPException(
            400,
            "One or more selected models are not configured.",
        )

    job_id = str(uuid4())

    with lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "stage": "Queued",
        }

    job_executor.submit(
        execute_job,
        job_id,
        request,
    )

    return {"job_id": job_id}


@app.get("/api/benchmarks/{job_id}")
def get_benchmark(job_id: str):
    with lock:
        job = jobs.get(job_id)

        if not job:
            raise HTTPException(
                404,
                "Benchmark job not found.",
            )

        return dict(job)