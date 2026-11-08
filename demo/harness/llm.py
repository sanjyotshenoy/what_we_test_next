"""LLM access for the live harness: pluggable providers + event hooks.

Providers (OpenAI-compatible):
    nebius   Nebius Token Factory; key NEBIUS_API_KEY (demo/.env)
    local    external OpenAI-compatible endpoint; key HARNESS_LOCAL_KEY

HARNESS_LLM sets the order tried, e.g. "nebius,local" (default): if a call to one provider fails
(network, 5xx, auth, missing key) the next one is tried, and the switch is reported to the hooks,
so the stage UI can show it instead of hiding it.

Hooks: register a callable with `add_hook(fn)`; it receives one dict per event:
    {"event": "start"|"end"|"fallback"|"error", "provider", "model", "latency_s", "usage", "error", ...}
Use them for the on-screen trace, logging and cost accounting.

    from demo.harness.llm import chat, add_hook
    add_hook(print)
    reply = chat("Does imatinib inhibit KIT?", system="...", temperature=0.2)

    python -m demo.harness.llm --check          # which providers are configured and reachable
    python -m demo.harness.llm --models nebius  # model IDs a provider serves
    python -m demo.harness.llm "prompt" [--provider local] [--model ...]
"""
from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from openai import OpenAI

from demo.harness.paths import ROOT, DEMO
# Earlier files win: load_dotenv never overrides variables that are already set.
load_dotenv(DEMO / ".env")


def _read(path: Path) -> str | None:
    try:
        return path.read_text().strip() or None
    except OSError:
        return None


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    default_model: str
    key_fn: Callable[[], str | None]
    extra_body: dict | None = None   # merged into every request (e.g. thinking switch)

    def key(self) -> str | None:
        return self.key_fn()


PROVIDERS: dict[str, Provider] = {
    "nebius": Provider(
        name="nebius",
        base_url=os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"),
        default_model=os.environ.get("HARNESS_NEBIUS_MODEL", os.environ.get("NEBIUS_MODEL", "openai/gpt-oss-120b")),
        key_fn=lambda: os.environ.get("NEBIUS_API_KEY"),
    ),
    "local": Provider(
        name="local",
        base_url=os.environ.get("HARNESS_LOCAL_URL", "http://127.0.0.1:18300/v1"),
        default_model="qwen3.8-flash-next",
        key_fn=lambda: os.environ.get("HARNESS_LOCAL_KEY"),
    ),
}

_hooks: list[Callable[[dict], None]] = []


def add_hook(fn: Callable[[dict], None]) -> None:
    _hooks.append(fn)


def remove_hook(fn: Callable[[dict], None]) -> None:
    _hooks.remove(fn)


def _emit(**event: Any) -> None:
    for fn in list(_hooks):
        try:
            fn(event)
        except Exception:      # a broken UI hook must never break the pipeline on stage
            pass


def order() -> list[str]:
    names = [n.strip() for n in os.environ.get("HARNESS_LLM", "nebius,local").split(",") if n.strip()]
    unknown = [n for n in names if n not in PROVIDERS]
    if unknown:
        raise ValueError(f"unknown provider(s) in HARNESS_LLM: {unknown}; known: {list(PROVIDERS)}")
    return names


@lru_cache(maxsize=None)
def client(name: str) -> OpenAI:
    p = PROVIDERS[name]
    key = p.key()
    if not key:
        raise RuntimeError(f"provider {name!r} has no API key configured")
    return OpenAI(base_url=p.base_url, api_key=key, timeout=float(os.environ.get("HARNESS_LLM_TIMEOUT", 120)), max_retries=0)


def complete(messages: list[dict], model: str | None = None, provider: str | None = None, **kwargs: Any):
    """One chat completion; returns (response, provider_name). `model` applies to the first provider only
    (model IDs differ between providers); fallbacks use their own default model.
    Extra kwargs (tools, temperature, max_tokens, stream, ...) go to the API unchanged."""
    names = [provider] if provider else order()
    user_body = kwargs.pop("extra_body", None) or {}
    last: Exception | None = None
    for i, name in enumerate(names):
        p = PROVIDERS[name]
        use_model = model if (model and i == 0) else p.default_model
        body = {**(p.extra_body or {}), **user_body} or None
        _emit(event="start", provider=name, model=use_model)
        t = time.monotonic()
        try:
            resp = client(name).chat.completions.create(model=use_model, messages=messages, extra_body=body, **kwargs)
        except Exception as e:  # noqa: BLE001 - any failure moves to the next provider
            last = e
            _emit(event="error", provider=name, model=use_model, latency_s=time.monotonic() - t, error=repr(e))
            if i + 1 < len(names):
                _emit(event="fallback", provider=name, to=names[i + 1], error=repr(e))
            continue
        usage = getattr(resp, "usage", None)
        _emit(event="end", provider=name, model=use_model, latency_s=time.monotonic() - t,
              usage=usage.model_dump() if usage else None)
        return resp, name
    raise RuntimeError(f"all LLM providers failed ({names}): {last!r}") from last


def chat(prompt: str | list[dict], model: str | None = None, system: str | None = None,
         provider: str | None = None, **kwargs: Any) -> str:
    """Text in, text out (same shape as wwtn.llm.chat, plus provider fallback and hooks)."""
    messages = prompt if isinstance(prompt, list) else [{"role": "user", "content": prompt}]
    if system:
        messages = [{"role": "system", "content": system}, *messages]
    resp, _ = complete(messages, model=model, provider=provider, **kwargs)
    return resp.choices[0].message.content or ""


def check() -> dict[str, str]:
    """Per provider: 'ok (<n> models)', 'no key', or the error. Costs no tokens (lists models)."""
    out = {}
    for name in PROVIDERS:
        if not PROVIDERS[name].key():
            out[name] = "no key"
            continue
        try:
            n = len(client(name).with_options(timeout=10).models.list().data)
            out[name] = f"ok ({n} models)"
        except Exception as e:  # noqa: BLE001
            out[name] = f"unreachable: {type(e).__name__}: {e}"[:200]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Harness LLM providers (Nebius, local Qwen).")
    ap.add_argument("prompt", nargs="?")
    ap.add_argument("--provider", choices=list(PROVIDERS))
    ap.add_argument("--model")
    ap.add_argument("--system")
    ap.add_argument("--check", action="store_true", help="show which providers are configured and reachable")
    ap.add_argument("--models", metavar="PROVIDER", choices=list(PROVIDERS), help="list a provider's model IDs")
    args = ap.parse_args()
    if args.check:
        print(f"order: {order()}")
        for name, status in check().items():
            print(f"  {name:7s} {PROVIDERS[name].base_url}  default={PROVIDERS[name].default_model}  -> {status}")
    elif args.models:
        print("\n".join(sorted(m.id for m in client(args.models).models.list())))
    elif args.prompt:
        add_hook(lambda e: e["event"] != "start" and print(f"[{e['event']}] {e}", flush=True))
        print(chat(args.prompt, model=args.model, system=args.system, provider=args.provider))
    else:
        ap.error("give a prompt, --check or --models")


if __name__ == "__main__":
    main()
