"""LLM-as-a-judge benchmark orchestration and result validation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
import statistics
from typing import Any

from generation import generate_text


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
        raise ValueError(f"expected JSON but received: {text[:200]!r}") from error
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def validate_prompt_spec(value: dict[str, Any]) -> None:
    required = {"benchmark_prompt", "expected_output_format", "assumptions"}
    if set(value) != required:
        raise ValueError(f"prompt specification must contain exactly {sorted(required)}")
    if not isinstance(value["benchmark_prompt"], str) or not value["benchmark_prompt"].strip():
        raise ValueError("benchmark_prompt must be a non-empty string")
    if not isinstance(value["expected_output_format"], str):
        raise ValueError("expected_output_format must be a string")
    if not isinstance(value["assumptions"], list) or not all(isinstance(item, str) for item in value["assumptions"]):
        raise ValueError("assumptions must be a list of strings")


def validate_rubric(value: dict[str, Any]) -> None:
    criteria = value.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("rubric must have at least one criterion")
    weights = [item.get("weight") for item in criteria if isinstance(item, dict)]
    if len(weights) != len(criteria) or any(
        not isinstance(weight, int) or isinstance(weight, bool) or weight < 0 for weight in weights
    ):
        raise ValueError("each rubric criterion needs a non-negative integer weight")
    if sum(weights) != 100:
        raise ValueError("rubric criterion weights must total 100")


def validate_evaluation(value: dict[str, Any]) -> float:
    score = value.get("final_score")
    if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 100:
        raise ValueError("evaluation final_score must be an integer from 1 through 100")
    return score / 10


def create_benchmarks(
    use_case: str, criteria: str, assessor_models: tuple[str, ...], client, prompts: WorkflowPrompts, attempts: int
) -> list[dict[str, Any]]:
    """Have every assessor independently author a task and a matching rubric."""
    benchmarks: list[dict[str, Any]] = []
    for assessor in assessor_models:
        print(f"[{assessor}] authoring benchmark and rubric...")
        try:
            prompt_spec = parse_json(generate_text(
                prompts.prompt_author_user.format(use_case=use_case, criteria=criteria),
                prompts.prompt_author_system, assessor, client, attempts,
            ))
            validate_prompt_spec(prompt_spec)
            rubric = parse_json(generate_text(
                prompts.rubric_author_user.format(
                    use_case=use_case, criteria=criteria,
                    benchmark_prompt=prompt_spec["benchmark_prompt"],
                    expected_output_format=prompt_spec["expected_output_format"],
                ),
                prompts.rubric_author_system, assessor, client, attempts,
            ))
            validate_rubric(rubric)
            benchmarks.append({"assessor": assessor, "prompt_spec": prompt_spec, "rubric": rubric})
        except (RuntimeError, ValueError) as error:
            print(f"[{assessor}] skipped: {error}")
    return benchmarks


def run_benchmark(
    benchmarks: list[dict[str, Any]], assessee_models: tuple[str, ...], client, prompts: WorkflowPrompts, attempts: int
) -> list[dict[str, Any]]:
    """Run each assessee against each task, then score it using that task's rubric."""
    results: list[dict[str, Any]] = []
    for assessee in assessee_models:
        for benchmark in benchmarks:
            assessor = benchmark["assessor"]
            prompt = benchmark["prompt_spec"]["benchmark_prompt"]
            print(f"[{assessee}] answering benchmark authored by [{assessor}]...")
            record: dict[str, Any] = {"assessee": assessee, "assessor": assessor}
            try:
                answer = generate_text(
                    prompts.assessee_user.format(benchmark_prompt=prompt),
                    prompts.assessee_system, assessee, client, attempts,
                )
                record["response"] = answer
                evaluation = parse_json(generate_text(
                    prompts.response_assessor_user.format(
                        benchmark_prompt=prompt,
                        rubric=json.dumps(benchmark["rubric"], ensure_ascii=False),
                        assessee_response=answer,
                    ),
                    prompts.response_assessor_system, assessor, client, attempts,
                ))
                record["evaluation"] = evaluation
                record["final_score"] = validate_evaluation(evaluation)
            except (RuntimeError, ValueError) as error:
                record["error"] = str(error)
                print(f"[{assessee}] / [{assessor}] skipped: {error}")
            results.append(record)
    return results


def summarise_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate valid 1–10 evaluator scores for each assessee model."""
    scores: defaultdict[str, list[float]] = defaultdict(list)
    for result in results:
        score = result.get("final_score")
        if isinstance(score, (int, float)) and not isinstance(score, bool):
            scores[result["assessee"]].append(float(score))
    return sorted(
        (
            {"model": model, "final_score": statistics.mean(values), "successful_evaluations": len(values)}
            for model, values in scores.items()
        ),
        key=lambda item: (-item["final_score"], item["model"]),
    )
