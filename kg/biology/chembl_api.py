"""Read ChEMBL over the REST API, for the rows the local SQLite dump would give.

`chembl_db.py` is the fast path and needs the 5.8 GB dump. This is the slow path that needs nothing, so the
bacterial graph can be built on a laptop that has never downloaded ChEMBL. Same row shapes either way: the API
returns the fields `activity.json` documents, and `build_bacteria.py` reads only those.

    api = ChemblAPI()
    acts = api.activities("CHEMBL614411")                 # every MIC on Bacteroides fragilis
    acts = api.activities("CHEMBL352", compounds=[...])   # only these compounds, on S. aureus

Structure lookups go through `molecules()`, which asks for structures only and never for activities: the live
ChEMBL release still holds the measurements a benchmark question holds out, so pulling activities from here
would hand the agent the answer (the same rule `agent/compounds.py` follows).
"""
import json
import subprocess
import time
from typing import Iterable

BASE = "https://www.ebi.ac.uk/chembl/api/data"
PAGE = 1000          # the API's maximum
BATCH = 40           # IDs per `__in` filter; longer URLs start getting refused
RETRIES = 4


class ChemblAPIError(RuntimeError):
    pass


def _get(url: str, retries: int = RETRIES) -> dict:
    """One GET, retried: a page that comes back empty is the failure mode that matters here, because it looks
    like 'no results' rather than an error and silently empties whatever is being built."""
    last = ""
    for attempt in range(retries):
        done = subprocess.run(["curl", "-s", "--max-time", "120", url], capture_output=True, text=True)
        try:
            return json.loads(done.stdout)
        except json.JSONDecodeError:
            last = (done.stdout or done.stderr or "")[:200]
            time.sleep(1.5 * (attempt + 1))
    raise ChemblAPIError(f"no JSON from ChEMBL after {retries} tries: {url[:120]} ({last!r})")


class ChemblAPI:
    def __init__(self, base: str = BASE, pause: float = 0.1):
        self.base = base
        self.pause = pause

    def _pages(self, path: str, query: str) -> list[dict]:
        out: list[dict] = []
        offset = 0
        while True:
            page = _get(f"{self.base}/{path}.json?limit={PAGE}&offset={offset}&{query}")
            rows = page.get(path.rstrip("s") + "s") or page.get("activities") or page.get("molecules") or []
            out += rows
            if len(rows) < PAGE:
                return out
            offset += PAGE
            time.sleep(self.pause)

    def activities(self, target_chembl_id: str, standard_type: str = "MIC",
                   compounds: Iterable[str] | None = None) -> list[dict]:
        """Every `standard_type` activity on one target. With `compounds`, only those molecules — which is how
        the pathogen arm is pulled, so it holds the compounds the commensal arm actually has rather than the
        250k that share nothing with it."""
        query = f"target_chembl_id={target_chembl_id}&standard_type={standard_type}"
        if compounds is None:
            return self._pages("activity", query)
        ids = sorted(set(compounds))
        out: list[dict] = []
        for i in range(0, len(ids), BATCH):
            batch = ",".join(ids[i:i + BATCH])
            out += self._pages("activity", f"{query}&molecule_chembl_id__in={batch}")
            time.sleep(self.pause)
        return out

    def molecules(self, compound_ids: Iterable[str]) -> dict[str, dict]:
        """{chembl_id: {"name", "smiles"}} for each compound. Structures only — never activities."""
        ids = sorted(set(compound_ids))
        out: dict[str, dict] = {}
        for i in range(0, len(ids), BATCH):
            batch = ",".join(ids[i:i + BATCH])
            page = _get(f"{self.base}/molecule.json?limit={PAGE}&molecule_chembl_id__in={batch}"
                        "&only=molecule_chembl_id,pref_name,molecule_structures")
            for m in page.get("molecules", []):
                structures = m.get("molecule_structures") or {}
                out[m["molecule_chembl_id"]] = {"name": m.get("pref_name") or "",
                                                "smiles": structures.get("canonical_smiles") or ""}
            time.sleep(self.pause)
        return out
