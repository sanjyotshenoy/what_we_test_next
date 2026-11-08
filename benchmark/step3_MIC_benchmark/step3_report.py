#!/usr/bin/env python
"""Build the English before/after benchmark report for the step-3 MIC task.

Before = original gate rule (any simulator error -> 0).
After  = errors fed back to the model, up to 3 repair rounds, -5 points (out of 100) per round used.
Cost   = first answer + every repair round, at Nebius list prices.

Inputs: candidates_step3/results.json (scores of the first answers + standard answer),
        candidates_step3/results_after.json (scores of the repaired protocols),
        candidates_step3/repairs.json, candidates_step3/<model>/sample1.json
Outputs: candidates_step3/benchmark_before_after.md and leaderboard.csv
"""

import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "candidates_step3")
NAMES = {"kimi-k3.1-pro": "Kimi K3.1 Pro", "glm-5.3": "GLM 5.3", "deepseek-v4.1-flash-1017": "DeepSeek V4.1 Flash 1017",
         "nemotron-3-super": "Nemotron 3 Super", "gpt-oss-120b": "GPT-OSS-120B"}
ROWS = [("plate_layout", "Plate layout", 2), ("dilution_series", "Two-fold dilution series", 2),
        ("controls", "Growth / sterility controls", 2), ("final_volume_ratio", "Final volume and inoculum ratio", 1),
        ("eight_channel", "8-channel addressing", 2), ("contamination", "Cross-contamination", 2),
        ("max_300", "Well volume <= 300 uL", 1), ("plate_slot", "MIC plate not in slots 1-3", 2),
        ("tip_balance", "Tip box balanced", 0.5), ("labware_close", "Labware close together", 0.5),
        ("mixing", "Mixing", 1), ("reservoir_volumes", "Reservoir volumes", 1.5),
        ("operator_instructions", "Operator instructions", 0.5), ("tip_choice", "Tip choice for volumes", 0.5),
        ("run_time", "Estimated run time", 1), ("tip_count", "Tip count estimate", 1)]


def model_of(path):
  return os.path.basename(os.path.dirname(path))


