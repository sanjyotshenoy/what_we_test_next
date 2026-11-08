#!/usr/bin/env python
"""Score Opentrons OT-2 protocols for the step-3 MIC task against rubrics/step3_rubric.csv.

Pipeline per protocol:
  1. Gate: Opentrons' own analyzer (`python -m opentrons.cli analyze`, opentrons 8.8.2 = last PyPI release
     that simulates OT-2; apiLevel above 2.27 is lowered to 2.27 for the simulation only).
  2. The analyzer's command list (every pickUpTip / aspirate / dispense, after transfer() & mix() are expanded)
     is replayed nozzle by nozzle: which nozzles carry tips (incl. partly filled racks), which wells each nozzle
     reaches, liquid composition of every well, what each tip has touched (contamination), mixing, volumes.
  3. Rubric rows are scored from those measurements. Rows that need reading the protocol's text
     (operator instructions, a tip count the protocol states) come from <sample>.config.json "manual".

Per-sample config (<sample>.config.json, optional):
  "empty_tips": {"6": ["B2", "C2", ...]}      rack positions the protocol tells the operator to leave empty
  "liquids": {"3:A2": ["Abx1", 2000]}          reservoir wells the protocol uses but never declares
  "stock_fold": 2                              stock = N x top final concentration, as the protocol states (default 2)
  "manual": {"operator_instructions": {"score": 1, "why": "..."}, "tip_count_stated": {"score": 1, "why": "..."}}

Run with the Python that has opentrons 8.8.2 installed:
  <otenv>/bin/python step3_score.py candidates_step3/*/sample1.py --gold <gold.py> --out results.json
"""

import argparse
import glob
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict

from opentrons.protocols.labware import get_labware_definition

MAX_API = (2, 27)
ROWS = "ABCDEFGH"
TIME = {"pickup": 6.0, "drop": 5.0, "asp_disp": 2.0, "mix_cmd": 1.0, "other": 1.0}
DEAD_VOL = {"trough": 1000.0, "plate": 50.0}  # uL left behind in a source well
MIN_VOL = {"p300_multi": 30, "p300_multi_gen2": 30, "p300_single": 30, "p300_single_gen2": 30,
           "p20_multi_gen2": 1, "p20_single_gen2": 1}
WEIGHTS = {  # rubric row -> weight (rubrics/step3_rubric.csv)
  "plate_layout": 2, "dilution_series": 2, "controls": 2, "final_volume_ratio": 1, "eight_channel": 2,
  "contamination": 2, "max_300": 1, "plate_slot": 2, "tip_balance": 0.5, "labware_close": 0.5, "mixing": 1,
  "reservoir_volumes": 1.5, "operator_instructions": 0.5, "tip_choice": 0.5, "run_time": 1, "tip_count": 1,
}
ROW_NAMES = {
  "gate": "Runs without errors", "plate_layout": "Plate layout: 4 antibiotics x 2 replicate rows",
  "dilution_series": "Two-fold dilution series", "controls": "Growth and sterility controls",
  "final_volume_ratio": "Final volume and inoculum ratio", "eight_channel": "8-channel: each antibiotic reaches only its own rows",
  "contamination": "No cross-contamination", "max_300": "Well volume never above 300 uL",
  "plate_slot": "MIC plate not in slots 1-3", "tip_balance": "Tip box balanced", "labware_close": "Labware close together",
  "mixing": "Mixing after dilution and after bacteria", "reservoir_volumes": "Reservoir volumes cover an 8-channel draw",
  "operator_instructions": "Operator instructions", "tip_choice": "Pipette / tip choice for volumes",
  "run_time": "Estimated run time", "tip_count": "Tip count estimate",
}


def canon(name):
  n = name.lower()
  m = re.search(r"(?:antibiotic|abx|drug|compound)\s*[_#-]?\s*(\d)", n)
  if m:
    return f"Abx{m.group(1)}"
  if any(s in n for s in ("bacteri", "inocul", "culture", "cells", "strain", "cfu")):
    return "Bacteria"
  if any(s in n for s in ("media", "medium", "broth", "mhb", "camhb", " lb", "diluent", "water")) or n == "lb":
    return "Media"
  return name


# ----------------------------------------------------------------------------------------------
# 1. Gate: Opentrons analyzer
# ----------------------------------------------------------------------------------------------

