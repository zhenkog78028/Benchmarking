"""LLM-as-a-judge benchmark orchestration and result validation."""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json
import statistics
from typing import Any

from generation import generate_text


# Tune this according to your provider's rate limits.
DEFAULT_MAX_WORKERS = 8

# These calls should produce compact structured data rather than essays.
PROMPT_MAX_TOKENS = 500
RUBRIC_MAX_TOKENS = 400
EVALUATION_MAX_TOKENS = 250
ASSESSEE_MAX_TOKENS = 1800

# Assessee responses may legitimately need more room.
ASSESSEE_MAX_TOKENS = 1800


@dataclass(frozen=True)
class WorkflowPrompts:
    prompt_author_system: str
    prompt_author_user: str
    rubric_author_system: str
    rubric_author_user: str
    assessee_system: str
    assessee_user: str
    response_assessor_system: str
    response_assessor_user: str


def parse_json(text: str) -> dict[str, Any]:
    """Parse a JSON model response, allowing an accidental Markdown fence."""
    candidate = text.strip()

    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[1] if "\n" in candidate else ""
        if candidate.rstrip().endswith("```"):
            candidate = candidate.rstrip()[:-3]

    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"expected JSON but received: {text[:200]!r}"
        ) from error

    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")

    return value


def validate_prompt_spec(value: dict[str, Any]) -> None:
    required = {
        "benchmark_prompt",
        "expected_output_format",
        "assumptions",
    }

    if set(value) != required:
        raise ValueError(
            f"prompt specification must contain exactly {sorted(required)}"
        )

    if (
        not isinstance(value["benchmark_prompt"], str)
        or not value["benchmark_prompt"].strip()
    ):
        raise ValueError("benchmark_prompt must be a non-empty string")

    if not isinstance(value["expected_output_format"], str):
        raise ValueError("expected_output_format must be a string")

    if (
        not isinstance(value["assumptions"], list)
        or not all(
            isinstance(item, str)
            for item in value["assumptions"]
        )
    ):
        raise ValueError("assumptions must be a list of strings")


def validate_rubric(value: dict[str, Any]) -> None:
    """Validate the compact benchmark rubric."""
    if set(value) != {"criteria", "automatic_failures"}:
        raise ValueError(
            "rubric must contain exactly criteria and automatic_failures"
        )

    criteria = value["criteria"]

    if not isinstance(criteria, list) or not criteria:
        raise ValueError("rubric must have at least one criterion")

    seen_ids: set[str] = set()
    total_weight = 0

    for item in criteria:
        if not isinstance(item, dict):
            raise ValueError("each rubric criterion must be an object")

        if set(item) != {"id", "weight", "requirement"}:
            raise ValueError(
                "each criterion must contain exactly id, weight, and requirement"
            )

        criterion_id = item["id"]
        weight = item["weight"]
        requirement = item["requirement"]

        if not isinstance(criterion_id, str) or not criterion_id.strip():
            raise ValueError("criterion id must be a non-empty string")

        if criterion_id in seen_ids:
            raise ValueError(f"duplicate criterion id: {criterion_id}")

        seen_ids.add(criterion_id)

        if (
            not isinstance(weight, int)
            or isinstance(weight, bool)
            or weight < 0
        ):
            raise ValueError(
                "criterion weight must be a non-negative integer"
            )

        total_weight += weight

        if not isinstance(requirement, str) or not requirement.strip():
            raise ValueError(
                "criterion requirement must be a non-empty string"
            )

    if total_weight != 100:
        raise ValueError("rubric criterion weights must total 100")

    automatic_failures = value["automatic_failures"]

    if (
        not isinstance(automatic_failures, list)
        or not all(
            isinstance(item, str) and item.strip()
            for item in automatic_failures
        )
    ):
        raise ValueError(
            "automatic_failures must be a list of non-empty strings"
        )


