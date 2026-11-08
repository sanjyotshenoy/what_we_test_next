"""Build the robot status feed from the Opentrons simulator, with per-well liquid tracking.

Runs under the OT-2-capable simulator venv (opentrons 8.8.2; opentrons >= 9 refuses OT-2 protocols):

    .venv-ot2/bin/python harness/stage/build_feed.py PROTOCOL.py OUT.json [--api 2.27] [--reservoir A1=broth,...]

Each feed step: {i, t, dur, depth, kind, text, col?, vol?, src?}. `t` is an *estimated* robot time in seconds
(per-command durations below); the stage page maps it onto the pre-recorded video with cue points (sync.json).
`plates[i]` is the plate after step i: per column (the P300 multi moves 8 rows at once) the volume and the
fraction of each component, so the plate panel can draw fill level and colour.
"""
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

# Estimated seconds per command (a real OT-2 run sets the true pace; the video sync corrects it).
DUR = {"pick_up": 4.0, "drop": 4.0, "aspirate": 2.5, "dispense": 2.0, "mix": 1.0, "pause": 3.0, "comment": 0.5,
       "home": 6.0, "other": 1.0}

RX = {
    "pick_up": re.compile(r"^Picking up tip from (\w+) of (.+)$"),
    "drop": re.compile(r"^Dropping tip"),
    "aspirate": re.compile(r"^Aspirating ([\d.]+) uL from (\w+) of (.+?) on slot (\w+)"),
    "dispense": re.compile(r"^Dispensing ([\d.]+) uL into (?:(\w+) of )?(.+?)(?: on slot (\w+)| at |$)"),
    "mix": re.compile(r"^Mixing (\d+) times with a volume of ([\d.]+)"),
    "pause": re.compile(r"^Pausing"),
    "home": re.compile(r"^Homing"),
}


def classify(text):
    for kind, rx in RX.items():
        m = rx.match(text)
        if m:
            return kind, m
    return ("comment" if text.strip() else "other"), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("protocol")
    ap.add_argument("out")
    ap.add_argument("--api", help="override apiLevel for the simulator (e.g. 2.27); recorded in the feed")
    ap.add_argument("--plate-label", default="P1", help="labware label/name of the assay plate in run-log text")
    ap.add_argument("--reservoir", default="A1=broth,A2=drug,A3=cells",
                    help="reservoir well -> component name")
    args = ap.parse_args()

    from opentrons import simulate  # imported here so --help works without opentrons

    src = Path(args.protocol).read_text()
    original_api = re.search(r'"apiLevel":\s*"([\d.]+)"', src)
    if args.api:
        src = re.sub(r'("apiLevel":\s*")[\d.]+(")', rf"\g<1>{args.api}\g<2>", src)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(src)
        tmp = f.name
    with open(tmp) as fh:
        runlog, _ = simulate.simulate(fh, file_name=Path(args.protocol).name)

    reservoir = dict(kv.split("=") for kv in args.reservoir.split(","))
    components = list(dict.fromkeys(reservoir.values()))
    cols = {c: {k: 0.0 for k in components} for c in range(1, 13)}   # uL per component, per well in column c
    tip = {k: 0.0 for k in components}

    steps, plates, t = [], [], 0.0

    def snapshot():
        out = {}
        for c, comp in cols.items():
            v = sum(comp.values())
            out[c] = {"v": round(v, 1), **{k: round(comp[k] / v, 4) if v else 0 for k in components}}
        return out

    def walk(entries, depth):
        nonlocal t, tip
        for e in entries:
            text = e["payload"].get("text", "")
            kind, m = classify(text)
            step = {"i": len(steps), "t": round(t, 2), "dur": DUR[kind], "depth": depth, "kind": kind, "text": text}
            if kind in ("aspirate", "dispense"):
                vol, well, labware = float(m.group(1)), m.group(2) or "", m.group(3)
                step["vol"] = vol
                on_plate = labware == args.plate_label or labware.startswith(args.plate_label)
                if on_plate:
                    col = int(re.sub(r"\D", "", well))
                    step["col"] = col
                    if kind == "aspirate":
                        well_comp = cols[col]
                        v = sum(well_comp.values()) or 1.0
                        take = {k: well_comp[k] / v * vol for k in components}
                        for k in components:
                            well_comp[k] = max(0.0, well_comp[k] - take[k])
                            tip[k] += take[k]
                    else:
                        tv = sum(tip.values()) or 1.0
                        for k in components:
                            moved = tip[k] / tv * vol
                            cols[col][k] += moved
                            tip[k] = max(0.0, tip[k] - moved)
                else:
                    step["src"] = reservoir.get(well, well or labware)
                    if kind == "aspirate" and well in reservoir:
                        tip[reservoir[well]] += vol
                    elif kind == "dispense":           # back into a reservoir, or into the trash
                        tv = sum(tip.values()) or 1.0
                        tip = {k: max(0.0, tip[k] - tip[k] / tv * vol) for k in components}
            elif kind == "drop":
                tip = {k: 0.0 for k in components}
            steps.append(step)
            t += step["dur"]
            subs = e.get("subcommands", [])
            if subs:
                walk(subs, depth + 1)
            plates.append(snapshot())

    walk(runlog, 0)
    feed = {
        "protocol": Path(args.protocol).name,
        "api_level_original": original_api.group(1) if original_api else None,
        "api_level_simulated": args.api or (original_api.group(1) if original_api else None),
        "simulator": "opentrons " + __import__("opentrons").__version__,
        "components": components,
        "reservoir": reservoir,
        "duration_est_s": round(t, 1),
        "steps": steps,
        "plates": plates,
    }
    Path(args.out).write_text(json.dumps(feed, separators=(",", ":")))
    kinds = {}
    for s in steps:
        kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
    final = plates[-1]
    print(f"{len(steps)} steps, est. {t/60:.1f} min, kinds {kinds}", file=sys.stderr)
    print("final plate (per column):", {c: final[c] for c in (1, 2, 10, 11, 12)}, file=sys.stderr)


if __name__ == "__main__":
    main()
