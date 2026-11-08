"""Download every MIC activity in ChEMBL into one long table: screening/data/mic_matrix.csv.

    python -m screening.fetch_mic                     # full download, resumes where it left off
    python -m screening.fetch_mic --limit-pages 3     # a taste of it (3 x 1000 rows)
    python -m screening.fetch_mic --restart           # throw away what is there and start over

One row per (compound, species, measurement), which is the long form of the compound x species MIC matrix the
screening stage learns on. ChEMBL's `activity` endpoint is paginated by offset, so the download is resumable: after
each page is written and flushed, the offset of the next page goes into `<out>.state.json`, and a restart re-opens
the CSV in append mode at that offset. A page that fails is retried with exponential backoff; HTTP 429 and 5xx are
treated as transient, a 4xx as fatal (a bad query will not fix itself).

`only=` keeps the payload to the columns we use - the full activity record has 45 fields and we want 11, which is
roughly a 4x saving over ~800 requests. Provenance is in the table itself: document_chembl_id and assay_chembl_id
say which paper and which assay every number came from, so a prediction built on it can cite them.
"""
import argparse
import csv
import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://www.ebi.ac.uk/chembl/api/data/activity.json"
PAGE = 1000                     # the endpoint's maximum; fewer requests, same data
DELAY_S = 0.2                   # be a good citizen: ~5 requests/s against a public EBI service
MAX_RETRIES = 6
TIMEOUT_S = 120

OUT = Path(__file__).resolve().parent / "data" / "mic_matrix.csv"

# `year` is ChEMBL's `document_year` (the paper's year, not the deposition date); `target_tax_id` is the NCBI taxon
# of the ORGANISM target, which is the only species identifier here that is not a free-text name - species features
# in features.py key off it.
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
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            wait = 2 ** attempt
        if attempt == max_retries - 1:
            raise RuntimeError(f"giving up on offset {offset} after {max_retries} attempts")
        print(f"  offset {offset}: transient failure, retrying in {wait}s")
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


def _state_path(out: Path) -> Path:
    return out.with_suffix(out.suffix + ".state.json")


def _read_state(out: Path) -> dict:
    path = _state_path(out)
    if not path.exists() or not out.exists():
        return {"offset": 0, "rows": 0}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"offset": 0, "rows": 0}                      # a torn state file means start over, not crash


def download(out: Path = OUT, page: int = PAGE, limit_pages: int | None = None, restart: bool = False,
             delay_s: float = DELAY_S) -> dict:
    """Paginate the endpoint into `out`, resuming from the recorded offset. Returns the final state dict."""
    out.parent.mkdir(parents=True, exist_ok=True)
    if restart:
        out.unlink(missing_ok=True)
        _state_path(out).unlink(missing_ok=True)
    state = _read_state(out)
    offset, written = state["offset"], state["rows"]
    if offset:
        print(f"resuming at offset {offset} ({written} rows already in {out.name})")

    fresh = offset == 0
    with open(out, "w" if fresh else "a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        if fresh:
            writer.writeheader()
        total, pages = None, 0
        while total is None or offset < total:
            activities, total = fetch_page(offset, page)
            if not activities:
                break                                        # the endpoint ran out before total_count said so
            writer.writerows(to_row(a) for a in activities)
            handle.flush()
            offset += len(activities)
            written += len(activities)
            # Written *after* the flush, so the state file never promises rows the CSV does not have.
            _state_path(out).write_text(json.dumps({"offset": offset, "rows": written, "total_count": total,
                                                    "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                                                 time.gmtime())}))
            pages += 1
            if pages % 50 == 0 or offset >= total:
                print(f"  {written}/{total} rows ({100 * written / total:.1f}%)")
            if limit_pages is not None and pages >= limit_pages:
                break
            time.sleep(delay_s)
    final = _read_state(out)
    print(f"wrote {final['rows']} rows to {out}")
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--page", type=int, default=PAGE, help=f"rows per request (max {PAGE})")
    parser.add_argument("--limit-pages", type=int, default=None, help="stop after this many pages (for testing)")
    parser.add_argument("--restart", action="store_true", help="ignore any saved progress and start at offset 0")
    parser.add_argument("--delay", type=float, default=DELAY_S, help="seconds between requests")
    args = parser.parse_args()
    download(args.out, page=args.page, limit_pages=args.limit_pages, restart=args.restart, delay_s=args.delay)


if __name__ == "__main__":
    main()
