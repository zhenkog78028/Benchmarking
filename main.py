import pandas as pd

from config import GENERATION_CONFIG, MODELS, DATA_COLUMNS
from execution import run_benchmark
from generation import generate_code

def benchmark(llms=MODELS,config=GENERATION_CONFIG):
    data = pd.DataFrame(columns=DATA_COLUMNS)

    for llm in llms:
        for i in range(config.trials):
            result = generate_code(config.prime_prompt, config.system_prompt, llm, config.client, attempts=config.attempts)

            run_benchmark(llm, result, data)

    return data

def main():
    outcome = benchmark(config=GENERATION_CONFIG)
    print(outcome.to_string())
    #outcome.to_clipboard()


if __name__ == "__main__":
    main()
