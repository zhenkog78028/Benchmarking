"""CLI entry point for the use-case-specific LLM benchmark."""

import argparse
import json
from pathlib import Path

from benchmark_workflow import (
    WorkflowPrompts,
    create_benchmarks,
    run_benchmark,
    summarise_results,
)
from config import (
    ASSESSORS,
    ASSESSEES,
    ASSESSEE_SYSTEM_PROMPT,
    ASSESSEE_USER_PROMPT,
    CLIENT,
    PROMPT_AUTHOR_SYSTEM_PROMPT,
    PROMPT_AUTHOR_USER_PROMPT,
    RESPONSE_ASSESSOR_SYSTEM_PROMPT,
    RESPONSE_ASSESSOR_USER_PROMPT,
    RUBRIC_AUTHOR_SYSTEM_PROMPT,
    RUBRIC_AUTHOR_USER_PROMPT,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a custom LLM benchmark.")
    parser.add_argument("--use-case", help="The user-described task to benchmark.", default="I run a restauraunt and I need to keep track of things such as silverware, plates, food, and what not, and would use AI for predicting breakage and losses in inventory.")
    parser.add_argument("--criteria", help="The requirements used to judge model quality.", default="I need accuracy and robustness to create accurate predictions accross various restaraunt condintions and busyness")
    parser.add_argument("--attempts", type=int, default=3, help="Attempts per API call (default: 3).")
    parser.add_argument("--output", type=Path, default=Path("benchmark_results.json"), help="JSON report path.")
    args = parser.parse_args()
    if args.attempts < 1:
        parser.error("--attempts must be at least 1")

    use_case = args.use_case or input("Describe the use case: ").strip()
    criteria = args.criteria or input("Describe the evaluation criteria: ").strip()
    if not use_case or not criteria:
        parser.error("both a use case and criteria are required")

    prompts = WorkflowPrompts(
        prompt_author_system=PROMPT_AUTHOR_SYSTEM_PROMPT,
        prompt_author_user=PROMPT_AUTHOR_USER_PROMPT,
        rubric_author_system=RUBRIC_AUTHOR_SYSTEM_PROMPT,
        rubric_author_user=RUBRIC_AUTHOR_USER_PROMPT,
        assessee_system=ASSESSEE_SYSTEM_PROMPT,
        assessee_user=ASSESSEE_USER_PROMPT,
        response_assessor_system=RESPONSE_ASSESSOR_SYSTEM_PROMPT,
        response_assessor_user=RESPONSE_ASSESSOR_USER_PROMPT,
    )
    benchmarks = create_benchmarks(use_case, criteria, ASSESSORS, CLIENT, prompts, args.attempts)
    if not benchmarks:
        raise SystemExit("No valid benchmarks were created; no assessee models were run.")

    results = run_benchmark(benchmarks, ASSESSEES, CLIENT, prompts, args.attempts)
    model_scores = summarise_results(results)
    report = {
        "use_case": use_case,
        "criteria": criteria,
        "benchmarks": benchmarks,
        "results": results,
        "model_scores": model_scores,
    }
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    print("\nFinal model scores (mean rubric score, 1–10):")
    for item in model_scores:
        print(f"{item['model']}: {item['final_score']}/10 ({item['successful_evaluations']} evaluations)")
    print(f"\nFull report written to {args.output}")


if __name__ == "__main__":
    main()
