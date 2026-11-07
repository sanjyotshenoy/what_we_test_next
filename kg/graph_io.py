"""Read and write a graph in the kg/README.md format: graph/nodes.csv and graph/edges.csv, `props` as JSON.

Graphs are pandas DataFrames in memory (GPU-accelerated under WWTN_GPU=1, see kg/backend.py). In a frame, `props`
stays canonical JSON text (sorted keys): cudf turns a column of dicts into a struct column that gives every row
every key, so dicts only appear once a row leaves the frame (`props_of`, `read_graph`).
"""
import json
from pathlib import Path

import kg  # noqa: F401  - picks CPU or GPU mode before pandas is imported
import pandas as pd

NODE_COLUMNS = ["id", "type", "name", "props", "source"]
EDGE_COLUMNS = ["src", "rel", "dst", "props", "source"]


def _frame(rows, columns: list[str]) -> pd.DataFrame:
    frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(list(rows), columns=columns)
    return frame.reindex(columns=columns)


def props_text(p) -> str:
    """Canonical JSON text for a props value (dict, JSON text, or missing)."""
    if isinstance(p, str):
        p = json.loads(p or "{}")
    return json.dumps(p if isinstance(p, dict) else {}, sort_keys=True)


def props_of(p) -> dict:
    """A props value (JSON text or dict) as a dict."""
    if isinstance(p, dict):
        return p
    return json.loads(p) if isinstance(p, str) and p else {}


def _props_json(props: pd.Series) -> pd.Series:
    return pd.Series([props_text(p) for p in props.to_list()], index=props.index, dtype=object)


def write_graph(folder: Path, nodes, edges) -> None:
    """`nodes`/`edges`: DataFrames or lists of dicts. Duplicate node IDs keep the first row; duplicate edges are
    identical (src, rel, dst, props) rows."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    node_frame = _frame(nodes, NODE_COLUMNS).assign(props=lambda f: _props_json(f["props"]))
    edge_frame = _frame(edges, EDGE_COLUMNS).assign(props=lambda f: _props_json(f["props"]))
    node_frame.drop_duplicates(subset="id").to_csv(folder / "nodes.csv", index=False)
    edge_frame.drop_duplicates(subset=["src", "rel", "dst", "props"]).to_csv(folder / "edges.csv", index=False)


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def read_frames(folder: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    folder = Path(folder)
    return _read(folder / "nodes.csv"), _read(folder / "edges.csv")


def rows(frame: pd.DataFrame) -> list[dict]:
    """Frame rows as plain dicts, with `props` parsed."""
    return [{**r, "props": props_of(r["props"])} for r in frame.to_dict("records")]


def read_graph(folder: Path) -> tuple[list[dict], list[dict]]:
    nodes, edges = read_frames(folder)
    return rows(nodes), rows(edges)
