"""PubChem BioAssay client: candidate AIDs per archetype and each AID's protocol text, cached on disk.

    python -m kg.protocols.pubchem candidates proto:kinase_biochem_lum      # confirmatory dose-response AIDs
    python -m kg.protocols.pubchem show 588811                              # protocol text, target, series

From Python:

    from kg.protocols.pubchem import PubChem
    pc = PubChem()
    record = pc.assay(588811)            # parsed description: text fields, targets, tested concentrations
    pc.candidates(archetype)             # an archetype dict from archetypes.yaml

Endpoints (shapes checked against the live API, 2026-11-07):
  PUG-REST  /assay/aid/<aid>/description/JSON       PC_AssayContainer[0].assay.descr: name, description,
            protocol, comment (lists of lines), target, xref, results (tc = tested concentration), dr,
            activity_outcome_method (2 = confirmatory: matches the summary's "Method")
  PUG-REST  /assay/target/genesymbol/<sym>/aids/JSON, /assay/target/accession/<acc>/aids/JSON,
            /assay/type/doseresponse/aids/JSON      IdentifierList.AID
  Entrez    esearch/esummary on db=pcassay           full-text and field search ([APRL] = protocol text,
            [ACMD] = activity outcome method), deposit dates; PUG-REST has no assay text search.
Responses are cached as JSON under data/raw/pubchem/ (git-ignored); rate ≤ 5 req/s to PubChem and ≤ 3 req/s to
Entrez (no API key), with retries on 429/5xx.
"""
import argparse
import json
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from kg.constants import CUTOFF_YEAR

PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
CACHE = Path("data/raw/pubchem")
MIN_INTERVAL = {PUG: 0.21, EUTILS: 0.34}   # PubChem asks for ≤ 5 req/s; Entrez ≤ 3 req/s without an API key
OUTCOME_METHOD = {1: "screening", 2: "confirmatory", 3: "summary"}
# PubChem result-column unit codes, as factors to µM. Only the code seen in fetched AIDs is listed:
# 5 = µM (its columns are named like "Activity_at_0.0056uM").
# TODO(final): other concentration codes (nM, mM, µg/mL) are not mapped; such series are skipped, not guessed.
UNIT_TO_UM = {5: 1.0}
# A series counts as one geometric dilution when no two tested concentrations are closer than MIN_STEP (a single
# dilution never repeats a point) and its largest fold-step is at most SPREAD times its smallest (depositors round
# their concentrations, so a nominal 1:3 series shows steps from 2.0 to 4.0).
MIN_STEP, SPREAD = 1.5, 2.5
USER_AGENT = "what-we-test-next/0.1 (hackathon prototype; kg/protocols)"


class NotFound(Exception):
    pass


