"""The lab's capabilities, loaded from execution/lab.yaml.

    lab = Lab.load()
    lab.pipettes()                  # the ones confirmed mounted
    lab.labware("wellplate")        # every 96-well plate on hand
    lab.can_incubate_at(37)         # True

A thin typed reader, deliberately: the judgement about what the lab can do belongs in the YAML, where a person
can read and correct it, and the arithmetic belongs in feasibility.py. Nothing here decides anything.
"""
from pathlib import Path

import yaml

LAB_YAML = Path(__file__).resolve().parent / "lab.yaml"


class Lab:
    def __init__(self, spec: dict):
        self.spec = spec

    @classmethod
    def load(cls, path: Path | str | None = None) -> "Lab":
        with open(Path(path) if path else LAB_YAML, encoding="utf-8") as f:
            return cls(yaml.safe_load(f) or {})

    # --- instruments ---------------------------------------------------------------------------------------

    def instruments(self, kind: str | None = None) -> list[dict]:
        found = self.spec.get("instruments", [])
        return [i for i in found if kind is None or i.get("kind") == kind]

    def instrument(self, id: str) -> dict | None:
        return next((i for i in self.instruments() if i.get("id") == id), None)

    def pipettes(self, include_unconfirmed: bool = False) -> list[dict]:
        """Pipettes on the liquid handlers. A pipette marked `mounted: unconfirmed` is left out by default, so a
        protocol is never planned around one that may not be there."""
        found = [p for i in self.instruments("liquid_handler") for p in i.get("pipettes", [])]
        return found if include_unconfirmed else [p for p in found if p.get("mounted") != "unconfirmed"]

    def pipette_for(self, volume_uL: float) -> dict | None:
        """The smallest confirmed pipette that can move this volume in one go, or None."""
        fits = [p for p in self.pipettes() if p["min_uL"] <= volume_uL <= p["max_uL"]]
        return min(fits, key=lambda p: p["max_uL"]) if fits else None

    def read_modes(self) -> set[str]:
        return {m for i in self.instruments("plate_reader") for m in i.get("modes", [])}

    # --- labware -------------------------------------------------------------------------------------------

    def labware(self, kind: str | None = None) -> list[dict]:
        found = self.spec.get("labware", [])
        return [w for w in found if kind is None or w.get("kind") == kind]

    def plate(self) -> dict | None:
        """The assay plate: the wellplate with the most wells on hand."""
        plates = self.labware("wellplate")
        return max(plates, key=lambda w: w.get("rows", 0) * w.get("cols", 0)) if plates else None

    def tip_columns(self) -> int:
        """Columns of tips available to an 8-channel pipette, across every rack on hand."""
        return sum(int(r.get("tips", 0) / 8) * int(r.get("count", 0)) for r in self.labware("tiprack"))

    def reservoir_usable_mL(self) -> float:
        """What one reservoir channel can actually give up, after the dead volume the tips cannot reach."""
        found = self.labware("reservoir")
        if not found:
            return 0.0
        r = max(found, key=lambda x: x.get("max_mL", 0))
        return float(r.get("max_mL", 0)) - float(r.get("dead_mL", 0))

    # --- conditions ----------------------------------------------------------------------------------------

    @property
    def capabilities(self) -> dict:
        return self.spec.get("capabilities", {})

    def atmospheres(self) -> set[str]:
        return set(self.capabilities.get("atmosphere", []))

    def can_incubate_at(self, celsius: float, tolerance: float = 2.0) -> bool:
        return any(abs(float(t) - float(celsius)) <= tolerance for t in self.capabilities.get("incubation_C", []))

    def reagents(self) -> dict[str, dict]:
        return {r["id"]: r for r in self.spec.get("reagents", [])}

    def unconfirmed(self) -> list[str]:
        """Everything the file admits it is unsure about, so a verdict can say so out loud."""
        found = []
        for p in self.pipettes(include_unconfirmed=True):
            if p.get("mounted") == "unconfirmed":
                found.append(f"pipette {p['model']} on the {p['mount']} mount may not be installed")
        for key, value in self.capabilities.items():
            if value == "unconfirmed":
                found.append(f"capability '{key}' is unconfirmed")
        return found
