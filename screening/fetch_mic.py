"""Every MIC activity in ChEMBL as one long table: screening/data/mic_matrix.csv.

    python -m screening.fetch_mic                     # local ChEMBL 37 dump if there is one, else the REST API
    python -m screening.fetch_mic --sqlite <path>     # the dump at that path: one query, seconds (PREFERRED)
    python -m screening.fetch_mic --source rest       # the fallback: ~45 min over 6 sharded REST streams
    python -m screening.fetch_mic --limit-pages 3     # REST only: a taste of it (3 x 1000 rows per shard)
    python -m screening.fetch_mic --restart           # REST only: throw away saved progress and start over

One row per (compound, species, measurement), which is the long form of the compound x species MIC matrix the
screening stage learns on.

**The local SQLite dump is the route to use.** It answers the whole table in one query, brings canonical SMILES
and molecular weights with it (so it also replaces the ~116k molecule lookups features.py would otherwise make),
takes seconds rather than 45 minutes, and is reproducible - the same dump gives the same table forever. The REST
path is the **fallback**, for a machine where downloading 5.8 GB (30 GB unpacked) is not worth it.
`--source auto` (the default) uses the dump when one is present and falls back to REST when not.

The dump is the same one kg/biology/chembl_db.py uses, at the same path and honouring the same `CHEMBL_SQLITE`
environment variable, and pinned to the same release (**ChEMBL 37**): "latest" would shift the counts, and the
splits cut from the matrix would stop being comparable between machines.

**No matrix is committed to this repo** (screening/README.md says why), so this script has to be run before
anything else in the folder works.

The REST endpoint answers a page of 1000 in ~8s whatever the offset, so one stream would take ~2h for 799 pages. The
offset range is therefore cut into `--workers` contiguous **shards**, each written to its own part file and
concatenated at the end. Each shard records the offset of its next page after every flush, so an interrupted
download resumes per shard rather than from the start; the shard plan itself is saved so a resume cuts the range
the same way. A page that fails is retried with exponential backoff; HTTP 429 and 5xx are treated as transient, a
4xx as fatal (a bad query will not fix itself).

`only=` keeps the payload to the columns we use - the full activity record has 45 fields and we want 11, roughly a
4x saving over ~800 requests. Provenance is in the table itself: document_chembl_id and assay_chembl_id say which
paper and which assay every number came from, so a prediction built on it can cite them.
"""
import argparse
import csv
import gzip
import json
import os
import shutil
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

API = "https://www.ebi.ac.uk/chembl/api/data/activity.json"
PAGE = 1000                     # the endpoint's maximum; fewer requests, same data
WORKERS = 6                     # 6 streams x ~8s/page is well under 1 request/s against a public EBI service
DELAY_S = 0.2
MAX_RETRIES = 6
TIMEOUT_S = 180

OUT = Path(__file__).resolve().parent / "data" / "mic_matrix.csv"

# `year` is ChEMBL's `document_year` (the paper's year, not the deposition date); `target_tax_id` is the NCBI taxon
# of the ORGANISM target, the only species identifier here that is not a free-text name - species features in
# features.py key off it.
API_FIELDS = ["molecule_chembl_id", "target_chembl_id", "target_organism", "target_tax_id", "standard_value",
              "standard_units", "standard_relation", "standard_type", "document_chembl_id", "document_year",
              "assay_chembl_id"]
COLUMNS = ["molecule_chembl_id", "target_chembl_id", "target_organism", "target_tax_id", "standard_value",
           "standard_units", "standard_relation", "standard_type", "document_chembl_id", "year",
           "assay_chembl_id", "censored"]

# A censored measurement is a bound, not a value: ">128 ug/mL" means "we stopped at 128 and it still grew". Novel
# compounds' commensal readings are usually censored this way, so dropping them would drop most of the
# commensal-sparing signal - they are kept and flagged, and the baselines score them as a threshold call.
CENSORING_RELATIONS = {">", "<", ">=", "<="}


def censored(relation: str | None) -> bool:
    """True when the row records a bound rather than a measured value."""
    return (relation or "").strip() in CENSORING_RELATIONS


def _url(offset: int, page: int) -> str:
    query = urllib.parse.urlencode({"standard_type": "MIC", "limit": page, "offset": offset,
                                    "only": ",".join(API_FIELDS)})
    return f"{API}?{query}"