def analyze(py_path, workdir):
  src = open(py_path).read()
  note = None
  m = re.search(r"""["']apiLevel["']\s*:\s*["'](\d+)\.(\d+)["']""", src)
  if m and (int(m.group(1)), int(m.group(2))) > MAX_API:
    note = f"apiLevel {m.group(1)}.{m.group(2)} lowered to 2.27 for simulation"
    src = src[:m.start()] + '"apiLevel": "2.27"' + src[m.end():]
  def run_analyzer(text, tag):
    tmp = os.path.join(workdir, f"protocol_{tag}.py")
    open(tmp, "w").write(text)
    out = os.path.join(workdir, f"analysis_{tag}.json")
    p = subprocess.run([sys.executable, "-m", "opentrons.cli", "analyze", "--json-output", out, tmp],
                       capture_output=True, text=True, timeout=600)
    if not os.path.exists(out):
      return None, (p.stderr or p.stdout)[-1500:]
    return json.load(open(out)), None

  a, crash = run_analyzer(src, "orig")
  if a is None or a.get("errors"):
    return a, note, crash
  # apiLevel < 2.14 runs on the legacy core, whose analysis reports every location as "top of well, 0 mm":
  # the gate stays at the protocol's own level, but tip heights for the replay come from a 2.14 copy
  if m and (int(m.group(1)), int(m.group(2))) < (2, 14):
    b, _ = run_analyzer(src[:m.start()] + '"apiLevel": "2.14"' + src[m.end():], "214")
    if b is not None and not b.get("errors"):
      note = f"passes at apiLevel {m.group(1)}.{m.group(2)}; replayed at 2.14 because older levels do not report tip heights"
      return b, note, None
  return a, note, None


# ----------------------------------------------------------------------------------------------
# 2. Replay
# ----------------------------------------------------------------------------------------------

class Labware:
  def __init__(self, load_name, slot, version):
    self.load_name, self.slot = load_name, str(slot)
    d = get_labware_definition(load_name, "opentrons", version)
    self.is_tiprack = d["parameters"].get("isTiprack", False)
    self.ordering = d["ordering"]  # columns of well names
    self.wells = d["wells"]
    self.single_row = all(len(col) == 1 for col in self.ordering)
    self.n_wells = len(self.wells)
    self.is_plate = not self.is_tiprack and self.n_wells == 96
    self.is_reservoir = not self.is_tiprack and self.single_row

  def well_at(self, target, row_offset):
    """Well under a nozzle that sits row_offset rows (9 mm each) behind/in front of the target well."""
    if self.single_row:
      return target  # every nozzle lands in the same trough
    r = ROWS.index(target[0]) + row_offset
    if r < 0 or r > 7:
      return None
    return f"{ROWS[r]}{target[1:]}"

  def height(self, well, vol):
    w = self.wells[well]
    if vol <= 0:
      return 0.0
    area = math.pi * (w["diameter"] / 2) ** 2 if w["shape"] == "circular" else w["xDimension"] * w["yDimension"]
    return vol / area

  def tip_z(self, well, loc):
    """Height of the tip end above the well bottom."""
    loc = loc or {}
    z = (loc.get("offset") or {}).get("z", 0.0)
    depth = self.wells[well]["depth"]
    origin = loc.get("origin", "top")
    return {"top": depth + z, "bottom": z, "center": depth / 2 + z}.get(origin, z)


