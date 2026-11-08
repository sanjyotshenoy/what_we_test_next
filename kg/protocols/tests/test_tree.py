"""The decision tree on top of the templates: routing Conditions, and sub-steps nested under their step.

What is checked: every condition in conditions.yaml becomes a node, hangs off the archetypes that cite it and
nothing else, and quotes those archetypes verbatim; sub-steps nest under the right parent without disturbing the
top-level HAS_STEP / NEXT chain, and keep their parent's evidence or a narrower span of it; and
`kg.query.templates()` still answers with the fields it answered with before.
"""
import json

from kg.protocols.build_db import check_condition, load_archetypes, load_conditions, load_templates
from kg.protocols.extract import VERBS
from kg.protocols.tests.conftest import KINASE_CLASS

RELATIONS = ("REQUIRES", "PREFERRED_WHEN")
# the keys kg.query.templates() answered with before the tree was added; another branch depends on them
TEMPLATE_FIELDS = {"id", "name", "purpose", "via_class", "params", "readout", "answers"}


def normalized(text) -> str:
    """An archetype field as build_db writes it: one line, single spaces (`notes` is a list of lines)."""
    if isinstance(text, list):
        text = " ".join(text)
    return " ".join(str(text).split())


def conditions_of(nodes):
    return [n for n in nodes.values() if n["type"] == "Condition"]


def test_every_condition_becomes_a_node_with_its_provenance(graph):
    nodes, _ = graph
    conditions = load_conditions()
    assert len(conditions_of(nodes)) == len(conditions) >= 10
    for condition in conditions:
        node = nodes[condition["id"]]
        assert condition["id"].startswith("cond:") and node["name"] == condition["text"].strip()
        assert node["props"]["machine_checkable"] is bool(condition.get("check"))
        assert node["props"]["derived_from"] == condition["from"]
        assert node["source"]


def test_condition_quotes_are_verbatim_in_the_archetype_they_cite(graph):
    """A condition may not say more than the archetype text it was read from (the rule for adding one)."""
    archetypes = load_archetypes()
    for condition in load_conditions():
        assert condition["from"], condition["id"]
        for origin in condition["from"]:
            archetype = archetypes[origin["archetype"]]
            assert origin["relation"] in RELATIONS
            assert origin["field"] in ("purpose", "notes")
            assert origin["quote"] in normalized(archetype[origin["field"]]), (condition["id"], origin["quote"])


def test_conditions_hang_off_the_protocols_that_cite_them_and_no_others(graph):
    nodes, edges = graph
    routing = [e for e in edges if e["rel"] in RELATIONS]
    expected = {(o["archetype"], o["relation"], c["id"]) for c in load_conditions() for o in c["from"]}
    assert {(e["src"], e["rel"], e["dst"]) for e in routing} == expected
    assert len(routing) == len(expected) >= 15
    for e in routing:
        assert nodes[e["dst"]]["type"] == "Condition" and nodes[e["src"]]["type"] == "Protocol"
        assert e["props"]["quote"] and e["props"]["archetype_field"] and e["source"]
    # every archetype routes on something, and the three curated ones carry at least one hard requirement
    assert {e["src"] for e in routing} == set(load_archetypes())
    for id in load_templates():
        assert any(e["src"] == id and e["rel"] == "REQUIRES" for e in routing), id


def test_conditions_are_reachable_from_the_query_layer(kg):
    found = kg.conditions("proto:kinase_biochem_lum")
    relations = [c["relation"] for c in found]
    assert relations and relations == sorted(relations, key=RELATIONS.index)   # REQUIRES before PREFERRED_WHEN
    recombinant = next(c for c in found if c["id"] == "cond:recombinant_enzyme_available")
    assert recombinant["relation"] == "REQUIRES"
    assert recombinant["quote"] == "when recombinant enzyme is available"
    assert recombinant["check"]
    # and the other way round: which protocols require purified protein
    requiring = {n["node"]["id"] for n in kg.neighbors("cond:recombinant_enzyme_available", direction="in")}
    assert requiring == {"proto:kinase_biochem_lum", "proto:protease_fret_activity"}
    # a condition read off one archetype does not leak to another
    assert "cond:target_is_whole_organism" not in {c["id"] for c in found}


