#import sqlite3
import pandas as pd
import os
from time import perf_counter_ns
from dotenv import load_dotenv
from openai import OpenAI
import time
from openai import RateLimitError

from config import PRIME_PROMPT, SYSTEM_PROMPT, MODELS
from execution import run_code

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

models = MODELS

def benchmark1(llms=models, trials=1):
    data = pd.DataFrame(columns=("model", "success", "generation_speed", "execution_speed", "code"))

    prompt = PRIME_PROMPT

    system_prompt = SYSTEM_PROMPT

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

def main():
    benchmark1(trials=1)


if __name__ == "__main__":
    main()
