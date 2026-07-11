import sys
import os

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Get the parent (super) directory
parent_dir = os.path.dirname(current_dir)

# Add the parent directory to sys.path so Python can find it
sys.path.append(parent_dir)

#gets prompt, then gets rubric
import pandas as pd

from testB_config import MODELS, DATA_COLUMNS, PRIME_PROMPT_PROMPT, CLIENT, SYSTEM_PROMPT_PROMPT, GenerationConfig
from execution import run_benchmark
from generation import generate_code
#from dataclasses import dataclass

#this could be refactored to be somewhere else, but this is a good level of abstraction for now
def benchmark(llms, gen_config):
    #we need a way to display the results
    data = pd.DataFrame(columns=DATA_COLUMNS)

    for llm in llms:
        for _ in range(gen_config.trials):
            #generates code using the prompt and system prompt from config.py, and the model specified in llm
            result = generate_code(gen_config.prime_prompt, gen_config.system_prompt, llm, gen_config.client, attempts=gen_config.attempts)
            
            #runs the code, only records time
            run_benchmark(llm, result, data)

    return data

def main():
    issue = input("Enter your issue: ")

    #gets prompt generation parameters
    prompt_config = GenerationConfig(
        prime_prompt=PRIME_PROMPT_PROMPT.format(issue = issue),
        system_prompt=SYSTEM_PROMPT_PROMPT,
        client= CLIENT,
        trials=1,
        attempts=3,
    )
    #this pretty much runs the test
    outcome = benchmark(MODELS, prompt_config)
    print(outcome.loc[0, "output"])
    #outcome.to_clipboard()



print("starting")
main()

#we now need to work on a front end and a way to display the results, and a way to generate prompts and rubrics for different use cases