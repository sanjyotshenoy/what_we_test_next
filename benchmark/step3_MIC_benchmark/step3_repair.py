#!/usr/bin/env python
"""Self-repair round for protocols that fail the gate.

The model sees the same conversation it had (prompt + its own answer), then the simulator's error message,
and returns a corrected protocol. Repeat until the protocol passes the gate or --max-rounds is reached.
Each round is saved as sample1.fix<k>.{md,py,json} with token usage and cost; the scorer later takes off
5 points (out of 100) per round used.

Gate = Opentrons' analyzer (opentrons 8.8.2) has no errors, robotType is OT-2, and only 8-channel pipettes
are loaded (the prompt's labware list has an 8-channel pipette only).

Usage: python step3_repair.py --otpython <python with opentrons 8.8.2> [--models a,b] [--max-rounds 3]
"""

import argparse
import concurrent.futures as cf
import json
import os
import re
import subprocess
import tempfile
import time

from step3_generate import HERE, MODELS, call, env, extract_code, stream_chat

REPAIR_MSG = ("I ran this protocol in the Opentrons OT-2 simulator and it failed with this error:\n\n{error}\n\n"
              "Please fix it and give me the complete corrected protocol.")


def gate(py, otpython):
  """-> None if the protocol passes, else the error message a user would see."""
  src = open(py).read()
  if re.search(r"^\s*(?:import|from)\s+(?:os|sys|subprocess|socket|shutil|requests|urllib|http|ctypes|pathlib)\b",
               src, re.M) or re.search(r"\b(?:eval|exec|__import__)\s*\(", src):
    raise RuntimeError(f"{py} imports system/network modules: not run automatically, review it by hand")
  m = re.search(r"""["']apiLevel["']\s*:\s*["'](\d+)\.(\d+)["']""", src)
  if m and (int(m.group(1)), int(m.group(2))) > (2, 27):
    src = src[:m.start()] + '"apiLevel": "2.27"' + src[m.end():]
  with tempfile.TemporaryDirectory() as d:
    p, out = os.path.join(d, "protocol.py"), os.path.join(d, "analysis.json")
    open(p, "w").write(src)
    r = subprocess.run([otpython, "-m", "opentrons.cli", "analyze", "--json-output", out, p],
                       capture_output=True, text=True, timeout=600)
    if not os.path.exists(out):
      return (r.stderr or r.stdout)[-1500:]
    a = json.load(open(out))
  if a.get("errors"):
    return a["errors"][0].get("detail", str(a["errors"][0]))[:1500]
  if a.get("robotType", "OT-2 Standard") != "OT-2 Standard":
    return f"This protocol is for robotType {a.get('robotType')}, not the OT-2."
  for c in a["commands"]:
    if c["commandType"] == "loadPipette" and "multi" not in c["params"]["pipetteName"]:
      prm = c["params"]
      return (f"The robot run cannot start: the protocol requires a {prm['pipetteName']} on the {prm['mount']} mount, "
              "but that pipette is not attached. Only the 8-channel pipette from the labware requirements is available.")
  return None


def repair(name, otpython, max_rounds, base, key, prices):
  d = os.path.join(HERE, "candidates_step3", name)
  prompt = open(os.path.join(HERE, "tasks", "step3_prompt.txt")).read()
  messages = [{"role": "user", "content": prompt},
              {"role": "assistant", "content": open(os.path.join(d, "sample1.md")).read()}]
  py = os.path.join(d, "sample1.py")
  log = []
  err = gate(py, otpython)
  for k in range(1, max_rounds + 1):
    if err is None:
      break
    messages.append({"role": "user", "content": REPAIR_MSG.format(error=err)})
    body = {"model": MODELS[name], "messages": messages, "max_tokens": 32000, "reasoning_effort": "high"}
    t0 = time.time()
    content, reasoning, usage, finish = stream_chat(base, key, body)
    p = prices.get(MODELS[name], {})
    cost = usage.get("prompt_tokens", 0) * float(p.get("prompt", 0)) + \
           usage.get("completion_tokens", 0) * float(p.get("completion", 0))
    stem = os.path.join(d, f"sample1.fix{k}")
    open(stem + ".md", "w").write(content)
    if reasoning:
      open(stem + ".reasoning.md", "w").write(reasoning)
    code = extract_code(content)
    if code:
      open(stem + ".py", "w").write(code)
      py = stem + ".py"
    new_err = gate(py, otpython) if code else "no protocol code in the answer"
    entry = {"round": k, "error_fed_back": err, "seconds": round(time.time() - t0, 1), "usage": usage,
             "finish_reason": finish, "cost_usd": round(cost, 6), "code_extracted": bool(code),
             "passes_after": new_err is None, "error_after": new_err}
    json.dump(entry, open(stem + ".json", "w"), indent=1)
    log.append(entry)
    messages.append({"role": "assistant", "content": content})
    err = new_err
  return {"model": name, "rounds": len(log), "passes": err is None, "final_protocol": py, "log": log}


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--otpython", required=True)
  ap.add_argument("--models", default=",".join(MODELS))
  ap.add_argument("--max-rounds", type=int, default=3)
  a = ap.parse_args()
  key, base = env()
  listing = json.load(call(base, key, "/models?verbose=true"))
  prices = {m["id"]: m.get("pricing", {}) for m in listing.get("data", [])}
  names = a.models.split(",")
  with cf.ThreadPoolExecutor(max_workers=len(names)) as ex:
    res = list(ex.map(lambda n: repair(n, a.otpython, a.max_rounds, base, key, prices), names))
  for r in res:
    cost = sum(x["cost_usd"] for x in r["log"])
    print(f"{r['model']}: rounds={r['rounds']} passes={r['passes']} repair_cost=${cost:.4f} final={r['final_protocol']}")
    for x in r["log"]:
      print(f"   round {x['round']}: fed back: {x['error_fed_back'][:140]!r} -> passes={x['passes_after']}")
  json.dump(res, open(os.path.join(HERE, "candidates_step3", "repairs.json"), "w"), indent=1)


if __name__ == "__main__":
  main()
