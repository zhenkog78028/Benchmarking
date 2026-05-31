#import sqlite3
import pandas as pd
import ollama
import os
from dotenv import load_dotenv

load_dotenv()
OLLAMA_HOST = os.getenv('OLLAMA_HOST')
client = ollama.Client(host=OLLAMA_HOST) # loading my local ollama server
models = ("codegemma:2b","granite3.3:2b","qwen2.5-coder:1.5b","llama3.2:1b")

'''
connection = sqlite3.connect("example.db")
cursor = connection.cursor()

def benchmarks_from_llms():
    pass

data = benchmarks_from_llms()
df = pd.DataFrame(data)
df.to_sql(name="scores", con=connection)
'''

def main():
    answers = {}
    for llm in models:
        response = client.chat(model=llm, messages=[
            {
            'role': 'user',
            'content': 'Hi, how are you?',
            'stream': 'false'
            },
        ])
        answers[llm]=response.message.content
    data = pd.DataFrame([answers])
    print(data.to_string())


if __name__ == "__main__":
    main()
