#import sqlite3
import pandas as pd
import os
from time import perf_counter_ns
import importlib.util
import tempfile
from dotenv import load_dotenv
from openai import OpenAI
import time
from openai import RateLimitError


load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

models = (
    "openai/gpt-oss-120b:free",
    "cohere/north-mini-code:free",
)

def benchmark1(llms=models, trials=1):
    data = pd.DataFrame(columns=("model", "success", "generation_speed", "execution_speed", "code"))

    prompt = """Please write a python function to calculate the n-th prime number.
Return your answer without any formatting (no backticks) or other explanation text, only the code.
Your answer should have a function `prime(n)` that takes in n and returns the n-th prime
"""

    system_prompt = """You are a code generator. Output ONLY raw code.
Do not include markdown code blocks (backticks), explanations, or 'Sure, here is your code' style introductions."""

    for llm in llms:
        for i in range(trials):
            start_generation = perf_counter_ns()

            response = None

            #trying my best to avoid rate limits with free models
            for attempt in range(5):
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
                    if attempt == 4:
                        print("Rate limit exceeded. Skipping this trial for model: ", llm)
                        break
                    time.sleep(2 ** attempt)
            
            if response is None:
                break      # move to the next model
            else:
                print(f"Model: {llm}, Trial: {i+1}, Response received.")

            end_generation = perf_counter_ns()
            generation_time = end_generation - start_generation

            code = response.choices[0].message.content or ""

            if code.startswith("```"):
                code = code[code.find("\n") + 1:code.rfind("\n")]

            try:
                time1 = perf_counter_ns()

                prime = run_code(code)
                test1 = prime(10) # what machine would we be running this on?
                test2 = prime(50)
                test3 = prime(100)

                time2 = perf_counter_ns()
                delta = time2 - time1

                success = int(test1 == 29 and test2 == 229 and test3 == 541)
                data.loc[len(data)] = [llm, success, generation_time, delta, code]

            except Exception:
                data.loc[len(data)] = [llm, -1, generation_time, None, code]

    print(data.to_string())
    data.to_clipboard()

#We should consider running the code in a sandboxed environment, subprocess, or VM, or using a library like `restrictedpython` to safely execute the code without risking security (but this is allegedly complex).
def run_code(code: str):
    """Write code to a temp file, import it as a module, return the prime function."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = f.name

    try:
        spec = importlib.util.spec_from_file_location("prime_module", tmp_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.prime
    finally:
        os.unlink(tmp_path)


def main():
    benchmark1(trials=1)


if __name__ == "__main__":
    main()
