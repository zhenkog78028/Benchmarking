import sqlite3
import pandas as pd

connection = sqlite3.connect("example.db")
cursor = connection.cursor()

def benchmarks_from_llms():
    pass

data = benchmarks_from_llms()
df = pd.DataFrame(data)
df.to_sql(name="scores", con=connection)


def main():
    print("Hello from benchmarking!")


if __name__ == "__main__":
    main()