def fetch_page(offset: int, page: int = PAGE, max_retries: int = MAX_RETRIES) -> tuple[list[dict], int]:
    """One page of activities, plus the endpoint's total_count. Retries transient failures with backoff."""
    url = _url(offset, page)
    for attempt in range(max_retries):
        try:
            request = urllib.request.Request(url, headers={"Accept": "application/json",
                                                           "User-Agent": "wwtn-screening/0.1 (biohack)"})
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                body = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
            payload = json.loads(body)
            return payload.get("activities", []), int(payload.get("page_meta", {}).get("total_count", 0))
        except urllib.error.HTTPError as error:
            if error.code < 500 and error.code != 429:
                raise                                        # a malformed query will not succeed on retry
            wait = 2 ** attempt
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, OSError):
            wait = 2 ** attempt
        if attempt == max_retries - 1:
            raise RuntimeError(f"giving up on offset {offset} after {max_retries} attempts")
        print(f"  offset {offset}: transient failure, retrying in {wait}s", flush=True)
        time.sleep(wait)
    raise AssertionError("unreachable")


def to_row(activity: dict) -> dict:
    """One API record as a CSV row (API field names -> our column names, plus the derived flag)."""
    relation = activity.get("standard_relation")
    return {"molecule_chembl_id": activity.get("molecule_chembl_id") or "",
            "target_chembl_id": activity.get("target_chembl_id") or "",
            "target_organism": activity.get("target_organism") or "",
            "target_tax_id": activity.get("target_tax_id") or "",
            "standard_value": activity.get("standard_value") or "",
            "standard_units": activity.get("standard_units") or "",
            "standard_relation": relation or "",
            "standard_type": activity.get("standard_type") or "",
            "document_chembl_id": activity.get("document_chembl_id") or "",
            "year": activity.get("document_year") or "",
            "assay_chembl_id": activity.get("assay_chembl_id") or "",
            "censored": censored(relation)}


# --- source 2: a local ChEMBL SQLite dump ------------------------------------------------------------------

# The same dump, path and env var as kg/biology/chembl_db.py, and the same release (ChEMBL 37) - see that module
# for how to get it. Not present on the machine that produced the committed CSV, so this path is UNTESTED here.
# TODO(final): run it against a real chembl_37.db and check the row count against the REST pull's 798,852.
DEFAULT_SQLITE = Path("data/raw/chembl/chembl_37/chembl_37_sqlite/chembl_37.db")

# `target_type = 'ORGANISM'` is the one place the two sources differ: the REST pull takes every MIC activity and
# lets screening.splits.load_matrix drop the rows with no organism (cell lines, mostly), while this filters in SQL
# because it is free to do so. It also keeps a handful of MIC rows on bacterial SINGLE PROTEIN targets that the
# REST table has and this one does not - a few hundred out of ~800k. The README says which source made the CSV.
MIC_SQL = """
SELECT md.chembl_id AS molecule_chembl_id, td.chembl_id AS target_chembl_id,
       td.organism AS target_organism, td.tax_id AS target_tax_id,
       act.standard_value, act.standard_units, act.standard_relation, act.standard_type,
       d.chembl_id AS document_chembl_id, d.year, a.chembl_id AS assay_chembl_id,
       cs.canonical_smiles, cp.full_mwt
FROM activities act
JOIN assays a               ON a.assay_id = act.assay_id
JOIN target_dictionary td   ON td.tid = a.tid
JOIN molecule_dictionary md ON md.molregno = act.molregno
LEFT JOIN compound_structures cs ON cs.molregno = act.molregno
LEFT JOIN compound_properties cp ON cp.molregno = act.molregno
LEFT JOIN docs d            ON d.doc_id = act.doc_id
WHERE act.standard_type = 'MIC' AND td.target_type = 'ORGANISM'
"""

# Written here rather than through features.py because features.py imports this module; duplicating three column
# names is cheaper than a circular import. features.smiles_table() reads exactly this shape.
SMILES_COLUMNS = ["molecule_chembl_id", "canonical_smiles", "full_mwt"]


def sqlite_path(explicit: Path | str | None = None) -> Path | None:
    """The dump to use: an explicit path, else $CHEMBL_SQLITE, else the default location if it is there."""
    for candidate in (explicit, os.environ.get("CHEMBL_SQLITE"), DEFAULT_SQLITE):
        if candidate and Path(candidate).exists():
            return Path(candidate)
    if explicit:                                             # asked for by name: say so rather than falling back
        raise FileNotFoundError(f"no ChEMBL SQLite dump at {explicit} (see kg/biology/chembl_db.py for the dump)")
    return None