def score_evaluation(
    value: dict[str, Any],
    rubric: dict[str, Any],
) -> tuple[float, float]:
    """
    Validate evaluator output and calculate scores deterministically.

    Score conventions:
    - Criterion score: 0-100 integer
    - Weighted percentage: 0-100 float
    - Final score: 1.0-10.0 float
    """
    if set(value) != {
        "criterion_scores",
        "automatic_failures_triggered",
    }:
        raise ValueError(
            "evaluation must contain exactly criterion_scores "
            "and automatic_failures_triggered"
        )

    criterion_scores = value["criterion_scores"]
    failures = value["automatic_failures_triggered"]

    if not isinstance(criterion_scores, list):
        raise ValueError("criterion_scores must be a list")

    if not isinstance(failures, list) or not all(
        isinstance(item, str) for item in failures
    ):
        raise ValueError(
            "automatic_failures_triggered must be a list of strings"
        )

    rubric_criteria = {
        item["id"]: item
        for item in rubric["criteria"]
    }

    submitted_scores: dict[str, int] = {}

    for item in criterion_scores:
        if not isinstance(item, dict):
            raise ValueError("criterion score must be an object")

        if set(item) != {"id", "score"}:
            raise ValueError(
                "criterion score must contain exactly id and score"
            )

        criterion_id = item["id"]
        score = item["score"]

        if criterion_id not in rubric_criteria:
            raise ValueError(
                f"unknown criterion id: {criterion_id}"
            )

        if criterion_id in submitted_scores:
            raise ValueError(
                f"duplicate criterion score: {criterion_id}"
            )

        if (
            not isinstance(score, int)
            or isinstance(score, bool)
            or not 0 <= score <= 100
        ):
            raise ValueError(
                "criterion score must be an integer from 0 through 100"
            )

        submitted_scores[criterion_id] = score

    expected_ids = set(rubric_criteria)
    submitted_ids = set(submitted_scores)

    if submitted_ids != expected_ids:
        missing = expected_ids - submitted_ids
        extra = submitted_ids - expected_ids

        raise ValueError(
            f"criterion scores do not match rubric; "
            f"missing={sorted(missing)}, extra={sorted(extra)}"
        )

    allowed_failures = set(rubric["automatic_failures"])

    unknown_failures = set(failures) - allowed_failures
    if unknown_failures:
        raise ValueError(
            f"unknown automatic failures: {sorted(unknown_failures)}"
        )

    # Automatic failures receive the minimum score.
    if failures:
        return 1.0, 0.0

    weighted_percentage = sum(
        rubric_criteria[criterion_id]["weight"]
        * score
        / 100
        for criterion_id, score in submitted_scores.items()
    )

    # Convert 0-100 percentage to the canonical 1-10 scale.
    # Preserve one decimal place rather than rounding to an integer.
    final_score = round(weighted_percentage / 10, 1)

    # Benchmark scores use a minimum of 1.0.
    final_score = max(1.0, min(10.0, final_score))

    return final_score, round(weighted_percentage, 1)



# ---------------------------------------------------------------------------
# Benchmark creation
# ---------------------------------------------------------------------------

def _create_single_benchmark(
    assessor: str,
    use_case: str,
    criteria: str,
    client,
    prompts: WorkflowPrompts,
    attempts: int,
) -> dict[str, Any] | None:
    """
    Create one assessor's benchmark.

    Prompt generation and rubric generation remain sequential because
    the rubric depends on the generated benchmark prompt.
    """
    print(f"[{assessor}] authoring benchmark and rubric...")

    try:
        prompt_spec = parse_json(
            generate_text(
                prompts.prompt_author_user.format(
                    use_case=use_case,
                    criteria=criteria,
                ),
                prompts.prompt_author_system,
                assessor,
                client,
                attempts,
                max_tokens=PROMPT_MAX_TOKENS,
            )
        )

        validate_prompt_spec(prompt_spec)

        rubric = parse_json(
            generate_text(
                prompts.rubric_author_user.format(
                    use_case=use_case,
                    criteria=criteria,
                    benchmark_prompt=prompt_spec["benchmark_prompt"],
                    expected_output_format=prompt_spec[
                        "expected_output_format"
                    ],
                ),
                prompts.rubric_author_system,
                assessor,
                client,
                attempts,
                max_tokens=RUBRIC_MAX_TOKENS,
            )
        )

        validate_rubric(rubric)

        return {
            "assessor": assessor,
            "prompt_spec": prompt_spec,
            "rubric": rubric,
        }

    except (RuntimeError, ValueError) as error:
        print(f"[{assessor}] skipped: {error}")
        return None


def create_benchmarks(
    use_case: str,
    criteria: str,
    assessor_models: tuple[str, ...],
    client,
    prompts: WorkflowPrompts,
    attempts: int,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> list[dict[str, Any]]:
    """
    Have every assessor independently author a task and matching rubric.

    Assessors are independent, so they are processed concurrently.
    """
    if not assessor_models:
        return []

    workers = min(max_workers, len(assessor_models))

    benchmarks: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _create_single_benchmark,
                assessor,
                use_case,
                criteria,
                client,
                prompts,
                attempts,
            )
            for assessor in assessor_models
        ]

        for future in as_completed(futures):
            benchmark = future.result()

            if benchmark is not None:
                benchmarks.append(benchmark)

    # Preserve configured assessor order so output is deterministic.
    order = {
        model: index
        for index, model in enumerate(assessor_models)
    }

    benchmarks.sort(
        key=lambda benchmark: order[benchmark["assessor"]]
    )

    return benchmarks


# ---------------------------------------------------------------------------
# Assessee generation
# ---------------------------------------------------------------------------