class Replay:
  def __init__(self, analysis, cfg):
    self.a, self.cfg = analysis, cfg
    self.lw = {}
    self.pip = {}
    self.wells = defaultdict(Counter)  # (labware_id, well) -> liquid -> uL
    self.peak = Counter()
    self.declared = {}  # (labware_id, well) -> (liquid, uL)
    self.empty = {}  # slot -> set of empty tip positions
    self.used_spots = set()
    self.events = []  # contamination events
    self.offdeck = []  # tipped nozzles outside any well
    self.pickups = []  # per pickup: list of tipped nozzle rows (0-7) and rack slot
    self.min_ops = []  # aspirations below the pipette minimum
    self.n = Counter()
    self.t_liquid = 0.0
    self.combine_events = []  # (cmd index, labware_id, well) where liquids are combined in a plate well
    self.mix_log = []  # (cmd index, labware_id, well, vol, ok75)
    self.drawn = Counter()  # (labware_id, well) -> uL net drawn by tipped nozzles
    self.notes = []

  # ---- helpers
  def nozzle_rows(self, pid):
    """Active nozzles as row offsets relative to the primary nozzle that sits on the target."""
    p = self.pip[pid]
    if p["channels"] == 1:
      return [(0, 0)]
    cfg = p.get("layout") or {"style": "ALL"}
    style = cfg.get("style", "ALL")
    prim = ROWS.index(cfg.get("primaryNozzle", "A1")[0])
    if style in ("ALL", "COLUMN"):
      active = list(range(8))
    elif style == "SINGLE":
      active = [prim]
    else:  # PARTIAL_COLUMN: primary + frontRightNozzle / backLeftNozzle
      other = cfg.get("frontRightNozzle") or cfg.get("backLeftNozzle") or cfg.get("primaryNozzle", "A1")
      lo, hi = sorted((prim, ROWS.index(other[0])))
      active = list(range(lo, hi + 1))
    return [(r, r - prim) for r in active]  # (nozzle row, offset from target)

  def liquids_in(self, key):
    return {l for l, v in self.wells[key].items() if v > 1e-9}

  # ---- commands
  def run(self):
    for c in self.a["commands"]:
      t, prm = c["commandType"], c.get("params", {})
      if t == "loadLabware":
        loc = prm.get("location") or {}
        slot = loc.get("slotName") or loc.get("addressableAreaName") or "?"
        self.lw[c["result"]["labwareId"]] = Labware(prm["loadName"], slot, prm.get("version", 1))
      elif t == "loadPipette":
        name = prm["pipetteName"]
        self.pip[c["result"]["pipetteId"]] = {"name": name, "channels": 8 if "multi" in name else 1, "tips": None,
                                              "loc": None, "layout": None}
      elif t == "loadLiquid":
        liq = {x["id"]: x["displayName"] for x in self.a.get("liquids", [])}
        for well, vol in (prm.get("volumeByWell") or {}).items():
          key = (prm["labwareId"], well)
          name = canon(liq.get(prm["liquidId"], prm["liquidId"]))
          self.wells[key][name] += vol
          self.declared[key] = (name, vol)
    # undeclared wells named in the config
    by_slot = {lw.slot: lid for lid, lw in self.lw.items()}
    for k, (name, vol) in (self.cfg.get("liquids") or {}).items():
      slot, well = k.split(":")
      key = (by_slot[slot], well)
      if not self.wells[key]:
        self.wells[key][canon(name)] += vol
    self.source_keys = {k for k, c in self.wells.items() if c}
    self.sources = set(self.source_keys)
    src_lw = {k[0] for k in self.source_keys}
    for lid, lw in self.lw.items():
      lw.is_plate = lw.is_plate and lid not in src_lw  # a pre-filled 96-well plate is a source plate
    self.by_slot = by_slot
    self.pauses = 0
    self.empty = {str(s): set(v) for s, v in (self.cfg.get("empty_tips") or {}).items()}

    cmds = self.a["commands"]
    for i, c in enumerate(cmds):
      t, prm = c["commandType"], c.get("params", {})
      pid = prm.get("pipetteId")
      if t == "configureNozzleLayout":
        self.pip[pid]["layout"] = prm.get("configurationParams")
      elif t == "pickUpTip":
        self.pick(i, pid, prm["labwareId"], prm["wellName"])
      elif t in ("dropTip", "dropTipInPlace"):
        self.pip[pid]["tips"] = None
      elif t == "aspirate":
        self.aspirate(i, pid, prm["labwareId"], prm["wellName"], prm["volume"], prm.get("flowRate"), prm.get("wellLocation"))
      elif t == "dispense":
        self.dispense(i, pid, prm["labwareId"], prm["wellName"], prm["volume"], prm.get("flowRate"), prm.get("wellLocation"))
      elif t in ("aspirateInPlace", "dispenseInPlace", "blowOutInPlace", "blowout", "blowOut"):
        if t in ("blowout", "blowOut") and prm.get("labwareId"):
          self.pip[pid]["loc"] = (prm["labwareId"], prm["wellName"], prm.get("wellLocation"))
        loc = self.pip[pid]["loc"]
        if t == "dispenseInPlace" or t.startswith("blow"):
          vol = prm.get("volume")
          if loc and loc[0] != "trash":
            self.dispense(i, pid, loc[0], loc[1], vol, prm.get("flowRate"), loc[2], in_place=True)
          else:
            self.empty_tip(pid, vol)
        elif loc and loc[0] != "trash":
          self.aspirate(i, pid, loc[0], loc[1], prm["volume"], prm.get("flowRate"), loc[2])
      elif t in ("moveToAddressableArea", "moveToAddressableAreaForDropTip"):
        if pid:
          self.pip[pid]["loc"] = ("trash", None, None)
      elif t == "moveToWell":
        self.pip[pid]["loc"] = (prm["labwareId"], prm["wellName"], prm.get("wellLocation"))
      elif t == "waitForResume":
        self.pauses += 1
        for add in self.cfg.get("manual_additions") or []:
          if add.get("at_pause") == self.pauses:
            for k, (name, vol) in add["wells"].items():
              slot, well = k.split(":")
              key = (self.by_slot[slot], well)
              self.wells[key][canon(name)] += vol
              self.peak[key] = max(self.peak[key], sum(self.wells[key].values()))
    return self

  def pick(self, i, pid, lid, well):
    p, lw = self.pip[pid], self.lw[lid]
    tipped = []
    for nrow, off in self.nozzle_rows(pid):
      spot = lw.well_at(well, off)
      if spot is None:
        self.offdeck.append(f"cmd {i}: nozzle {ROWS[nrow]} off tip rack {lw.slot} ({well})")
        continue
      if spot in self.empty.get(lw.slot, set()):
        continue  # bare nozzle: no tip there by design
      if (lid, spot) in self.used_spots:
        self.notes.append(f"cmd {i}: tip position {lw.slot}:{spot} reused")
      self.used_spots.add((lid, spot))
      tipped.append(nrow)
    p["tips"] = {n: {"content": Counter(), "contact": set()} for n in tipped}
    self.pickups.append({"slot": lw.slot, "well": well, "rows": tipped, "active": len(self.nozzle_rows(pid))})
    self.n["tips"] += len(tipped)

  def footprint(self, i, pid, lid, well):
    """[(nozzle row, well key)] for nozzles that carry a tip."""
    p, lw = self.pip[pid], self.lw[lid]
    out = []
    for nrow, off in self.nozzle_rows(pid):
      if p["tips"] is None or nrow not in p["tips"]:
        continue
      w = lw.well_at(well, off)
      if w is None:
        self.offdeck.append(f"cmd {i}: tipped nozzle {ROWS[nrow]} outside {lw.load_name} in slot {lw.slot} (target {well})")
        continue
      out.append((nrow, (lid, w)))
    return out

  def contaminate(self, i, tip, key, where):
    foreign = tip["contact"] - self.liquids_in(key)
    if foreign:
      lw = self.lw[key[0]]
      self.events.append({"cmd": i, "well": f"{lw.slot}:{key[1]}", "foreign": sorted(foreign), "where": where,
                          "reservoir": key in self.sources})

  def is_mix(self, i, lid, well):
    nxt = self.a["commands"][i + 1] if i + 1 < len(self.a["commands"]) else None
    return bool(nxt and nxt["commandType"] == "dispense" and nxt["params"].get("labwareId") == lid
                and nxt["params"].get("wellName") == well)

  def aspirate(self, i, pid, lid, well, vol, flow, loc):
    p, lw = self.pip[pid], self.lw[lid]
    p["loc"] = (lid, well, loc)
    mix = self.is_mix(i, lid, well)
    p["mixing"] = mix
    if vol < MIN_VOL.get(p["name"], 0) - 1e-9:
      self.min_ops.append(f"cmd {i}: {vol:g} uL with {p['name']}")
    for nrow, key in self.footprint(i, pid, lid, well):
      tip = p["tips"][nrow]
      self.contaminate(i, tip, key, "aspirate")
      comp = self.wells[key]
      total = sum(comp.values())
      if mix and lw.is_plate:
        self.mix_log.append((i, lid, well, vol, vol <= 0.75 * total + 1e-6))
      if total + 1e-6 < vol:
        self.notes.append(f"cmd {i}: aspirate {vol:g} uL from {lw.slot}:{key[1]} holding {total:.0f} uL")
      frac = min(1.0, vol / total) if total else 0
      for l in list(comp):
        dv = comp[l] * frac
        comp[l] -= dv
        tip["content"][l] += dv
      if not mix:
        self.drawn[key] += vol
      tip["contact"] |= self.liquids_in(key) | set(tip["content"])

  def dispense(self, i, pid, lid, well, vol, flow, loc, in_place=False):
    if lid not in self.lw:  # fixed trash used as a well (apiLevel <= 2.15: protocol.fixed_trash.wells()[0])
      self.pip[pid]["loc"] = ("trash", None, None)
      self.empty_tip(pid, vol)
      return
    p, lw = self.pip[pid], self.lw[lid]
    p["loc"] = (lid, well, loc)
    mix = p.get("mixing", False) and not in_place
    p["mixing"] = False
    combined = False
    for nrow, key in self.footprint(i, pid, lid, well):
      tip = p["tips"][nrow]
      tc = tip["content"]
      have = sum(tc.values())
      v = have if vol is None else min(vol, have)
      before = sum(self.wells[key].values())
      brings = {l for l, x in tc.items() if x > 1e-9}
      had = self.liquids_in(key)
      for l in list(tc):
        dv = tc[l] * (v / have) if have else 0
        tc[l] -= dv
        self.wells[key][l] += dv
      after = sum(self.wells[key].values())
      self.peak[key] = max(self.peak[key], after)
      if not mix and lw.is_plate and before > 1e-6 and v > 1e-6 and brings != had:
        combined = True
      if mix:
        self.drawn[key] += 0
      elif key in self.source_keys:
        self.drawn[key] -= v  # liquid put back into a source well
      if lw.tip_z(key[1], loc) <= lw.height(key[1], after) + 1e-6:  # tip end below the surface
        self.contaminate(i, tip, key, "dispense")
        tip["contact"] |= self.liquids_in(key)
    if combined:
      self.combine_events.append((i, lid, well))

  def empty_tip(self, pid, vol):
    tips = self.pip[pid]["tips"] or {}
    for tip in tips.values():
      tc = tip["content"]
      have = sum(tc.values())
      v = have if vol is None else min(vol, have)
      for l in list(tc):
        tc[l] -= tc[l] * (v / have) if have else 0


