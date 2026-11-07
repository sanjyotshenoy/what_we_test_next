"""The built protocol graph: shape, provenance, the query layer's edges, and routing by target class.

The `graph` and `kg` fixtures are in conftest.py (test_tree.py uses them too)."""
from kg.protocols.build_db import load_archetypes, load_rules, load_templates
from kg.protocols.extract import VERBS
from kg.protocols.tests.conftest import KINASE_CLASS


def protocols(nodes):
    return [n for n in nodes.values() if n["type"] == "Protocol"]


def test_every_archetype_becomes_a_protocol_with_a_purpose(graph):
    nodes, _ = graph
    found = protocols(nodes)
    assert {p["id"] for p in found} == set(load_archetypes())
    assert len(found) == 8
    assert all(p["props"]["purpose"] for p in found)
    assert sum(1 for p in found if p["props"]["negative_control"]) == 3


def test_curated_templates_have_steps_params_and_controls(graph):
    nodes, edges = graph
    curated = set(load_templates())
    assert len(curated) >= 3
    for id in curated:
        steps = [e["dst"] for e in edges if e["src"] == id and e["rel"] == "HAS_STEP"]
        params = [e["dst"] for e in edges if e["src"] == id and e["rel"] == "HAS_PARAM"]
        controls = [e["dst"] for e in edges if e["src"] == id and e["rel"] == "USES"]
        assert steps and params and controls
        assert nodes[id]["props"]["has_template"] and nodes[id]["props"]["exemplar_aids"]
        assert "agent-curated" in nodes[id]["props"]["curation"]


def test_steps_form_one_chain_with_verbs_from_the_closed_set(graph):
    nodes, edges = graph
    for id in load_templates():
        steps = [e["dst"] for e in edges if e["src"] == id and e["rel"] == "HAS_STEP"]
        nexts = {e["src"]: e["dst"] for e in edges if e["rel"] == "NEXT" and e["src"] in steps}
        first = [s for s in steps if s not in nexts.values()]
        assert len(first) == 1
        chain = [first[0]]
        while chain[-1] in nexts:
            chain.append(nexts[chain[-1]])
        assert sorted(chain) == sorted(steps)
        assert all(nodes[s]["props"]["verb"] in VERBS for s in steps)
        assert [nodes[s]["props"]["order"] for s in chain] == list(range(1, len(chain) + 1))


def test_every_parameter_traces_to_an_aid_or_a_file(graph):
    nodes, _ = graph
    params = [n for n in nodes.values() if n["type"] == "Parameter"]
    assert params
    for p in params:
        assert p["props"]["value"] is not None and p["props"]["observed"]
        for observation in p["props"]["observed"]:
            assert observation.get("aid") or observation.get("file")
            assert observation["quote"]


def test_every_node_and_edge_has_a_source(graph):
    nodes, edges = graph
    assert all(n["source"] for n in nodes.values())
    assert all(e["source"] for e in edges)


def test_rules_are_nodes_linked_both_ways(graph):
    nodes, edges = graph
    rules = load_rules()
    assert len(nodes_of(nodes, "Rule")) == len(rules) >= 10
    for rule in rules:
        node = nodes[rule["id"]]
        assert node["props"]["agm_nbk"].startswith("NBK") and node["props"]["quote"]
        assert node["props"]["machine_checkable"] is bool(rule.get("check"))
        targets = {e["src"] for e in edges if e["rel"] == "HAS_RULE" and e["dst"] == rule["id"]}
        reverse = {e["dst"] for e in edges if e["rel"] == "APPLIES_TO" and e["src"] == rule["id"]}
        assert targets == reverse and targets
        if rule["applies_to"] == "all":
            assert targets == set(load_archetypes())
        else:
            assert targets == set(rule["applies_to"])


def nodes_of(nodes, type):
    return [n for n in nodes.values() if n["type"] == type]


def test_query_templates_still_works_and_routes_by_class(kg):
    found = kg.templates("Q13627")
    ids = [t["id"] for t in found]
    assert "proto:kinase_biochem_lum" in ids
    assert all(t["via_class"] == KINASE_CLASS for t in found)
    # the non-kinase negative controls must never be offered for a kinase question
    assert not {"proto:gpcr_camp_functional", "proto:protease_fret_activity",
                "proto:bacterial_mic_broth"} & set(ids)
    biochem = next(t for t in found if t["id"] == "proto:kinase_biochem_lum")
    assert biochem["params"]["n_points"]["value"] == 9
    assert biochem["readout"] == ["luminescence (ADP-Glo)"]
    assert biochem["answers"] == ["qtype:potency"]


def test_query_templates_routes_a_protease_to_the_protease_archetype(kg):
    assert [t["id"] for t in kg.templates("P00533")] == ["proto:protease_fret_activity"]


def test_rules_reachable_from_a_protocol(kg):
    rules = [n["node"]["id"] for n in kg.neighbors("proto:kinase_biochem_lum", rel="HAS_RULE")]
    assert "rule:agm/substrate_at_km" in rules
    assert "rule:agm/camp_antagonist_agonist_level" not in rules   # a GPCR-only rule
