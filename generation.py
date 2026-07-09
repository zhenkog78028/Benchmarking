import time
from openai import RateLimitError
from dataclasses import dataclass

#dataclass for robustness as the amount of data returned grows eventually
@dataclass
class GenerationResult:
    code: str | None
    generation_time_ns: int | None

#Generate code using the specified LLM and prompt.
def generate_code(prompt: str, system_prompt: str, llm: str, client, attempts: int):
    start_generation = time.perf_counter_ns()

    response = None

    #trying my best to avoid rate limits with free models
    for attempt in range(attempts):
        try:
            response = client.chat.completions.create(
                model=llm,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                stream=False,
            )
            break
        except RateLimitError:
            if attempt == attempts - 1:
                print("Rate limit exceeded. Skipping this trial for model: ", llm)
                break
            time.sleep(2 ** attempt)
    
    if response is None:
        print(f"Model: {llm}, No response received after {attempts} attempts. Skipping this trial.")
        return GenerationResult(
            code=None,
            generation_time_ns=None,
        )    # move to the next model
    else:
        print(f"Model: {llm}, Response received.")

    end_generation = time.perf_counter_ns()
    generation_time = end_generation - start_generation

    code = response.choices[0].message.content or ""

    # Remove markdown code blocks if present
    if code.startswith("```"):
        code = code[code.find("\n") + 1:code.rfind("\n")]
    
    return GenerationResult(
        code=code,
        generation_time_ns=generation_time,
    )