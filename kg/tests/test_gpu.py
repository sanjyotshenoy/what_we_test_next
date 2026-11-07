"""GPU mode gives exactly the CPU results. Skipped when no GPU is visible (e.g. inside Claude Code's sandbox).

Run it on the GPU with:  .venv/bin/python -m pytest kg/tests/test_gpu.py -q
"""
import json
import os
import subprocess
import sys
import textwrap

import pytest

from kg.backend import gpu_available

pytestmark = pytest.mark.skipif(not gpu_available(), reason="no GPU visible (needs RAPIDS and a CUDA device)")

SCRIPT = textwrap.dedent("""
    import json, sys
    import kg  # first: picks the backend before pandas is imported
    import pandas as pd
    from kg.biology.targets import ProteinClass, TargetInfo
    from kg.backend import mode
    from kg.biology.build_seed import seed_frames
    from kg.graph_io import write_graph
    from kg.query import KG

    folder = sys.argv[1]
    kit = TargetInfo("CHEMBL1936", "Mast/stem cell growth factor receptor Kit", "P10721", "Homo sapiens",
                     "SINGLE PROTEIN", [ProteinClass(159, "PDGFR family", 1100, 5), ProteinClass(1100, "Protein Kinase", None, 3)])
    acts = pd.DataFrame([{
        "activity_id": i, "molecule_chembl_id": f"CHEMBL{i}", "molecule_pref_name": None, "canonical_smiles": "CCO",
        "target_chembl_id": "CHEMBL1936", "assay_chembl_id": f"A{i % 3}", "assay_description": "Inhibition of KIT",
        "bao_format": "BAO_0000357", "assay_type": "B", "standard_value": float(1 + (i * 37) % 997),
        "document_chembl_id": f"D{i % 5}", "document_year": 2000 + i % 20, "pchembl_value": 7.0} for i in range(300)])
    docs = pd.DataFrame([{"document_chembl_id": f"D{i}", "year": 2010, "pubmed_id": i, "doi": "x", "title": f"T{i}",
                          "journal": "J"} for i in range(5)])
    extra = pd.DataFrame([{"compound": "CHEMBL_NEW", "compound_name": "", "smiles": "CCN"}])
    nodes, edges = seed_frames(acts, {"CHEMBL1936": kit}, docs, extra_compounds=extra)
    nodes = pd.concat([nodes, pd.DataFrame([{"id": "proto:x", "type": "Protocol", "name": "x",
                                             "props": {"purpose": "potency"}, "source": "t"}])])
    edges = pd.concat([edges, pd.DataFrame([{"src": "proto:x", "rel": "APPLICABLE_TO", "dst": "chembl_class:1100",
                                             "props": {}, "source": "t"}])])
    write_graph(folder, nodes, edges)
    kg = KG.load([folder])
    print(json.dumps({"mode": mode(), "n_nodes": len(kg.nodes_df), "n_edges": kg.graph.number_of_edges(),
                      "resolve": [n["id"] for n in kg.resolve("kit")], "classes": [c["id"] for c in kg.classes("P10721")],
                      "activities": kg.activities("P10721", limit=25), "summary": kg.potency_summary("P10721"),
                      "templates": [t["id"] for t in kg.templates("P10721")]}, sort_keys=True))
""")


def run(folder, gpu: bool) -> dict:
    env = {**os.environ, "WWTN_GPU": "1" if gpu else ""}
    result = subprocess.run([sys.executable, "-c", SCRIPT, str(folder)], capture_output=True, text=True, env=env,
                            cwd=os.getcwd())
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_gpu_matches_cpu(tmp_path):
    cpu = run(tmp_path / "cpu", gpu=False)
    gpu = run(tmp_path / "gpu", gpu=True)
    assert cpu.pop("mode") == "cpu"
    assert gpu.pop("mode") == "gpu"
    assert gpu == cpu
    assert (tmp_path / "cpu" / "edges.csv").read_text() == (tmp_path / "gpu" / "edges.csv").read_text()