class PubChem:
    def __init__(self, cache: Path | str = CACHE, offline: bool = False, retries: int = 4):
        self.cache = Path(cache)
        self.offline = offline        # True: cache only, never the network (tests)
        self.retries = retries
        self._last: dict[str, float] = {}

    # --- HTTP + cache -------------------------------------------------------------------------------------------
    def _wait(self, base: str) -> None:
        gap = MIN_INTERVAL[base] - (time.monotonic() - self._last.get(base, 0.0))
        if gap > 0:
            time.sleep(gap)
        self._last[base] = time.monotonic()

    def _fetch(self, base: str, path: str, params: dict | None = None) -> bytes:
        url = f"{base}/{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
        for attempt in range(self.retries + 1):
            self._wait(base)
            try:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(request, timeout=60) as response:
                    return response.read()
            except urllib.error.HTTPError as err:
                if err.code == 404:
                    raise NotFound(url) from err
                if err.code not in (429, 500, 502, 503, 504) or attempt == self.retries:
                    raise
            except (urllib.error.URLError, TimeoutError):
                if attempt == self.retries:
                    raise
            time.sleep(2 ** attempt)
        raise RuntimeError("unreachable")

    def _json(self, key: str, base: str, path: str, params: dict | None = None, refresh: bool = False) -> dict:
        file = self.cache / f"{key}.json"
        if file.exists() and not refresh:
            return json.loads(file.read_text())
        if self.offline:
            raise FileNotFoundError(f"{file} is not cached and the client is offline")
        data = json.loads(self._fetch(base, path, params))
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(data))
        return data

    # --- AID lists ----------------------------------------------------------------------------------------------
    def aids_for_gene(self, symbol: str) -> list[int]:
        return self._ids(f"target/genesymbol/{symbol}", f"assay/target/genesymbol/{symbol}/aids/JSON")

    def aids_for_accession(self, accession: str) -> list[int]:
        return self._ids(f"target/accession/{accession}", f"assay/target/accession/{accession}/aids/JSON")

    def aids_of_type(self, kind: str = "doseresponse") -> list[int]:
        """kind: confirmatory, doseresponse, ... (PUG-REST /assay/type/<kind>)."""
        return self._ids(f"type/{kind}", f"assay/type/{kind}/aids/JSON")

    def _ids(self, key: str, path: str) -> list[int]:
        try:
            return self._json(key, PUG, path)["IdentifierList"]["AID"]
        except NotFound:
            return []

    def search(self, term: str, retmax: int = 200) -> list[int]:
        """Entrez full-text / field search over PubChem BioAssay, e.g. 'ADP-Glo[APRL] AND confirmatory[ACMD]'."""
        key = "esearch/" + urllib.parse.quote(f"{term}|{retmax}", safe="")
        data = self._json(key, EUTILS, "esearch.fcgi", {"db": "pcassay", "term": term, "retmax": retmax,
                                                         "retmode": "json"})
        return [int(i) for i in data["esearchresult"]["idlist"]]

    def summaries(self, aids: list[int]) -> dict[int, dict]:
        """Entrez esummary rows (deposit date, detection method, gene symbols, outcome method), cached per AID."""
        found, missing = {}, []
        for aid in aids:
            file = self.cache / f"esummary/{aid}.json"
            if file.exists():
                found[aid] = json.loads(file.read_text())
            else:
                missing.append(aid)
        for start in range(0, len(missing), 100):
            batch = missing[start:start + 100]
            if self.offline:
                raise FileNotFoundError(f"esummary for {batch} not cached and the client is offline")
            result = json.loads(self._fetch(EUTILS, "esummary.fcgi", {
                "db": "pcassay", "id": ",".join(map(str, batch)), "retmode": "json"}))["result"]
            for aid in batch:
                row = result.get(str(aid))
                if row and "error" not in row:
                    file = self.cache / f"esummary/{aid}.json"
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_text(json.dumps(row))
                    found[aid] = row
        return found

    # --- one AID ------------------------------------------------------------------------------------------------
    def description(self, aid: int) -> dict:
        return self._json(f"aid/{aid}/description", PUG, f"assay/aid/{aid}/description/JSON")

    def assay(self, aid: int) -> dict:
        return parse_description(self.description(aid))

    def candidates(self, archetype: dict, limit: int = 10, before_year: int = CUTOFF_YEAR) -> list[dict]:
        """Confirmatory AIDs with a dose-response series and protocol text, from the archetype's `pubchem` hints:
        `search` (Entrez terms) and optional `genes` (PUG-REST target lookup, intersected with the search hits
        when both are given). Deposited before `before_year` (the hold-out cutoff), most tested points first."""
        hints = archetype.get("pubchem") or {}
        hits: list[int] = []
        for term in hints.get("search", []):
            hits += [a for a in self.search(term) if a not in hits]
        if hints.get("genes"):
            by_gene = {a for g in hints["genes"] for a in self.aids_for_gene(g)}
            hits = [a for a in hits if a in by_gene] if hints.get("search") else sorted(by_gene)
        rows = self.summaries(hits)
        kept = [a for a in hits if a in rows and rows[a].get("activityoutcomemethod") == "Confirmatory"
                and _year(rows[a].get("depositdate")) < before_year]
        found, projects = [], set()
        for aid in kept:
            if len(found) >= limit:
                break
            project = (rows[aid].get("currentsourcename"), rows[aid].get("assayname", "")[:40])
            if project in projects:   # one AID per deposited project (some deposit dozens of near-copies)
                continue
            record = self.assay(aid)
            if record["protocol"].strip() and record["series"]:
                projects.add(project)
                found.append({**record, "deposited": rows[aid].get("depositdate", "")[:10]})
        return sorted(found, key=lambda r: (-len(r["series"][0]["concentrations_uM"]), r["aid"]))


def _year(date: str | None) -> int:
    try:
        return int((date or "").split("/")[0])
    except ValueError:
        return 9999   # undated: treat as after the cutoff (never kept)


