"""Shared helpers for obtaining model completions."""

from __future__ import annotations

from dataclasses import dataclass
import time
import random

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}




@dataclass
class GenerationResult:
    """A generated code response and the time spent obtaining it."""

    code: str | None
    generation_time_ns: int | None

def _status_code(exc) -> int | None:
    """Best-effort extraction of HTTP status from OpenAI/OpenRouter exceptions."""
    return (
        getattr(exc, "status_code", None)
        or getattr(getattr(exc, "response", None), "status_code", None)
    )


def _is_retryable(exc: Exception) -> bool:
    status = _status_code(exc)

    if status in RETRYABLE_STATUS:
        return True

    msg = str(exc).lower()
    transient = (
        "timeout",
        "timed out",
        "connection",
        "temporarily",
        "rate limit",
        "overloaded",
        "try again",
    )

    return any(x in msg for x in transient)


def generate_text(
    prompt: str,
    system_prompt: str,
    llm: str,
    client,
    attempts: int = 3,
    timeout: float = 15.0,
) -> str:
    """
    Generate text with retries for transient OpenRouter/provider failures.

    - Fast failure (~15 s/request)
    - Exponential backoff with jitter
    - Retries only transient errors
    """

    if attempts < 1:
        raise ValueError("attempts must be at least 1")

    last_error = None

    for attempt in range(attempts):
        try:
            response = client.chat.completions.create(
                model=llm,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                timeout=timeout,
                stream=False,
            )

            choices = getattr(response, "choices", None)
            if not choices:
                raise RuntimeError("No choices returned.")

            message = choices[0].message
            content = getattr(message, "content", None)

            if isinstance(content, list):
                content = "".join(
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict)
                )

            if not content or not content.strip():
                raise RuntimeError("Model returned an empty response.")

            return content.strip()

        except Exception as exc:
            last_error = exc

            # Don't retry permanent failures.
            if not _is_retryable(exc):
                break

            if attempt == attempts - 1:
                break

            # Exponential backoff with jitter.
            delay = min(2 ** attempt, 8)
            delay *= random.uniform(0.8, 1.2)
            time.sleep(delay)

    raise RuntimeError(
        f"{llm} failed after {attempts} attempt(s): {last_error}"
    ) from last_error


def generate_code(prompt: str, system_prompt: str, llm: str, client, attempts: int) -> GenerationResult:
    """Generate code while preserving the legacy result shape used by execution.py."""
    start_generation = time.perf_counter_ns()
    try:
        code = generate_text(prompt, system_prompt, llm, client, attempts)
    except RuntimeError:
        return GenerationResult(code=None, generation_time_ns=None)

    if code.startswith("```"):
        code = code[code.find("\n") + 1:code.rfind("\n")]
    return GenerationResult(code=code, generation_time_ns=time.perf_counter_ns() - start_generation)
