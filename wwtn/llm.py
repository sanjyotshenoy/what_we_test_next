"""Calling LLMs on Nebius Token Factory (OpenAI-compatible API).

The key comes from NEBIUS_API_KEY (environment, or a .env file at the repo root); never commit it.
NEBIUS_MODEL picks the default model; `python -m wwtn.llm --models` lists what the key can use.

    from wwtn.llm import chat
    print(chat("Suggest one follow-up experiment for a CRISPR knockout screen."))

    python -m wwtn.llm "your prompt"          # one-off from the command line
    python -m wwtn.llm --models               # list available model IDs

Docs: https://docs.tokenfactory.nebius.com/api-reference
"""
import argparse
import os
from functools import lru_cache

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_URL = os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
DEFAULT_MODEL = os.environ.get("NEBIUS_MODEL", "openai/gpt-oss-120b")

# The models both benchmarks compare (one per lab, a range of sizes); keep in step with MODELS in
# slides/talks/biohack/slides/benchmarks.js. Check they are still served with `python -m wwtn.llm --models`:
# Nebius retires models often (see its deprecation notices).
EVAL_MODELS = [
    "deepseek-ai/DeepSeek-V4-Pro-0813",
    "moonshotai/Kimi-K3",
    "Qwen/Qwen3.8-27B",
    "zai-org/GLM-5.3",
]


@lru_cache(maxsize=1)
def client() -> OpenAI:
    key = os.environ.get("NEBIUS_API_KEY")
    if not key:
        raise RuntimeError("NEBIUS_API_KEY is not set: export it, or put it in .env (see .env.example)")
    return OpenAI(base_url=BASE_URL, api_key=key)


def chat(prompt: str | list[dict], model: str | None = None, system: str | None = None, **kwargs) -> str:
    """One chat completion. `prompt` is a user message, or a full list of {"role", "content"} messages.
    Extra keyword arguments (temperature, max_tokens, ...) go straight to the API."""
    messages = prompt if isinstance(prompt, list) else [{"role": "user", "content": prompt}]
    if system:
        messages = [{"role": "system", "content": system}, *messages]
    response = client().chat.completions.create(model=model or DEFAULT_MODEL, messages=messages, **kwargs)
    return response.choices[0].message.content


def models() -> list[str]:
    """The model IDs this key can call."""
    return sorted(m.id for m in client().models.list())


def main() -> None:
    parser = argparse.ArgumentParser(description="Call an LLM on Nebius Token Factory.")
    parser.add_argument("prompt", nargs="?", help="the user message")
    parser.add_argument("--model", help=f"model ID (default: {DEFAULT_MODEL})")
    parser.add_argument("--system", help="an optional system message")
    parser.add_argument("--models", action="store_true", help="list the available model IDs and exit")
    args = parser.parse_args()
    if args.models:
        print("\n".join(models()))
    elif args.prompt:
        print(chat(args.prompt, model=args.model, system=args.system))
    else:
        parser.error("give a prompt, or --models")


if __name__ == "__main__":
    main()