def _text(lines) -> str:
    return "\n".join(lines or []).strip()


def parse_description(data: dict) -> dict:
    """The fields the protocol DB uses from a PUG-REST description JSON."""
    descr = data["PC_AssayContainer"][0]["assay"]["descr"]
    targets = []
    for t in descr.get("target", []):
        taxid = next((db["tag"]["id"] for db in t.get("organism", {}).get("org", {}).get("db", [])
                      if db.get("db") == "taxon"), None)
        targets.append({"name": t.get("name"), "accession": t.get("mol_id", {}).get("protein_accession"),
                        "gene_id": t.get("mol_id", {}).get("gene_id"), "taxid": taxid})
    series: dict[int, set] = {}
    for column in descr.get("results", []):
        tc = column.get("tc")
        if tc and tc.get("unit") in UNIT_TO_UM:
            series.setdefault(tc.get("dr_id", 0), set()).add(round(tc["concentration"] * UNIT_TO_UM[tc["unit"]], 6))
    source = descr.get("aid_source", {}).get("db", {})
    return {
        "aid": descr["aid"]["id"],
        "version": descr["aid"].get("version"),
        "name": descr.get("name", ""),
        "source": source.get("name", ""),
        "source_id": source.get("source_id", {}).get("str", ""),
        "outcome_method": OUTCOME_METHOD.get(descr.get("activity_outcome_method"), "other"),
        "description": _text(descr.get("description")),
        "protocol": _text(descr.get("protocol")),
        "comment": _text(descr.get("comment")),
        "targets": targets,
        "pmids": [x["xref"]["pmid"] for x in descr.get("xref", []) if "pmid" in x.get("xref", {})],
        "series": [{"dr_id": k, **series_stats(sorted(v))} for k, v in sorted(series.items())],
    }


def series_stats(concentrations_uM: list[float]) -> dict:
    """Top concentration, number of points and fold-step of a tested-concentration series (µM).

    The series is the set of concentration columns in the AID's results table, i.e. the union over all compounds
    in that test. Broad 'DryPowder' and NCGC qHTS AIDs interleave several dilution series in one test, so the union
    is not one dilution: `regular` is False then and `dilution_factor` is None (read the series off the text)."""
    c = sorted(x for x in concentrations_uM if x > 0)
    if not c:
        return {"concentrations_uM": [], "top_uM": None, "n_points": 0, "dilution_factor": None, "regular": False}
    steps = [b / a for a, b in zip(c, c[1:])]
    regular = bool(steps) and min(steps) >= MIN_STEP and max(steps) / min(steps) <= SPREAD
    return {"concentrations_uM": c, "top_uM": c[-1], "n_points": len(c), "regular": regular,
            "dilution_factor": round(statistics.median(steps), 2) if regular else None}


def main() -> None:

    parser = argparse.ArgumentParser(description="PubChem BioAssay lookups for the protocol DB.")
    sub = parser.add_subparsers(dest="command", required=True)
    cand = sub.add_parser("candidates", help="confirmatory dose-response AIDs for an archetype")
    cand.add_argument("archetype")
    cand.add_argument("--limit", type=int, default=10)
    show = sub.add_parser("show", help="an AID's protocol text, target and tested series")
    show.add_argument("aid", type=int)
    args = parser.parse_args()
    pc = PubChem()
    if args.command == "candidates":
        from kg.protocols.build_db import load_archetypes
        archetype = load_archetypes()[args.archetype]
        for r in pc.candidates(archetype, limit=args.limit):
            s = r["series"][0]
            print(f"AID {r['aid']}  {r['deposited']}  {r['source']}: {r['name'][:90]}\n"
                  f"    target {[t['name'] for t in r['targets']]}; {s['n_points']} points, top {s['top_uM']} µM, "
                  f"x{s['dilution_factor']}")
    else:
        r = pc.assay(args.aid)
        print(f"AID {r['aid']} ({r['outcome_method']}, {r['source']}): {r['name']}\ntargets: {r['targets']}")
        for s in r["series"]:
            print(f"series {s['dr_id']}: {s['n_points']} points, top {s['top_uM']} µM, x{s['dilution_factor']}")
        print(f"\n--- protocol ---\n{r['protocol']}\n\n--- comment ---\n{r['comment'][:2000]}")


if __name__ == "__main__":
    main()
