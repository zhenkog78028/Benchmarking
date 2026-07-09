#import sqlite3
import pandas as pd
#import os
from time import perf_counter_ns

from config import PRIME_PROMPT, SYSTEM_PROMPT, MODELS, CLIENT
from execution import run_code
from generation import generate_code

client = CLIENT

models = MODELS

def benchmark1(llms=models, trials=1):
    data = pd.DataFrame(columns=("model", "success", "generation_speed", "execution_speed", "code"))

    prompt = PRIME_PROMPT

    system_prompt = SYSTEM_PROMPT

    for llm in llms:
        for i in range(trials):
            result = generate_code(prompt, system_prompt, llm, client, attempts=5)

            try:
                time1 = perf_counter_ns()

                prime = run_code(result.code)
                test1 = prime(10) # what machine would we be running this on?
                test2 = prime(50)
                test3 = prime(100)

                time2 = perf_counter_ns()
                delta = time2 - time1

                success = int(test1 == 29 and test2 == 229 and test3 == 541)
                data.loc[len(data)] = [llm, success, result.generation_time_ns, delta, result.code]

            except Exception:
                data.loc[len(data)] = [llm, -1, result.generation_time_ns, None, result.code]

    print(data.to_string())
    data.to_clipboard()

def main():
    benchmark1(trials=1)


if __name__ == "__main__":
    main()
