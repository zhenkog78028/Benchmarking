import importlib.util
import tempfile
import os

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
