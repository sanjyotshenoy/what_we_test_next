"""Resolve a compound the knowledge graph may not hold: a name or ChEMBL ID in, a structure (SMILES) out.

Three sources, in order, each optional:

1. the biology graph itself (`agent/kg_backend.py`), which already carries `smiles` on every Compound node;
2. the local ChEMBL SQLite dump, if it is on this machine (`kg/biology/chembl_db.py` says how to get it);
3. the ChEMBL REST API, cached on disk under `data/raw/chembl_compounds/` (git-ignored).

**Structure fields only** (`molecule_chembl_id`, `pref_name`, `canonical_smiles`). This never reads activities
from the dump or the API: the live ChEMBL release still contains the measurements the benchmark holds out
(`kg/biology/README.md`: the IC50s a benchmark question asks about must not reach the agent), so pulling
activities from here would leak the answer the agent is supposed to propose an experiment for.

    resolver = CompoundResolver()
    hit = resolver.resolve("ibrutinib")       # -> Compound(id=..., name=..., smiles=..., source=...)

Every step degrades to None rather than failing: no dump, no network or an unknown compound just means the
caller has no structure to work with, and `resolver.notes` says why.
"""
import json
import os
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / "data" / "raw" / "chembl_compounds"      # git-ignored (data/raw/ in .gitignore)
API = "https://www.ebi.ac.uk/chembl/api/data/molecule"
TIMEOUT = 10
FIELDS = ("molecule_chembl_id", "pref_name", "canonical_smiles")   # structures only, never activities

CHEMBL_ID = re.compile(r"^CHEMBL\d+$", re.I)


@dataclass
class Compound:
    id: str
    name: str
    smiles: str
    source: str          # "biology KG", "ChEMBL dump" or "ChEMBL API"


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text.strip().lower()).strip("_")[:80] or "query"


class CompoundResolver:
    """Name or ChEMBL ID -> structure. `graph` is an optional `GraphBackend` to try first."""

    def __init__(self, graph=None, cache: Path | None = None, allow_network: bool = True):
        self.graph = graph
        self.cache = Path(cache) if cache else CACHE
        self.allow_network = allow_network and os.environ.get("WWTN_OFFLINE", "") == ""
        self.notes: list[str] = []

    # --- the sources -----------------------------------------------------------------------------------------

    def from_graph(self, text: str) -> Compound | None:
        if self.graph is None:
            return None
        node = self.graph.find_compound(text)
        if not node:
            return None
        smiles = node["props"].get("smiles") or ""
        return Compound(node["id"], node.get("name") or node["id"], smiles, "biology KG")

    def from_dump(self, text: str) -> Compound | None:
        """The local ChEMBL dump, by ChEMBL ID or preferred name. Structure tables only."""
        try:
            from kg.biology.chembl_db import DEFAULT_PATH
        except ImportError:                                      # pragma: no cover - kg always importable here
            return None
        path = Path(os.environ.get("CHEMBL_SQLITE") or DEFAULT_PATH)
        if not path.exists():
            self.notes.append("no local ChEMBL dump")
            return None
        sql = ("SELECT md.chembl_id, md.pref_name, cs.canonical_smiles FROM molecule_dictionary md "
               "LEFT JOIN compound_structures cs ON cs.molregno = md.molregno WHERE ")
        where, params = ("md.chembl_id = ?", (text.upper(),)) if CHEMBL_ID.match(text) \
            else ("UPPER(md.pref_name) = ?", (text.upper(),))
        try:
            con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                row = con.execute(sql + where + " LIMIT 1", params).fetchone()
            finally:
                con.close()
        except sqlite3.Error as e:
            self.notes.append(f"ChEMBL dump unreadable: {e}")
            return None
        if row is None:
            return None
        chembl_id, name, smiles = row
        return Compound(chembl_id, name or chembl_id, smiles or "", "ChEMBL dump")

    def _cached(self, key: str) -> dict | None:
        path = self.cache / f"{key}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _store(self, key: str, payload: dict) -> None:
        try:
            self.cache.mkdir(parents=True, exist_ok=True)
            (self.cache / f"{key}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as e:                                     # a read-only checkout is not a failure
            self.notes.append(f"could not cache the ChEMBL answer: {e}")

    def fetch(self, url: str) -> dict | None:
        """One GET against the ChEMBL API. Overridden in tests; never called when `allow_network` is False."""
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            self.notes.append(f"ChEMBL API unavailable: {type(e).__name__}")
            return None

    def from_api(self, text: str) -> Compound | None:
        """The ChEMBL REST API, cached on disk. Asks only for the structure fields in FIELDS."""
        key = _slug(text)
        payload = self._cached(key)
        if payload is None:
            if not self.allow_network:
                self.notes.append("network lookups are off")
                return None
            only = ",".join(FIELDS)
            if CHEMBL_ID.match(text):
                url = f"{API}/{text.upper()}.json?only={only}"
            else:
                url = f"{API}.json?pref_name__iexact={urllib.parse.quote(text)}&only={only}&limit=1"
            payload = self.fetch(url)
            if payload is None:
                return None
            self._store(key, payload)
        molecules = payload.get("molecules") if isinstance(payload, dict) else None
        row = (molecules or [payload])[0] if (molecules or isinstance(payload, dict)) else None
        if not isinstance(row, dict) or not row.get("molecule_chembl_id"):
            return None
        structures = row.get("molecule_structures") or {}
        smiles = row.get("canonical_smiles") or structures.get("canonical_smiles") or ""
        chembl_id = row["molecule_chembl_id"]
        return Compound(chembl_id, row.get("pref_name") or chembl_id, smiles, "ChEMBL API")

    # --- the resolver ----------------------------------------------------------------------------------------

    def resolve(self, text: str) -> Compound | None:
        """The first source that knows this compound, or None. A hit with no SMILES still counts as a hit: the
        caller then knows the compound exists but cannot be used for similarity."""
        text = str(text or "").strip()
        if not text:
            return None
        for source in (self.from_graph, self.from_dump, self.from_api):
            hit = source(text)
            if hit:
                return hit
        return None

    def smiles_for(self, text: str) -> tuple[str, str]:
        """(smiles, where_it_came_from). Empty SMILES when nothing could be resolved."""
        hit = self.resolve(text)
        if not hit:
            return "", "unresolved"
        return hit.smiles, hit.source
