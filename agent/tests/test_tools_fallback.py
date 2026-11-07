"""The sample-KG fallback and the seed graphs: one code path (agent/kg_backend.py) has to serve both."""
import pytest

from agent.tools import DEMO_COMPOUND, DEMO_TARGET, KG_ROOT, TOOL_NAMES, TOOL_SPECS, KnowledgeBase, qtype

REAL_GRAPHS = all((KG_ROOT / g / "graph" / "nodes.csv").exists() for g in ("biology", "protocols"))


@pytest.fixture(scope="module")
def sample_kb():
    """No graphs under this root, so the hand-written sample in agent/data/sample_kg is used."""
    return KnowledgeBase("/nonexistent-kg-root")


def test_the_sample_kg_is_used_when_the_real_graphs_are_missing(sample_kb):
    assert sample_kb.sample is True
    assert "sample_kg" in sample_kb.source


def test_sample_kg_resolves_and_keeps_the_demo_pair_absent(sample_kb):
    r = sample_kb.bio_kg_resolve("imatinib", "KIT")
    assert r["compound_id"] == "CHEMBL941" and r["target_id"] == "P10721"
    assert r["target_classes"] == ["class:tyrosine_kinase"]
    assert sample_kb.lookup("imatinib", "KIT")["found"] is False      # the deliberately held-out pair


def test_sample_kg_routes_question_types_by_its_prop(sample_kb):
    """The sample protocols carry a `question_type` prop instead of ANSWERS edges."""
    potency = sample_kb.protocol_kg_templates("potency", target="KIT")
    assert [t["id"] for t in potency["templates"]] == ["proto:kinase_glo"]
    cells = sample_kb.protocol_kg_templates("cellular_activity", target="KIT")
    assert [t["id"] for t in cells["templates"]] == ["proto:cell_ctg"]
    assert sample_kb.protocol_kg_templates("binding", target="KIT")["templates"] == []


def test_sample_kg_analogs_fall_back_without_smiles(sample_kb):
    """Nothing in the sample KG has a SMILES, so similarity cannot be computed: potency order, and say so."""
    r = sample_kb.bio_kg_analogs("imatinib", "KIT", k=3)
    assert r["ranked_by_similarity"] is False
    assert [row[1] for row in r["rows"]] == ["n/a", "n/a", "n/a"]
    assert r["ic50_nM"] == [20.0, 50.0, 200.0]


def test_a_measured_pair_is_answered_from_the_sample_kg(sample_kb):
    answer = sample_kb.lookup("imatinib", "ABL1")
    assert answer["found"] is True and answer["verdict"] == "answered"
    assert "IC50 250 nM" in answer["result"]


def test_the_tool_registry_matches_the_methods(sample_kb):
    assert TOOL_NAMES == {"bio_kg_resolve", "bio_kg_analogs", "protocol_kg_templates"}
    for name in TOOL_NAMES:
        assert callable(getattr(sample_kb, name))
    assert sample_kb.call("not_a_tool", {})["error"] is True
    assert sample_kb.call("bio_kg_analogs", {"bogus": 1})["error"] is True


def test_every_tool_result_has_the_shape_the_trace_expects(sample_kb):
    for name, args in (("bio_kg_resolve", {"compound": "imatinib", "target": "KIT"}),
                       ("bio_kg_analogs", {"compound": "imatinib", "target": "KIT"}),
                       ("protocol_kg_templates", {"question_type": "potency", "target": "KIT"})):
        r = sample_kb.call(name, args)
        assert isinstance(r.get("summary"), str) and r["summary"]
        assert isinstance(r["columns"], list) and isinstance(r["rows"], list)
        assert all(isinstance(row, list) for row in r["rows"])
        assert sample_kb.result_text(r).startswith(r["summary"])


def test_question_type_normalisation():
    assert qtype("Cellular Activity") == "cellular_potency"
    assert qtype("qtype:potency") == "potency"
    assert qtype("IC50") == "potency"
    assert qtype("affinity") == "binding"
    assert qtype("something-else") == "something_else"      # unknown types pass through, they just match nothing
    assert qtype(None) == ""