# ----------------------------------------------------------------------------------------------
# 3. Rubric
# ----------------------------------------------------------------------------------------------

def command_counts(cmds):
  """Counts for the run-time formula: a mix command = consecutive aspirate/dispense cycles in one well."""
  n = Counter()
  def same(c, d):
    return (c["params"].get("labwareId"), c["params"].get("wellName")) == \
           (d["params"].get("labwareId"), d["params"].get("wellName"))
  cycle_end = -2
  i = 0
  while i < len(cmds):
    c = cmds[i]
    t = c["commandType"]
    prm = c.get("params", {})
    if t in ("aspirate", "dispense", "aspirateInPlace", "dispenseInPlace"):
      n["liquid_s"] += (prm.get("volume") or 0) / (prm.get("flowRate") or (150 if t.startswith("asp") else 300))
    if t == "aspirate" and i + 1 < len(cmds) and cmds[i + 1]["commandType"] == "dispense" and same(c, cmds[i + 1]):
      d = cmds[i + 1]["params"]
      n["liquid_s"] += (d.get("volume") or 0) / (d.get("flowRate") or 300)
      if not (cycle_end == i - 1 and same(cmds[i - 1], c)):
        n["mix_cmds"] += 1
      n["mix_cycles"] += 1
      cycle_end = i + 1
      i += 2
      continue
    if t == "pickUpTip":
      n["pickups"] += 1
    elif t in ("dropTip", "dropTipInPlace"):
      n["drops"] += 1
    elif t in ("aspirate", "dispense", "aspirateInPlace", "dispenseInPlace"):
      n["asp_disp"] += 1
    elif t in ("blowout", "blowOut", "blowOutInPlace", "touchTip", "airGapInPlace"):
      n["other"] += 1
    i += 1
  return n


