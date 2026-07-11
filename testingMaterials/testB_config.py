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
    #"openai/gpt-oss-120b:free",
    "cohere/north-mini-code:free",
)

DATA_COLUMNS = (
    "model",
    "success",
    "generation_speed",
    "execution_speed",
    "output",
)

PRIME_PROMPT_PROMPT = """You will be given an use case below. Based on the use case, generate a prompt that will be used to generate code for this use case used to benchmark various language models. The prompt should be clear, concise, and provide enough context for the model to understand the problem. The outcomes from this prompt should be plain text, which will be automatically ran in a single file of the appropriate language, so make sure the scope of the benchmark is appropriate and include formatting instructions. The prompt should also specify the programming language to be used and any specific requirements or constraints that should be considered when generating the code. The prompt should be written in a way that encourages the model to generate a solution that is efficient, effective, and adheres to best practices in software development. The use case is as follows: {issue}."""

SYSTEM_PROMPT_PROMPT = """You are in charge of creating benchmarks for other AI models to solve coding problems. Based on the provided issues, you need to return a prompt, and only a prompt, that can be read by a variety of languange models. Do not include markdown formatting (avoid using asterisks for bold, and etc.), unecessary explanations, or 'Sure, here is your prompt' style introductions. Make sure your benchmarks are reasonable in scope, meaning it can be ran in a single file."""

