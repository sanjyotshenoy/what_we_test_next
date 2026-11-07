"""Basic typed queries over the knowledge graphs (both kg/*/graph folders, merged). No network calls.

    python -m kg.query resolve KIT
    python -m kg.query activities P10721
    python -m kg.query templates P10721

From Python:

    from kg.query import KG
    kg = KG.load()
    kg.resolve("imatinib"); kg.classes("P10721"); kg.potency_summary("P10721"); kg.templates("P10721")

Every result carries node IDs, so whatever an agent builds on it can cite them. These are the lookups the agent's
tools wrap (HANDOFF.md §3.3); analogs by chemical similarity are not here yet (every Compound node has `smiles`).
"""
import argparse
from pathlib import Path

import kg  # noqa: F401  - picks CPU or GPU mode before pandas/networkx are imported
import networkx as nx
import pandas as pd

from kg.backend import mode
from kg.graph_io import EDGE_COLUMNS, NODE_COLUMNS, props_of, props_text, read_frames, rows

DEFAULT_FOLDERS = [Path("kg/biology/graph"), Path("kg/protocols/graph")]
HIERARCHY = ("MEMBER_OF", "SUBCLASS_OF")


def _as_frame(rows, columns: list[str]) -> pd.DataFrame:
    frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(list(rows), columns=columns)
    frame = frame.reindex(columns=columns).reset_index(drop=True)
    frame["props"] = [props_text(p) for p in frame["props"].to_list()]
    return frame


class KG:
    """Both graphs as pandas frames (`nodes_df`, `edges_df`) plus a networkx MultiDiGraph (`graph`) of the same
    edges. Lookups are frame filters; class chains are graph traversals. Under WWTN_GPU=1 the same calls run
    through cudf.pandas and the nx-cugraph backend (kg/backend.py)."""

    def __init__(self, nodes, edges):
        self.nodes_df = _as_frame(nodes, NODE_COLUMNS)
        self.edges_df = _as_frame(edges, EDGE_COLUMNS)
        self._by_id = self.nodes_df.drop_duplicates("id").set_index("id", drop=False)
        self._name_lower = self.nodes_df["name"].astype(str).str.lower()
        self._id_lower = self.nodes_df["id"].astype(str).str.lower()
        self._chembl_lower = pd.Series([str(props_of(p).get("chembl_id") or "").lower()
                                        for p in self.nodes_df["props"].to_list()], index=self.nodes_df.index)

        self.graph = nx.from_pandas_edgelist(self.edges_df, "src", "dst", edge_attr="rel",
                                             create_using=nx.MultiDiGraph)
        self.graph.add_nodes_from(self.nodes_df["id"])
        hierarchy = self.edges_df[self.edges_df["rel"].isin(HIERARCHY)]
        self._hierarchy = nx.from_pandas_edgelist(hierarchy, "src", "dst", create_using=nx.DiGraph)

        inhibits = self.edges_df[self.edges_df["rel"] == "INHIBITS"]
        props = [props_of(p) for p in inhibits["props"].to_list()]
        self._inhibits = pd.DataFrame({
            "compound": inhibits["src"].to_list(), "target": inhibits["dst"].to_list(),
            "ic50_nM": [float(p["ic50_nM"]) for p in props], "assay": [p.get("assay") for p in props],
            "document": [p.get("document") for p in props], "year": [p.get("year") for p in props],
        })

    @classmethod
    def load(cls, folders: list[Path] | None = None) -> "KG":
        frames = [read_frames(folder) for folder in folders or DEFAULT_FOLDERS]
        return cls(pd.concat([n for n, _ in frames], ignore_index=True),
                   pd.concat([e for _, e in frames], ignore_index=True))

    def node(self, id: str) -> dict | None:
        if id not in self._by_id.index:
            return None
        row = self._by_id.loc[id].to_dict()
        return {**row, "props": props_of(row["props"])}

    def resolve(self, text: str, type: str | None = None) -> list[dict]:
        """Exact ID, then exact name (any case), then a Target's ChEMBL ID, then names containing the text."""
        wanted = text.strip().lower()
        of_type = self.nodes_df["type"] == type if type else pd.Series(True, index=self.nodes_df.index)
        is_target = self.nodes_df["type"] == "Target"
        tiers = [self._id_lower == wanted, self._name_lower == wanted, is_target & (self._chembl_lower == wanted),
                 self._name_lower.str.contains(wanted, regex=False)]
        found, seen = [], set()
        for mask in tiers:
            tier = self.nodes_df[mask & of_type]
            tier = tier.assign(_len=tier["name"].astype(str).str.len()).sort_values(["_len", "id"])
            for row in rows(tier.drop(columns="_len")):
                if row["id"] not in seen:
                    seen.add(row["id"])
                    found.append(row)
        return found[:10]

    def neighbors(self, id: str, rel: str | None = None, direction: str = "out") -> list[dict]:
        edges = self.edges_df if rel is None else self.edges_df[self.edges_df["rel"] == rel]
        rows = []
        for side, other in (("src", "dst"), ("dst", "src")):
            if direction not in (("out", "both") if side == "src" else ("in", "both")):
                continue
            for e in rows(edges[edges[side] == id]):
                rows.append({"rel": e["rel"], "node": self.node(e[other]) or {"id": e[other]}, "props": e["props"]})
        return rows

    def classes(self, target_id: str) -> list[dict]:
        """The target's TargetClass nodes, most specific first, up MEMBER_OF then SUBCLASS_OF."""
        if target_id not in self._hierarchy:
            return []
        chain = list(nx.dfs_preorder_nodes(self._hierarchy, target_id))[1:]
        return [self.node(c) or {"id": c} for c in chain]

    def activities(self, target_id: str, limit: int = 50) -> list[dict]:
        rows = self._inhibits[self._inhibits["target"] == target_id]
        rows = rows.merge(self.nodes_df[["id", "name", "props"]], how="left", left_on="compound", right_on="id")
        rows = rows.sort_values(["ic50_nM", "compound"]).head(limit)
        return [{"compound": r["compound"], "name": r["name"] if isinstance(r["name"], str) else r["compound"],
                 "smiles": props_of(r["props"] if isinstance(r["props"], str) else "").get("smiles", ""),
                 "ic50_nM": float(r["ic50_nM"]), "assay": r["assay"], "document": r["document"], "year": r["year"]}
                for r in rows.to_dict("records")]

    def potency_summary(self, target_id: str) -> dict:
        """The crude concentration-range prior until analogs by similarity exist."""
        values = self._inhibits.loc[self._inhibits["target"] == target_id, "ic50_nM"]
        if values.empty:
            return {"n": 0, "min_nM": None, "median_nM": None, "max_nM": None}
        return {"n": int(values.size), "min_nM": float(values.min()), "median_nM": float(values.median()),
                "max_nM": float(values.max())}

    def templates(self, target_id: str) -> list[dict]:
        class_ids = {c["id"] for c in self.classes(target_id)}
        applicable = self.edges_df[(self.edges_df["rel"] == "APPLICABLE_TO") & self.edges_df["dst"].isin(class_ids)]
        found = []
        for e in applicable.sort_values("src").to_dict("records"):
            protocol = self.node(e["src"]) or {"name": e["src"], "props": {}}
            out = self.edges_df[self.edges_df["src"] == e["src"]]
            targets = lambda rel: [self.node(d) or {"id": d, "name": d, "props": {}}  # noqa: E731
                                   for d in out.loc[out["rel"] == rel, "dst"]]
            found.append({
                "id": e["src"], "name": protocol["name"], "purpose": protocol["props"].get("purpose"),
                "via_class": e["dst"],
                "params": {p["name"]: p["props"] for p in targets("HAS_PARAM")},
                "readout": [r["name"] for r in targets("MEASURES")],
                "answers": [a["id"] for a in targets("ANSWERS")],
            })
        return found