def main():
  before = {model_of(r["protocol"]): r for r in json.load(open(os.path.join(D, "results.json")))
            if "candidates_step3" in r["protocol"]}
  gold = next(r for r in json.load(open(os.path.join(D, "results.json"))) if "standard_answer" in r["protocol"])
  after_scores = {model_of(r["protocol"]): r for r in json.load(open(os.path.join(D, "results_after.json")))
                  if "candidates_step3" in r["protocol"]}
  repairs = {r["model"]: r for r in json.load(open(os.path.join(D, "repairs.json")))}
  notes = json.load(open(os.path.join(D, "notes.json"))) if os.path.exists(os.path.join(D, "notes.json")) else {}

  rows = []
  for m, nice in NAMES.items():
    gen = json.load(open(os.path.join(D, m, "sample1.json")))
    b = before[m]
    rep = repairs.get(m, {"rounds": 0, "passes": b["gate"] == 1, "log": []})
    a = after_scores.get(m, b) if rep["passes"] else None
    rounds = rep["rounds"]
    after_raw = round(a["reward"] * 100, 1) if a else 0.0
    after = max(0.0, round(after_raw - 5 * rounds, 1)) if a else 0.0
    fix_cost = sum(x["cost_usd"] for x in rep["log"])
    rows.append({
      "Model": nice, "Nebius model ID": gen["model_id"],
      "Before: gate": "pass" if b["gate"] else "fail", "Before: score /100": round(b["reward"] * 100, 1),
      "Repair rounds": rounds, "After: gate": "pass" if a else "fail",
      "After: rubric /100": after_raw, "Repair penalty": -5 * rounds if a else "", "After: score /100": after,
      "First answer cost (USD)": round(gen["cost_usd"], 4), "Repair cost (USD)": round(fix_cost, 4),
      "Total cost (USD)": round(gen["cost_usd"] + fix_cost, 4),
      "Output tokens (all calls)": gen["usage"].get("completion_tokens", 0) +
                                   sum(x["usage"].get("completion_tokens", 0) for x in rep["log"]),
      "Est. run time (min)": (a or {}).get("evidence", {}).get("run_time", {}).get("minutes", ""),
      "_after": a, "_before": b, "_rep": rep, "_note": notes.get(m, ""),
    })
  rows.sort(key=lambda r: (-r["After: score /100"], r["Total cost (USD)"]))

  cols = [c for c in rows[0] if not c.startswith("_")]
  with open(os.path.join(D, "leaderboard.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols + ["Notes"])
    w.writeheader()
    for r in rows:
      w.writerow({**{c: r[c] for c in cols}, "Notes": r["_note"]})

  L = []
  L.append("# MIC benchmark on Nebius models: before and after the repair rule\n")
  L.append("Task: the step-3 prompt, word for word, one sample per model, reasoning effort high. "
           "Scored with `rubrics/step3_rubric.csv` (16 weighted rows, total weight 20.5, shown here out of 100).\n")
  L.append("| | Before | After |\n|---|---|---|")
  L.append("| Simulator error | Whole protocol scores 0 | Error message goes back to the model, which returns a fix "
           "(up to 3 rounds). Each round used: -5 points. Still failing after 3 rounds: 0 |")
  L.append("| Cost | First answer only | First answer + every repair round |\n")
  L.append("## Results\n")
  L.append("| Model | Before | Repair rounds | After: rubric | Penalty | **After: score** | First answer | Repairs | **Total cost** |")
  L.append("|---|---|---|---|---|---|---|---|---|")
  for r in rows:
    pen = f"{r['Repair penalty']}" if r["Repair penalty"] not in ("", 0) else "0"
    L.append(f"| {r['Model']} | {r['Before: score /100']:.1f} ({r['Before: gate']}) | {r['Repair rounds']} | "
             f"{r['After: rubric /100']:.1f} | {pen} | **{r['After: score /100']:.1f}** ({r['After: gate']}) | "
             f"${r['First answer cost (USD)']:.4f} | ${r['Repair cost (USD)']:.4f} | **${r['Total cost (USD)']:.4f}** |")
  tot = sum(r["Total cost (USD)"] for r in rows)
  L.append(f"| Standard answer (reference) | {gold['reward'] * 100:.1f} (pass) | 0 | {gold['reward'] * 100:.1f} | 0 | "
           f"**{gold['reward'] * 100:.1f}** | | | |")
  L.append(f"\nTotal spent on Nebius: **${tot:.4f}**. Costs = Nebius list price x tokens the API reported. Each repair "
           "call resends the whole conversation, so input tokens grow every round. Cached input tokens are counted at "
           "full price, so repair costs are an upper bound.\n")

  L.append("## Repair rounds\n")
  for r in rows:
    if not r["_rep"]["log"]:
      continue
    L.append(f"**{r['Model']}**\n")
    for x in r["_rep"]["log"]:
      L.append(f"- Round {x['round']} (${x['cost_usd']:.4f}): fed back `{x['error_fed_back'][:160].strip()}` "
               f"-> {'passes' if x['passes_after'] else 'still fails: `' + (x['error_after'] or '')[:120].strip() + '`'}")
    L.append("")

  L.append("## Rubric rows after repair (0 / 0.5 / 1)\n")
  live = [r for r in rows if r["_after"]]
  L.append("| Row | Weight | " + " | ".join(r["Model"] for r in live) + " | Standard answer |")
  L.append("|---|---|" + "---|" * (len(live) + 1))
  for key, label, w in ROWS:
    cells = [str(r["_after"]["scores"].get(key)) for r in live]
    L.append(f"| {label} | {w} | " + " | ".join(cells) + f" | {gold['scores'].get(key)} |")
  L.append("")
  L.append("## Notes per model\n")
  for r in rows:
    if r["_note"]:
      L.append(f"- **{r['Model']}**: {r['_note']}")
  open(os.path.join(D, "benchmark_before_after.md"), "w").write("\n".join(L) + "\n")
  print("\n".join(L))


if __name__ == "__main__":
  main()
