from dotenv import load_dotenv
from openai import OpenAI
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class GenerationConfig:
    prime_prompt: str
    system_prompt: str
    client: object
    trials: int
    attempts: int

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

MODELS = (
    "openai/gpt-oss-120b:free",
    "cohere/north-mini-code:free",
)

DATA_COLUMNS = (
    "model",
    "success",
    "generation_speed",
    "execution_speed",
    "code",
)

PRIME_PROMPT = """Please write a python function to calculate the n-th prime number.
Return your answer without any formatting (no backticks) or other explanation text, only the code.
Your answer should have a function `prime(n)` that takes in n and returns the n-th prime
"""

SYSTEM_PROMPT = """You are a code generator. Output ONLY raw code.
Do not include markdown code blocks (backticks), explanations, or 'Sure, here is your code' style introductions."""

#doing this to improve tracability from main.py, without polluting main.py with too many variables
GENERATION_CONFIG = GenerationConfig(
    prime_prompt=PRIME_PROMPT,
    system_prompt=SYSTEM_PROMPT,
    client=CLIENT,
    trials=1,
    attempts=3,
)