def _generate_assessee_response(
    assessee: str,
    benchmark: dict[str, Any],
    client,
    prompts: WorkflowPrompts,
    attempts: int,
) -> dict[str, Any]:
    """Generate one assessee response without evaluating it yet."""
    assessor = benchmark["assessor"]
    prompt = benchmark["prompt_spec"]["benchmark_prompt"]

    print(
        f"[{assessee}] answering benchmark authored by [{assessor}]..."
    )

    record: dict[str, Any] = {
        "assessee": assessee,
        "assessor": assessor,
    }

    try:
        answer = generate_text(
            prompts.assessee_user.format(
                benchmark_prompt=prompt,
            ),
            prompts.assessee_system,
            assessee,
            client,
            attempts,
            max_tokens=ASSESSEE_MAX_TOKENS,
        )

        record["response"] = answer

    except RuntimeError as error:
        record["error"] = str(error)

        print(
            f"[{assessee}] / [{assessor}] response skipped: {error}"
        )

    return record


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def _evaluate_response(
    record: dict[str, Any],
    benchmark: dict[str, Any],
    client,
    prompts: WorkflowPrompts,
    attempts: int,
) -> dict[str, Any]:
    """Evaluate one already-generated assessee response."""
    if "error" in record:
        return record

    assessee = record["assessee"]
    assessor = record["assessor"]
    prompt = benchmark["prompt_spec"]["benchmark_prompt"]

    try:
        evaluation = parse_json(
            generate_text(
                prompts.response_assessor_user.format(
                    benchmark_prompt=prompt,
                    rubric=json.dumps(
                        benchmark["rubric"],
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    assessee_response=record["response"],
                ),
                prompts.response_assessor_system,
                assessor,
                client,
                attempts,
                max_tokens=EVALUATION_MAX_TOKENS,
            )
        )

        final_score, weighted_percentage = score_evaluation(
            evaluation,
            benchmark["rubric"],
        )

        record["evaluation"] = evaluation
        record["weighted_percentage"] = weighted_percentage
        record["final_score"] = final_score


    except (RuntimeError, ValueError) as error:
        record["error"] = str(error)

        print(
            f"[{assessee}] / [{assessor}] evaluation skipped: {error}"
        )

    return record


def run_benchmark(
    benchmarks: list[dict[str, Any]],
    assessee_models: tuple[str, ...],
    client,
    prompts: WorkflowPrompts,
    attempts: int,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> list[dict[str, Any]]:
    """
    Run each assessee against each benchmark and score the responses.

    Phase 1:
        Generate assessee responses concurrently.

    Phase 2:
        Evaluate all successful responses concurrently.

    Splitting these phases prevents a slow judge call from blocking unrelated
    response-generation work.
    """
    if not benchmarks or not assessee_models:
        return []

    work = [
        (assessee, benchmark)
        for assessee in assessee_models
        for benchmark in benchmarks
    ]

    workers = min(max_workers, len(work))

    generated: list[
        tuple[dict[str, Any], dict[str, Any]]
    ] = []

    # Phase 1: generate responses.
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_benchmark = {
            executor.submit(
                _generate_assessee_response,
                assessee,
                benchmark,
                client,
                prompts,
                attempts,
            ): benchmark
            for assessee, benchmark in work
        }

        for future in as_completed(future_to_benchmark):
            benchmark = future_to_benchmark[future]
            record = future.result()
            generated.append((record, benchmark))

    # Phase 2: evaluate successful responses.
    results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_record = {
            executor.submit(
                _evaluate_response,
                record,
                benchmark,
                client,
                prompts,
                attempts,
            ): record
            for record, benchmark in generated
        }

        for future in as_completed(future_to_record):
            results.append(future.result())

    # Restore deterministic ordering.
    assessee_order = {
        model: index
        for index, model in enumerate(assessee_models)
    }

    assessor_order = {
        benchmark["assessor"]: index
        for index, benchmark in enumerate(benchmarks)
    }

    results.sort(
        key=lambda result: (
            assessee_order.get(result["assessee"], 999999),
            assessor_order.get(result["assessor"], 999999),
        )
    )

    return results


def summarise_results(
    results: list[dict[str, Any]],
    assessee_models: list[str] | tuple[str, ...],
) -> list[dict[str, Any]]:
    """Aggregate scores while preserving every selected assessee."""

    scores: defaultdict[str, list[int]] = defaultdict(list)

    for result in results:
        score = result.get("final_score")

        if isinstance(score, int) and not isinstance(score, bool):
            scores[result["assessee"]].append(score)

    summary = []

    for model in assessee_models:
        values = scores[model]

        summary.append({
            "model": model,
            "final_score": statistics.mean(values) if values else None,
            "successful_evaluations": len(values),
        })

    return sorted(
        summary,
        key=lambda item: (
            item["final_score"] is None,
            -(item["final_score"] or 0),
            item["model"],
        ),
    )