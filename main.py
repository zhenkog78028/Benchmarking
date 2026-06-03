#import sqlite3
import pandas as pd
import ollama
import os
from time import perf_counter_ns
from dotenv import load_dotenv

load_dotenv()
OLLAMA_HOST = os.getenv('OLLAMA_HOST')
client = ollama.Client(host=OLLAMA_HOST) # loading my local ollama server
models = ("gemma3:1b","granite3.3:2b","qwen2.5-coder:1.5b","llama3.2:1b")

'''
connection = sqlite3.connect("example.db")
cursor = connection.cursor()

def benchmarks_from_llms():
    pass

data = benchmarks_from_llms()
df = pd.DataFrame(data)
df.to_sql(name="scores", con=connection)
'''

def benchmark1(llms=models, trials=5):
    data = pd.DataFrame(columns=("model", "success","generation_speed","execution_speed","code"))
    prompt = '''Please write a python function to calculate the n-th prime number.
    Return your answer without any formatting (no backticks) or other explanation text, only the code.
    Your answer should have a function `prime(n)` that takes in n and returns the n-th prime
    '''
    for llm in llms:
        for i in range(trials):
            response = client.chat(model=llm, messages=[{'role': 'user', 'content': prompt, 'stream': 'false'}])
            try:
                generation_time = response.total_duration
                time1 = perf_counter_ns()
                exec(response.message.content) # obvious security risk, need to think of a way around this
                test1 = eval('prime(10)')
                test2 = eval('prime(50)')
                test3 = eval('prime(100)')
                time2 = perf_counter_ns()
                delta = time2-time1
                if(test1 == 29 and test2 == 229 and test3 == 541):
                    data.loc[len(data)] = [llm, 1, generation_time, delta, response.message.content]
                else:
                    data.loc[len(data)] = [llm, 0, generation_time, delta, response.message.content]

            except:
                data.loc[len(data)] = [llm, 0, None, None, None]
    print(data.to_string())
    #data.to_html("output.html")

def main():
    benchmark1(trials=1)

if __name__ == "__main__":
    main()