def download_sqlite(out: Path = OUT, path: Path | str | None = None, smiles_out: Path | None = None) -> dict:
    """The whole MIC table from a local dump, plus the SMILES cache it brings along for free."""
    database = sqlite_path(path)
    if database is None:
        raise FileNotFoundError(f"no ChEMBL SQLite dump found (tried $CHEMBL_SQLITE and {DEFAULT_SQLITE})")
    out.parent.mkdir(parents=True, exist_ok=True)
    smiles_out = smiles_out if smiles_out is not None else out.parent / "smiles.csv.gz"

    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    structures, rows = {}, 0
    started = time.time()
    with open(out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for record in connection.execute(MIC_SQL):           # streamed, so a ~800k-row result stays off the heap
            row = to_row(dict(record))
            row["year"] = record["year"] or ""               # the dump calls it `year`, the API `document_year`
            writer.writerow(row)
            rows += 1
            if record["canonical_smiles"]:
                structures[record["molecule_chembl_id"]] = {
                    "molecule_chembl_id": record["molecule_chembl_id"],
                    "canonical_smiles": record["canonical_smiles"], "full_mwt": record["full_mwt"] or ""}
    connection.close()

    with gzip.open(smiles_out, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SMILES_COLUMNS)
        writer.writeheader()
        for key in sorted(structures):
            writer.writerow(structures[key])

    compressed = out.with_suffix(out.suffix + ".gz")
    with open(out, "rb") as source, gzip.open(compressed, "wb", compresslevel=9) as target:
        shutil.copyfileobj(source, target)
    state = {"source": "sqlite", "database": str(database), "rows": rows, "compounds_with_smiles": len(structures),
             "status": "complete", "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "elapsed_s": round(time.time() - started, 1)}
    _state_path(out).write_text(json.dumps(state, indent=2))
    print(f"wrote {rows} rows to {out} and {len(structures)} SMILES to {smiles_out.name} "
          f"in {state['elapsed_s']}s", flush=True)
    return state


# --- shard bookkeeping -------------------------------------------------------------------------------------

def _state_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".state.json")


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None                                          # a torn state file means redo the work, not crash


def shard_ranges(total: int, workers: int, page: int = PAGE) -> list[tuple[int, int]]:
    """Cut [0, total) into `workers` contiguous half-open ranges on page boundaries."""
    pages = max(1, -(-total // page))                        # ceil
    per = -(-pages // max(1, min(workers, pages)))           # pages per shard
    bounds = [(first * page, min(total, (first + per) * page)) for first in range(0, pages, per)]
    return [(start, stop) for start, stop in bounds if start < stop]


def _part_path(out: Path, index: int) -> Path:
    return out.with_name(f"{out.stem}.part{index}{out.suffix}")


def download_range(part: Path, start: int, stop: int, page: int = PAGE, delay_s: float = DELAY_S,
                   limit_pages: int | None = None, label: str = "") -> int:
    """Fetch offsets [start, stop) into `part`, resuming from its recorded offset. Returns rows in the file."""
    state = _read_json(_state_path(part)) if part.exists() else None
    offset = state["offset"] if state and state.get("start") == start else start
    written = state["rows"] if state and state.get("start") == start else 0
    if offset >= stop:
        print(f"{label} already complete ({written} rows)", flush=True)
        return written

    fresh = offset == start
    with open(part, "w" if fresh else "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        pages = 0
        while offset < stop:
            activities, _ = fetch_page(offset, min(page, stop - offset))
            if not activities:
                break                                        # the endpoint ran out before total_count said so
            writer.writerows(to_row(a) for a in activities)
            handle.flush()
            offset += len(activities)
            written += len(activities)
            # Written *after* the flush, so the state file never promises rows the part file does not have.
            _state_path(part).write_text(json.dumps({"start": start, "stop": stop, "offset": offset,
                                                     "rows": written}))
            pages += 1
            if pages % 25 == 0:
                print(f"{label} {written}/{stop - start} rows", flush=True)
            if limit_pages is not None and pages >= limit_pages:
                break
            time.sleep(delay_s)
    print(f"{label} done: {written} rows", flush=True)
    return written


def _concatenate(out: Path, parts: list[Path]) -> int:
    """Join the part files in offset order into one CSV with a single header row."""
    rows = 0
    with open(out, "w", newline="", encoding="utf-8") as handle:
        handle.write(",".join(COLUMNS) + "\n")
        for part in parts:
            with open(part, encoding="utf-8") as source:
                shutil.copyfileobj(source, handle)
            with open(part, encoding="utf-8") as source:
                rows += sum(1 for _ in source)
    return rows


def download(out: Path = OUT, page: int = PAGE, workers: int = WORKERS, limit_pages: int | None = None,
             restart: bool = False, delay_s: float = DELAY_S, keep_parts: bool = False) -> dict:
    """Paginate the endpoint into `out` with `workers` sharded streams. Returns the final state dict."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if restart:
        for stale in out.parent.glob(f"{out.stem}*"):
            stale.unlink()

    plan = _read_json(_state_path(out)) if _state_path(out).exists() else None
    if plan and plan.get("page") == page and plan.get("limit_pages") == limit_pages:
        total, ranges = plan["total_count"], [tuple(r) for r in plan["shards"]]
        print(f"resuming the saved {len(ranges)}-shard plan over {total} rows", flush=True)
    else:
        _, total = fetch_page(0, 1)                          # one cheap request for total_count
        ranges = shard_ranges(total, workers, page)
        print(f"{total} MIC activities; {len(ranges)} shards of ~{ranges[0][1] - ranges[0][0]} rows", flush=True)
        _state_path(out).write_text(json.dumps({"total_count": total, "page": page, "limit_pages": limit_pages,
                                                "shards": [list(r) for r in ranges], "status": "downloading"}))

    parts = [_part_path(out, i) for i in range(len(ranges))]
    started = time.time()
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(ranges)))) as pool:
        futures = [pool.submit(download_range, part, start, stop, page, delay_s, limit_pages, f"[shard {i}]")
                   for i, (part, (start, stop)) in enumerate(zip(parts, ranges))]
        for future in futures:
            future.result()                                  # re-raise the first shard failure

    rows = _concatenate(out, parts)
    # The plain CSV is ~96 MB, past what this repo commits (CONTRIBUTING.md); the gzip is ~a quarter of that and
    # is what gets committed. screening.splits.data_path() reads whichever of the two is present.
    compressed = out.with_suffix(out.suffix + ".gz")
    with open(out, "rb") as source, gzip.open(compressed, "wb", compresslevel=9) as target:
        shutil.copyfileobj(source, target)
    print(f"gzipped to {compressed.name} ({compressed.stat().st_size / 1e6:.1f} MB)", flush=True)
    state = {"source": "rest", "total_count": total, "rows": rows, "page": page, "limit_pages": limit_pages,
             "shards": [list(r) for r in ranges], "status": "complete",
             "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "elapsed_s": round(time.time() - started, 1)}
    _state_path(out).write_text(json.dumps(state, indent=2))
    if not keep_parts:
        for part in parts:
            part.unlink(missing_ok=True)
            _state_path(part).unlink(missing_ok=True)
    print(f"wrote {rows} rows to {out} in {state['elapsed_s']}s", flush=True)
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--page", type=int, default=PAGE, help=f"rows per request (max {PAGE})")
    parser.add_argument("--workers", type=int, default=WORKERS, help="parallel offset shards")
    parser.add_argument("--limit-pages", type=int, default=None, help="stop each shard after this many pages")
    parser.add_argument("--restart", action="store_true", help="delete any saved progress and start over")
    parser.add_argument("--delay", type=float, default=DELAY_S, help="seconds between requests within a shard")
    parser.add_argument("--keep-parts", action="store_true", help="do not delete the per-shard part files")
    parser.add_argument("--source", choices=("auto", "rest", "sqlite"), default="auto",
                        help="auto (default) uses a local ChEMBL 37 dump if there is one, else the REST API")
    parser.add_argument("--sqlite", type=Path, default=None,
                        help=f"the ChEMBL 37 SQLite dump (default: $CHEMBL_SQLITE, else {DEFAULT_SQLITE})")
    args = parser.parse_args()

    use_sqlite = args.source == "sqlite" or args.sqlite is not None or (
        args.source == "auto" and sqlite_path() is not None)
    if use_sqlite:
        download_sqlite(args.out, args.sqlite)
    else:
        download(args.out, page=args.page, workers=args.workers, limit_pages=args.limit_pages,
                 restart=args.restart, delay_s=args.delay, keep_parts=args.keep_parts)


if __name__ == "__main__":
    main()