def test_the_protocol_tool_spec_keeps_both_arguments():
    spec = next(t for t in TOOL_SPECS if t["function"]["name"] == "protocol_kg_templates")
    props = spec["function"]["parameters"]["properties"]
    assert {"question_type", "target", "target_class"} <= set(props)
    assert spec["function"]["parameters"]["required"] == ["question_type"]


# --- the real seed graphs (skipped when they are not checked out) -----------------------------------------

@pytest.mark.skipif(not REAL_GRAPHS, reason="kg/*/graph not present")
class TestSeedGraphs:
    @pytest.fixture(scope="class")
    @classmethod
    def real_kb(cls):
        return KnowledgeBase()

    def test_graphs_load(self, real_kb):
        assert real_kb.sample is False and real_kb.source == "kg/*/graph"

    def test_the_demo_question_is_answerable_by_experiment(self, real_kb):
        """The demo pair must be in the graph, with no measurement between them."""
        r = real_kb.bio_kg_resolve(DEMO_COMPOUND, DEMO_TARGET)
        assert r["compound_id"] == DEMO_COMPOUND and r["target_id"]
        assert r["compound_structure_only"] is True and r["compound_has_smiles"] is True
        assert real_kb.lookup(DEMO_COMPOUND, DEMO_TARGET)["found"] is False

    def test_the_class_chain_reaches_protein_kinase(self, real_kb):
        r = real_kb.bio_kg_resolve(DEMO_COMPOUND, DEMO_TARGET)
        assert "chembl_class:1100" in r["target_classes"]
        assert r["template_classes"] == ["chembl_class:1100"]

    def test_a_potency_template_is_found_through_the_chain(self, real_kb):
        r = real_kb.protocol_kg_templates("potency", target=DEMO_TARGET)
        assert [t["id"] for t in r["templates"]] == ["proto:kinase_biochem_lum"]
        assert r["via_classes"] == ["chembl_class:1100"]
        assert real_kb.protocol_kg_templates("thermal_shift", target=DEMO_TARGET)["templates"] == []

    def test_analogs_are_ranked_by_similarity(self, real_kb):
        r = real_kb.bio_kg_analogs(DEMO_COMPOUND, DEMO_TARGET, k=5)
        assert r["ranked_by_similarity"] is True
        assert len(r["rows"]) == 5
        assert r["similarity"] == sorted(r["similarity"], reverse=True)
        assert r["similarity"][0] > 0.4                     # the chosen pair has real analog support
        assert r["target_potency_spread_nM"]["n"] > 100

    def test_gene_symbols_resolve(self, real_kb):
        for symbol in ("BTK", "AXL", "MERTK", "MTOR", "AURKA"):
            assert real_kb.find_target(symbol), symbol


def test_the_abstain_verdict_has_two_kinds(sample_kb):
    """Addition 3: the benchmark's abstain metric needs "never heard of it" apart from "nobody measured it"."""
    unknown = sample_kb.lookup("not-a-compound", "KIT")
    assert unknown["verdict"] == "I don’t know" and unknown["kind"] == "unresolved"
    assert unknown["unresolved"] == ["not-a-compound"] and "compound unknown to the KB" in unknown["result"]

    unmeasured = sample_kb.lookup("imatinib", "KIT")
    assert unmeasured["verdict"] == "I don’t know" and unmeasured["kind"] == "no_measurement"
    assert unmeasured["resolved"] == ["CHEMBL941", "P10721"]

    answered = sample_kb.lookup("imatinib", "ABL1")
    assert answered["verdict"] == "answered" and answered["kind"] == "answered"

    both = sample_kb.lookup("nope", "also-nope")
    assert both["kind"] == "unresolved" and "compound and target unknown" in both["result"]


def test_the_lookup_keeps_the_fields_the_trace_documents(sample_kb):
    for args in (("imatinib", "KIT"), ("imatinib", "ABL1"), ("nope", "KIT")):
        lookup = sample_kb.lookup(*args)
        assert {"tool", "args", "result", "verdict", "rows"} <= set(lookup)
