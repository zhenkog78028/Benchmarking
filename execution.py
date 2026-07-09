import importlib.util
import tempfile
import os
from time import perf_counter_ns

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

def run_benchmark(llm, result, data):
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