def _table(rows: list[dict], columns: list[str]) -> str:
    cells = [[str(r.get(c, "")) for c in columns] for r in rows]
    widths = [max([len(c)] + [len(row[i]) for row in cells]) for i, c in enumerate(columns)]
    lines = ["  ".join(c.ljust(w) for c, w in zip(columns, widths))]
    lines += ["  ".join(v.ljust(w) for v, w in zip(row, widths)) for row in cells]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the seed knowledge graphs.")
    parser.add_argument("command", choices=["resolve", "neighbors", "classes", "activities", "summary", "templates"])
    parser.add_argument("arg", help="a name or text for resolve; a node ID otherwise")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    kg = KG.load()
    print(f"[{mode()} mode]")
    if args.command == "resolve":
        print(_table(kg.resolve(args.arg), ["id", "type", "name"]))
    elif args.command == "neighbors":
        print(_table([{"rel": r["rel"], "id": r["node"]["id"], "name": r["node"].get("name", "")}
                      for r in kg.neighbors(args.arg, direction="both")][:args.limit], ["rel", "id", "name"]))
    elif args.command == "classes":
        print(_table(kg.classes(args.arg), ["id", "name"]))
    elif args.command == "activities":
        print(_table(kg.activities(args.arg, args.limit), ["compound", "name", "ic50_nM", "assay", "document", "year"]))
    elif args.command == "summary":
        print(kg.potency_summary(args.arg))
    else:
        for t in kg.templates(args.arg):
            params = ", ".join(f"{k}={v['value']} {v['unit']}" for k, v in t["params"].items())
            print(f"{t['id']}  (via {t['via_class']}): {t['purpose']}\n  readout: {', '.join(t['readout'])}\n  {params}")


if __name__ == "__main__":
    main()