def test_condition_checks_evaluate_over_a_design(graph):
    nodes, _ = graph
    biochemical = {"system": "recombinant DYRK1A", "readout": "luminescence (ADP-Glo)"}
    cellular = {"system": "Ba/F3 EpoR-JAK2V617F cells", "readout": "luminescence (cellular ATP)"}
    enzyme = nodes["cond:recombinant_enzyme_available"]["props"]
    cells = nodes["cond:cultured_cell_line_available"]["props"]
    orthogonal = nodes["cond:orthogonal_non_luminescent_readout_needed"]["props"]
    assert check_condition(enzyme, biochemical) is True
    assert check_condition(enzyme, cellular) is False
    assert check_condition(cells, cellular) is True
    assert check_condition(orthogonal, biochemical) is False
    assert check_condition(orthogonal, {"readout": "TR-FRET ratio"}) is True
    assert check_condition(enzyme, {}) is None                       # a field it needs is missing
    assert check_condition(nodes["cond:labelled_tracer_available"]["props"], biochemical) is None   # no expression


def test_substeps_nest_under_their_parent_without_disturbing_the_top_level(graph):
    nodes, edges = graph
    for id, template in load_templates().items():
        top = [e["dst"] for e in edges if e["src"] == id and e["rel"] == "HAS_STEP"]
        assert len(top) == len(template["steps"])          # sub-steps are not top-level steps
        for i, step in enumerate(template["steps"], start=1):
            step_id = f"{id}/step{i}"
            substeps = [e for e in edges if e["src"] == step_id and e["rel"] == "HAS_SUBSTEP"]
            assert len(substeps) == len(step.get("substeps", [])) == nodes[step_id]["props"]["n_substeps"]
            assert "parent" not in nodes[step_id]["props"]
            for j, (e, substep) in enumerate(zip(substeps, step.get("substeps", [])), start=1):
                node = nodes[e["dst"]]
                assert e["dst"] == f"{step_id}/sub{j}" and e["props"]["order"] == j
                assert node["type"] == "Step" and node["name"] == substep["text"]
                assert node["props"]["parent"] == step_id and node["props"]["order"] == j
                assert node["props"]["verb"] in VERBS and node["source"] == nodes[step_id]["source"]
                # a sub-step never carries an ordering edge: NEXT orders the top level only
                assert not [x for x in edges if x["rel"] == "NEXT" and e["dst"] in (x["src"], x["dst"])]


def test_the_top_level_order_is_unchanged_by_the_sub_steps(graph):
    nodes, edges = graph
    for id, template in load_templates().items():
        chain = [e["dst"] for e in edges if e["src"] == id and e["rel"] == "HAS_STEP"]
        assert [nodes[s]["props"]["order"] for s in chain] == list(range(1, len(template["steps"]) + 1))
        assert [nodes[s]["name"] for s in chain] == [s["text"] for s in template["steps"]]
        nexts = [(e["src"], e["dst"]) for e in edges if e["rel"] == "NEXT" and e["src"] in chain]
        assert nexts == list(zip(chain, chain[1:]))


def test_substep_evidence_is_the_parents_or_narrower(graph):
    """The split may not add evidence: every sub-step quote is a parent quote, or a span inside one."""
    for template in load_templates().values():
        for step in template["steps"]:
            parent = step.get("evidence", [])
            for substep in step.get("substeps", []):
                assert substep["evidence"]
                for item in substep["evidence"]:
                    source = item.get("aid") or item.get("file")
                    assert any(source == (p.get("aid") or p.get("file")) and item["quote"] in p["quote"]
                               for p in parent), (step["text"], item["quote"])


def test_substeps_are_in_the_graph_for_the_steps_we_split(kg):
    """The three curated templates: which steps were split, and which were deliberately left flat."""
    split = {t: [s["order"] for s in kg.steps(t) if s["substeps"]] for t in load_templates()}
    assert split == {"proto:kinase_biochem_lum": [5, 9], "proto:cell_viability_atp": [5],
                     "proto:bacterial_mic_broth": [2, 4]}
    dilution = next(s for s in kg.steps("proto:bacterial_mic_broth") if s["order"] == 2)
    assert [s["verb"] for s in dilution["substeps"]] == ["serial_dilute", "dispense"]
    assert "discard" in dilution["substeps"][1]["text"].lower()


def test_templates_keeps_the_fields_it_had_and_gains_conditions(kg):
    found = kg.templates("Q13627")
    biochemical = next(t for t in found if t["id"] == "proto:kinase_biochem_lum")
    assert TEMPLATE_FIELDS <= set(biochemical)
    assert biochemical["via_class"] == KINASE_CLASS
    assert biochemical["params"]["n_points"]["value"] == 9
    assert biochemical["readout"] == ["luminescence (ADP-Glo)"]
    assert biochemical["answers"] == ["qtype:potency"]
    assert biochemical["purpose"].startswith("Measure how potently a compound inhibits")
    assert json.dumps(biochemical)        # still serializable, with the conditions in it
    assert "cond:recombinant_enzyme_available" in {c["id"] for c in biochemical["conditions"]}
    assert set(biochemical) - TEMPLATE_FIELDS == {"conditions"}      # the only added field
