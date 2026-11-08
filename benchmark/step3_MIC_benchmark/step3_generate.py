#!/usr/bin/env python
"""Send the step-3 MIC prompt, unchanged, to models on Nebius Token Factory and save their answers.

For each model: raw answer (.md), extracted protocol (.py) and metadata with token usage and cost (.json),
in candidates_step3/<model>/sample<k>.*. Prices come from Nebius's own /v1/models listing.
The API key is read from .env (NEBIUS_API_KEY) and never printed.

Usage:  python step3_generate.py [--samples 1] [--models id1,id2,...]
"""

import argparse
import concurrent.futures as cf
import json
import os
import re
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = {
  "kimi-k3.1-pro": "moonshotai/Kimi-K3.1-Pro",
  "glm-5.3": "zai-org/GLM-5.3",
  "deepseek-v4.1-flash-1017": "deepseek-ai/DeepSeek-V4.1-Flash-1017",
  "nemotron-3-super": "nvidia/nemotron-3-super-120b-a12b",
  "gpt-oss-120b": "openai/gpt-oss-120b",
}


def env():
  e = dict(l.strip().split("=", 1) for l in open(os.path.join(HERE, ".env")) if "=" in l)
  return e["NEBIUS_API_KEY"], e.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/").rstrip("/")


def call(base, key, path, body=None, timeout=60):
  req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body else None,
                               headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
  return urllib.request.urlopen(req, timeout=timeout)


def stream_chat(base, key, body):
  """Streamed chat completion -> (content, reasoning, usage, finish_reason)."""
  body = dict(body, stream=True, stream_options={"include_usage": True})
  content, reasoning, usage, finish = [], [], None, None
  with call(base, key, "/chat/completions", body, timeout=1800) as r:
    for raw in r:
      line = raw.decode("utf-8", "replace").strip()
      if not line.startswith("data:"):
        continue
      data = line[5:].strip()
      if data == "[DONE]":
        break
      ev = json.loads(data)
      if ev.get("usage"):
        usage = ev["usage"]
      for ch in ev.get("choices") or []:
        d = ch.get("delta") or {}
        content.append(d.get("content") or "")
        reasoning.append(d.get("reasoning_content") or d.get("reasoning") or "")
        finish = ch.get("finish_reason") or finish
  return "".join(content), "".join(reasoning), usage or {}, finish


def extract_code(text):
  blocks = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", text, re.S)
  runs = [b for b in blocks if re.search(r"^\s*def run\s*\(", b, re.M)]
  return max(runs, key=len) if runs else None


def run_one(name, mid, k, prompt, prices, base, key, outdir):
  body = {"model": mid, "messages": [{"role": "user", "content": prompt}],
          "max_tokens": 32000, "reasoning_effort": "high"}
  t0 = time.time()
  effort = "high"
  try:
    content, reasoning, usage, finish = stream_chat(base, key, body)
  except urllib.error.HTTPError as e:
    msg = e.read().decode("utf-8", "replace")[:300]
    if e.code in (400, 422) and "reasoning" in msg.lower():  # model does not take reasoning_effort
      body.pop("reasoning_effort")
      effort = "not supported (model default)"
      content, reasoning, usage, finish = stream_chat(base, key, body)
    else:
      raise RuntimeError(f"HTTP {e.code}: {msg}") from None
  secs = time.time() - t0
  p = prices.get(mid, {})
  pin, pout = float(p.get("prompt", 0)), float(p.get("completion", 0))
  ptok, ctok = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
  code = extract_code(content)
  d = os.path.join(outdir, name)
  os.makedirs(d, exist_ok=True)
  stem = os.path.join(d, f"sample{k}")
  with open(stem + ".md", "w") as f:
    f.write(content)
  if reasoning:
    with open(stem + ".reasoning.md", "w") as f:
      f.write(reasoning)
  if code:
    with open(stem + ".py", "w") as f:
      f.write(code)
  meta = {"model": name, "model_id": mid, "sample": k, "reasoning_effort": effort, "finish_reason": finish,
          "seconds": round(secs, 1), "usage": usage,
          "price_per_token": {"input": pin, "output": pout},
          "cost_usd": round(ptok * pin + ctok * pout, 6), "code_extracted": bool(code)}
  with open(stem + ".json", "w") as f:
    json.dump(meta, f, indent=1)
  return meta


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--samples", type=int, default=1)
  ap.add_argument("--models", default=",".join(MODELS))
  ap.add_argument("--out", default=os.path.join(HERE, "candidates_step3"))
  a = ap.parse_args()
  key, base = env()
  prompt = open(os.path.join(HERE, "tasks", "step3_prompt.txt")).read()
  listing = json.load(call(base, key, "/models?verbose=true"))
  prices = {m["id"]: m.get("pricing", {}) for m in listing.get("data", [])}
  jobs = [(n, MODELS[n], k) for n in a.models.split(",") for k in range(1, a.samples + 1)]
  with cf.ThreadPoolExecutor(max_workers=len(jobs)) as ex:
    futs = {ex.submit(run_one, n, mid, k, prompt, prices, base, key, a.out): (n, k) for n, mid, k in jobs}
    for f in cf.as_completed(futs):
      n, k = futs[f]
      try:
        m = f.result()
        u = m["usage"]
        print(f"{n} sample{k}: {m['seconds']}s, in {u.get('prompt_tokens')} / out {u.get('completion_tokens')} tokens, "
              f"${m['cost_usd']:.4f}, finish={m['finish_reason']}, effort={m['reasoning_effort']}, code={m['code_extracted']}",
              flush=True)
      except Exception as e:  # noqa: BLE001
        print(f"{n} sample{k}: ERROR {e}", flush=True)


if __name__ == "__main__":
  main()
