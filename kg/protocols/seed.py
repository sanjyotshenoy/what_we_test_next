"""Seed protocol graph: three hand-written dose-response templates, BAO-tagged and linked to the kinase class.

TODO(final): seed graph for testing; replace with the kg/protocols owner's graph.

    python -m kg.protocols.seed          # writes kg/protocols/graph/{nodes,edges}.csv

The defaults are typical vendor-style choices written from general knowledge, never from a 2024+ (held-out) paper.
Every protocol is APPLICABLE_TO chembl_class:1100 (ChEMBL "Protein Kinase"), the TargetClass node that the
biology graph defines; TargetClass IDs are the bridge between the two graphs.
"""
from pathlib import Path

from kg.graph_io import write_graph

OUT = Path("kg/protocols/graph")
SOURCE = "hand-curated"
KINASE_CLASS = "chembl_class:1100"

SHARED_PARAMS = {
    "top_concentration": (10, "uM"),
    "dilution_factor": (3, "fold"),
    "n_points": (10, "concentrations"),
    "replicates": (3, "wells per concentration"),
    "dmso_percent": (1, "% v/v"),
}

TEMPLATES = [
    {
        "id": "proto:kinase_biochem_lum",
        "name": "Biochemical kinase inhibition, luminescence readout",
        "purpose": "Measure the potency (IC50) of an inhibitor on a purified kinase.",
        "answers": "qtype:potency",
        "bao_format": "BAO:0000357", "bao_endpoint": "BAO:0000190",
        "readout": ("readout:luminescence_adp", "luminescence (ADP or ATP detection)"),
        "params": {"incubation_time": (60, "min")},
        "steps": [
            ("serial_dilute", "Serially dilute the compound in DMSO across the series."),
            ("dispense", "Dispense kinase and substrate in assay buffer into the plate."),
            ("transfer", "Transfer the compound series into the assay wells."),
            ("incubate", "Pre-incubate compound with kinase."),
            ("dispense", "Start the reaction with ATP; after the reaction time add the detection reagent."),
            ("incubate", "Incubate for the detection signal to develop."),
            ("read", "Read luminescence on the plate reader."),
        ],
    },
    {
        "id": "proto:cell_viability_atp",
        "name": "Cell viability, luminescent ATP readout",
        "purpose": "Measure the effect of a compound on the viability of cultured cells.",
        "answers": "qtype:cellular_potency",
        "bao_format": "BAO:0000219", "bao_endpoint": "BAO:0000190",
        "readout": ("readout:luminescence_cellular_atp", "luminescence (cellular ATP)"),
        "params": {"incubation_time": (72, "h")},
        "steps": [
            ("dispense", "Seed cells into the plate and let them attach."),
            ("serial_dilute", "Serially dilute the compound in DMSO across the series."),
            ("transfer", "Transfer the compound series onto the cells."),
            ("incubate", "Incubate cells with compound."),
            ("dispense", "Add the ATP detection reagent."),
            ("incubate", "Incubate for the signal to stabilise."),
            ("read", "Read luminescence on the plate reader."),
        ],
    },
    {
        "id": "proto:kinase_binding_competition",
        "name": "Kinase competition binding",
        "purpose": "Measure how strongly a compound binds a kinase, by competition with a labelled ligand.",
        "answers": "qtype:binding",
        "bao_format": "BAO:0000357", "bao_endpoint": None,
        "readout": ("readout:binding_signal", "binding signal (labelled ligand displaced)"),
        "params": {"incubation_time": (60, "min")},
        "steps": [
            ("serial_dilute", "Serially dilute the compound in DMSO across the series."),
            ("dispense", "Dispense kinase and labelled ligand into the plate."),
            ("transfer", "Transfer the compound series into the assay wells."),
            ("incubate", "Incubate to binding equilibrium."),
            ("read", "Read the binding signal."),
        ],
    },
]

CONTROLS = [  # (id, name, BAO role)
    ("reagent:dmso_vehicle", "DMSO vehicle (negative control)", "BAO:0000079"),
    ("reagent:staurosporine", "staurosporine (positive control)", "BAO:0000080"),
]


def seed_rows() -> tuple[list[dict], list[dict]]:
    nodes, edges = [], []
    node = lambda id, type, name, props=None: nodes.append(  # noqa: E731
        {"id": id, "type": type, "name": name, "props": props or {}, "source": SOURCE})
    edge = lambda src, rel, dst, props=None: edges.append(  # noqa: E731
        {"src": src, "rel": rel, "dst": dst, "props": props or {}, "source": SOURCE})

    for cid, name, bao in CONTROLS:
        node(cid, "Reagent", name, {"bao": bao})
    for t in TEMPLATES:
        pid = t["id"]
        node(pid, "Protocol", t["name"], {"purpose": t["purpose"], "bao_format": t["bao_format"],
                                          "bao_endpoint": t["bao_endpoint"]})
        node(t["answers"], "QuestionType", t["answers"].split(":", 1)[1])
        edge(pid, "ANSWERS", t["answers"])
        edge(pid, "APPLICABLE_TO", KINASE_CLASS)
        readout_id, readout_name = t["readout"]
        node(readout_id, "Readout", readout_name)
        edge(pid, "MEASURES", readout_id)
        for cid, _, _ in CONTROLS:
            edge(pid, "USES", cid)
        for name, (value, unit) in {**SHARED_PARAMS, **t["params"]}.items():
            param_id = f"{pid}/param/{name}"
            node(param_id, "Parameter", name, {"value": value, "unit": unit})
            edge(pid, "HAS_PARAM", param_id)
        step_ids = []
        for i, (verb, text) in enumerate(t["steps"], start=1):
            step_id = f"{pid}/step{i}"
            node(step_id, "Step", text, {"verb": verb, "order": i})
            edge(pid, "HAS_STEP", step_id)
            if step_ids:
                edge(step_ids[-1], "NEXT", step_id)
            step_ids.append(step_id)
    return nodes, edges


def main() -> None:
    nodes, edges = seed_rows()
    write_graph(OUT, nodes, edges)
    print(f"wrote {len(nodes)} nodes and {len(edges)} edges to {OUT}")


if __name__ == "__main__":
    main()
