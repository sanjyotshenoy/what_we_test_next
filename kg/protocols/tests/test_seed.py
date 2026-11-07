from kg.protocols.seed import seed_rows

VERBS = {"dispense", "transfer", "serial_dilute", "mix", "incubate", "read"}
SHARED_PARAMS = {"top_concentration", "dilution_factor", "n_points", "replicates", "dmso_percent"}


def graph():
    nodes, edges = seed_rows()
    return {n["id"]: n for n in nodes}, edges


def protocols(nodes):
    return [n for n in nodes.values() if n["type"] == "Protocol"]


def test_three_protocols():
    nodes, _ = graph()
    found = protocols(nodes)
    assert len(found) == 3
    assert all(p["props"]["purpose"] for p in found)


def test_steps_chain():
    nodes, edges = graph()
    for p in protocols(nodes):
        steps = [e["dst"] for e in edges if e["src"] == p["id"] and e["rel"] == "HAS_STEP"]
        nexts = {e["src"]: e["dst"] for e in edges if e["rel"] == "NEXT" and e["src"] in steps}
        first = [s for s in steps if s not in nexts.values()]
        assert len(first) == 1
        chain = [first[0]]
        while chain[-1] in nexts:
            chain.append(nexts[chain[-1]])
        assert sorted(chain) == sorted(steps)
        assert all(nodes[s]["props"]["verb"] in VERBS for s in steps)


def test_applicable_to_kinase():
    nodes, edges = graph()
    for p in protocols(nodes):
        assert {"src": p["id"], "rel": "APPLICABLE_TO", "dst": "chembl_class:1100"} in [
            {k: e[k] for k in ("src", "rel", "dst")} for e in edges]


def test_params():
    nodes, edges = graph()
    for p in protocols(nodes):
        params = [nodes[e["dst"]] for e in edges if e["src"] == p["id"] and e["rel"] == "HAS_PARAM"]
        assert SHARED_PARAMS <= {n["name"] for n in params}
        assert all("value" in n["props"] and "unit" in n["props"] for n in params)
