#currently, this runs a benchmark for the prompt in config.py and asseses the models in config.py
#this does not create a rubric or prompt yet
#this is the same functionally as the version from a couple weeks ago, but using openrouter and refactored
import pandas as pd

from config import GENERATION_CONFIG, MODELS, DATA_COLUMNS
from execution import run_benchmark
from generation import generate_code

#this could be refactored to be somewhere else, but this is a good level of abstraction for now
def benchmark(llms=MODELS,gen_config=GENERATION_CONFIG):
    #we need a way to display the results
    data = pd.DataFrame(columns=DATA_COLUMNS)

    for llm in llms:
        for i in range(gen_config.trials):
            result = generate_code(gen_config.prime_prompt, gen_config.system_prompt, llm, gen_config.client, attempts=gen_config.attempts)

            run_benchmark(llm, result, data)

    return data

def main():
    #this pretty much runs the test
    outcome = benchmark(config=GENERATION_CONFIG)
    print(outcome.to_string())
    #outcome.to_clipboard()


if __name__ == "__main__":
    main()

#we now need to work on a front end and a way to display the results, and a way to generate prompts and rubrics for different use cases