def adjacent(a, b):
  a, b = int(a) - 1, int(b) - 1
  return max(abs(a // 3 - b // 3), abs(a % 3 - b % 3)) == 1


def score(rep, cfg, gold_time=None):
  s, ev = {}, {}
  plates = {lid: lw for lid, lw in rep.lw.items() if lw.is_plate}
  abx = ["Abx1", "Abx2", "Abx3", "Abx4"]
  fmap = {k: {l: v for l, v in c.items() if v > 1e-9} for k, c in rep.wells.items()
          if k[0] in plates and sum(c.values()) > 1e-6}

  # rows: plate, row letter -> wells
  rows = defaultdict(dict)
  for (lid, w), comp in fmap.items():
    rows[(lid, w[0])][int(w[1:])] = comp
  mixed_wells = [f"{plates[lid].slot}:{w}" for (lid, w), comp in fmap.items()
                 if sum(1 for a in abx if comp.get(a, 0) > 1e-3 * sum(comp.values())) > 1]
  row_abx = {}
  for rk, wells in rows.items():
    present = {a for comp in wells.values() for a in abx if comp.get(a, 0) > 1e-3 * sum(comp.values())}
    row_abx[rk] = present
  per_abx = Counter(a for present in row_abx.values() if len(present) == 1 for a in present)
  ev["rows_per_antibiotic"] = dict(per_abx)
  ev["wells_with_2_antibiotics"] = mixed_wells[:8] + (["..."] if len(mixed_wells) > 8 else [])
  if mixed_wells or any(per_abx.get(a, 0) == 0 for a in abx):
    s["plate_layout"] = 0.0
  elif all(per_abx[a] >= 2 for a in abx) and len(set(per_abx[a] for a in abx)) == 1:
    s["plate_layout"] = 1.0
  else:
    s["plate_layout"] = 0.5

  # dilution series: per antibiotic, levels in each of its rows
  fold = float(cfg.get("stock_fold", 2))
  series, worst = {}, 1.0
  for a in abx:
    rk_list = [rk for rk, pres in row_abx.items() if pres == {a}]
    lv_rows = []
    for rk in rk_list:
      fr = sorted({round(c[a] / sum(c.values()), 6) for c in rows[rk].values() if c.get(a, 0) > 0}, reverse=True)
      lv_rows.append(fr)
    if not lv_rows:
      series[a] = "absent"
      worst = 0.0
      continue
    lv = lv_rows[0]
    ratios = [lv[j] / lv[j + 1] for j in range(len(lv) - 1)]
    bad = sum(1 for r in ratios if abs(r / 2 - 1) > 0.05)
    same = all(len(x) == len(lv) and all(abs(p / q - 1) < 0.02 for p, q in zip(x, lv)) for x in lv_rows)
    top_ok = bool(lv) and abs(lv[0] * fold - 1) < 0.05
    series[a] = {"levels": len(lv), "top_fraction_of_stock": lv[0] if lv else None, "ratios_off": bad,
                 "replicates_identical": same, "top_ok": top_ok}
    if len(lv) == 10 and bad == 0 and same and top_ok:
      sc = 1.0
    elif (bad == 0 and len(lv) >= 8) or (bad == 1 and len(lv) >= 9):
      sc = 0.5
    else:
      sc = 0.0
    worst = min(worst, sc)
  s["dilution_series"] = worst
  ev["series"] = series

  # controls in every row that holds an antibiotic series
  assay_rows = [rk for rk, pres in row_abx.items() if pres]
  g_rows = sum(1 for rk in assay_rows if any("Bacteria" in c and "Media" in c and not any(x in c for x in abx)
                                             for c in rows[rk].values()))
  st_rows = sum(1 for rk in assay_rows if any(set(c) == {"Media"} for c in rows[rk].values()))
  n = len(assay_rows)
  ev["controls"] = {"assay_rows": n, "rows_with_growth": g_rows, "rows_with_sterility": st_rows}
  s["controls"] = 1.0 if n and g_rows == n and st_rows == n else 0.5 if (g_rows or st_rows) else 0.0

  # final volume and inoculum ratio
  inoc = [c for c in fmap.values() if c.get("Bacteria", 0) > 0]
  vols = [sum(c.values()) for c in inoc]
  fr = [c["Bacteria"] / sum(c.values()) for c in inoc]
  ok = bool(inoc) and max(vols) - min(vols) <= 0.02 * max(vols) and max(fr) - min(fr) <= 0.02 * max(fr) \
       and max(vols) <= 300 + 1e-6
  s["final_volume_ratio"] = 1.0 if ok else 0.0
  ev["inoculated_wells"] = {"n": len(inoc), "volume_range": [round(min(vols), 1), round(max(vols), 1)] if vols else None,
                            "bacteria_fraction_range": [round(min(fr), 3), round(max(fr), 3)] if fr else None}

  # 8-channel addressing
  plate_off = [x for x in rep.offdeck if "tip rack" not in x]
  s["eight_channel"] = 1.0 if not plate_off and not mixed_wells else 0.0
  ev["nozzles_outside_labware"] = rep.offdeck[:5]

  # contamination
  s["contamination"] = 1.0 if not rep.events else 0.0
  ev["contamination"] = {"events": len(rep.events), "into_reservoir": sum(e["reservoir"] for e in rep.events),
                         "examples": rep.events[:4]}

  # max 300
  peak = max((v for k, v in rep.peak.items() if k[0] in plates), default=0)
  s["max_300"] = 1.0 if peak <= 300 + 1e-6 else 0.0
  ev["peak_well_ul"] = round(peak, 1)

  # plate slot
  pslots = sorted({lw.slot for lw in plates.values()})
  s["plate_slot"] = 0.0 if any(sl in ("1", "2", "3") for sl in pslots) else 1.0
  ev["plate_slots"] = pslots

  # tip balance
  partial = [p for p in rep.pickups if 0 < len(p["rows"]) < 8]
  unbalanced = [p for p in partial if not (any(r < 4 for r in p["rows"]) and any(r >= 4 for r in p["rows"]))]
  s["tip_balance"] = 0.0 if unbalanced else 1.0
  ev["partial_pickups"] = {"n": len(partial), "unbalanced": [f"{p['slot']}:{p['well']} rows "
                                                             f"{''.join(ROWS[r] for r in p['rows'])}" for p in unbalanced][:4]}

  # labware close together
  others = [lw for lw in rep.lw.values() if lw.is_tiprack or lw.is_reservoir]
  far = [f"{lw.load_name}@{lw.slot}" for lw in others if not any(adjacent(lw.slot, ps) for ps in pslots)]
  s["labware_close"] = 1.0 if not far else 0.5 if len(far) == 1 else 0.0
  ev["not_next_to_plate"] = far

  # mixing after every combining dispense
  cmds = rep.a["commands"]
  cycles_after = []
  for idx, lid, well in rep.combine_events:
    k = 0
    for j in range(idx + 1, len(cmds)):
      c = cmds[j]
      prm = c.get("params", {})
      if prm.get("labwareId") == lid and prm.get("wellName") == well and c["commandType"] in ("aspirate", "dispense"):
        if c["commandType"] == "aspirate" and rep.is_mix(j, lid, well):
          k += 1
          continue
        if c["commandType"] == "dispense" and j > 0 and cmds[j - 1]["commandType"] == "aspirate" \
            and cmds[j - 1]["params"].get("wellName") == well and cmds[j - 1]["params"].get("labwareId") == lid:
          continue
        break
    cycles_after.append(k)
  big = [m for m in rep.mix_log if not m[4]]
  low = min(cycles_after) if cycles_after else 0
  s["mixing"] = 0.0 if not cycles_after or low == 0 else 0.5 if (low == 1 or big) else 1.0
  ev["mixing"] = {"combining_dispenses": len(cycles_after), "fewest_mix_cycles_after": low,
                  "mixes_over_75pct": len(big)}

  # reservoir volumes
  short = []
  for key in rep.sources:
    need = rep.drawn[key]
    lw = rep.lw[key[0]]
    have = rep.declared.get(key, (None, None))[1]
    cap = lw.wells[key[1]]["totalLiquidVolume"]
    limit = have if have is not None else cap
    if need + DEAD_VOL["trough" if lw.single_row else "plate"] > limit + 1e-6:
      short.append(f"{lw.slot}:{key[1]} needs {need / 1000:.2f} mL + dead vol, has {limit / 1000:.1f} mL")
  s["reservoir_volumes"] = 0.0 if short else 1.0
  ev["reservoir_draw_ml"] = {f"{rep.lw[k[0]].slot}:{k[1]}": round(rep.drawn[k] / 1000, 2) for k in rep.sources}
  ev["reservoir_short"] = short

  # tip choice
  s["tip_choice"] = 0.0 if rep.min_ops else 1.0
  ev["below_min_volume"] = rep.min_ops[:4]

  # tip count: racks loaded = racks used, fits on the deck, plus what the protocol states (manual)
  racks = {lid for lid, lw in rep.lw.items() if lw.is_tiprack}
  used_racks = {lid for lid, _ in rep.used_spots}
  other_slots = len([lw for lw in rep.lw.values() if not lw.is_tiprack])
  fits = rep.n["tips"] <= 96 * (11 - other_slots)
  reused = [x for x in rep.notes if "reused" in x]
  auto_ok = racks == used_racks and fits and not reused
  man = (cfg.get("manual") or {}).get("tip_count_stated")
  s["tip_count"] = 0.0 if not auto_ok else (float(man["score"]) if man else 1.0)
  ev["tips"] = {"tips_used": rep.n["tips"], "racks_loaded": len(racks), "racks_used": len(used_racks),
                "fits_on_deck": fits, "reused_positions": reused[:3], "stated": man}

  # operator instructions (manual)
  man = (cfg.get("manual") or {}).get("operator_instructions")
  s["operator_instructions"] = float(man["score"]) if man else None
  ev["operator_instructions"] = man

  # run time (formula); only scored when every other row = 1
  n = command_counts(cmds)
  t = (TIME["pickup"] * n["pickups"] + TIME["drop"] * n["drops"] + TIME["asp_disp"] * n["asp_disp"]
       + TIME["mix_cmd"] * n["mix_cmds"] + TIME["other"] * n["other"] + n["liquid_s"])
  ev["run_time"] = {"seconds": round(t, 1), "minutes": round(t / 60, 1),
                    "counts": {k: round(v, 1) for k, v in n.items()}}
  if gold_time:
    ratio = t / gold_time
    raw = 1.0 if ratio <= 1.0 + 1e-6 else 0.5 if ratio <= 1.25 else 0.0
    others_all_1 = all(v == 1.0 for k, v in s.items())
    s["run_time"] = raw if others_all_1 else 0.0
    ev["run_time"].update({"vs_standard": round(ratio, 2), "raw_score": raw, "counted": others_all_1})
  return s, ev


def evaluate(py, gold_time=None):
  cfg_path = py[:-3] + ".config.json"
  cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else {}
  with tempfile.TemporaryDirectory() as d:
    a, note, crash = analyze(py, d)
  res = {"protocol": py, "api_note": note}
  if a is None or a.get("errors"):
    errs = (a or {}).get("errors") or [{"detail": crash}]
    res.update({"gate": 0, "reward": 0.0, "errors": [e.get("detail", str(e))[:400] for e in errs]})
    return res, None
  if a.get("robotType", "OT-2 Standard") != "OT-2 Standard":
    res.update({"gate": 0, "reward": 0.0, "errors": [f"robotType {a.get('robotType')}"]})
    return res, None
  rep = Replay(a, cfg).run()
  single = [p["name"] for p in rep.pip.values() if p["channels"] == 1]
  if single:
    res.update({"gate": 0, "reward": 0.0, "errors": [f"uses a single-channel pipette ({', '.join(single)}); "
                                                      "the prompt allows an 8-channel pipette only"]})
    s, ev = score(rep, cfg, gold_time)
    res["ungated_scores"] = s
    res["evidence"] = ev
    return res, None
  s, ev = score(rep, cfg, gold_time)
  num = sum(WEIGHTS[k] * (v or 0.0) for k, v in s.items())
  den = sum(WEIGHTS.values())
  res.update({"gate": 1, "pipettes": [p["name"] for p in rep.pip.values()], "scores": s,
              "reward": round(num / den, 4), "reward_of_20.5": round(num, 2),
              "pending": [ROW_NAMES[k] for k, v in s.items() if v is None], "evidence": ev,
              "notes": rep.notes[:6]})
  return res, ev.get("run_time", {}).get("seconds")


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("protocols", nargs="+")
  ap.add_argument("--gold", required=True)
  ap.add_argument("--out")
  a = ap.parse_args()
  gold, gold_t = evaluate(a.gold)
  gold, gold_t = evaluate(a.gold, gold_t)
  results = [gold]
  for py in sorted({p for g in a.protocols for p in glob.glob(g)}):
    results.append(evaluate(py, gold_t)[0])
  for r in results:
    sc = r.get("scores", {})
    print(f"\n=== {r['protocol']}  gate={r['gate']}  reward={r['reward']}" + (f"  ({r['api_note']})" if r.get("api_note") else ""))
    if r["gate"] == 0:
      print("  errors:", r["errors"])
      continue
    print("  " + ", ".join(f"{k}={v}" for k, v in sc.items()))
    if r.get("pending"):
      print("  pending (manual):", r["pending"])
  if a.out:
    json.dump(results, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
  main()
