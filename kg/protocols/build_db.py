"""Build the protocol graph from archetypes.yaml, templates/*.json, rules.yaml and conditions.yaml.

    python -m kg.protocols.build_db            # writes kg/protocols/graph/{nodes,edges}.csv
    python -m kg.protocols.build_db --check     # build in memory and print a summary, write nothing

Node types: Protocol (one per archetype), Step, Parameter, Reagent, Readout, QuestionType, Rule, Condition,
TargetClass (referenced, defined by the biology graph). Edges: ANSWERS, APPLICABLE_TO, HAS_STEP, NEXT,
HAS_SUBSTEP (Step -> Step, one level of detail under a top-level step), HAS_PARAM, MEASURES, USES, HAS_RULE
(Protocol -> Rule) and APPLIES_TO (Rule -> Protocol, the reverse, so a Rule node can be walked from either
side), REQUIRES and PREFERRED_WHEN (Protocol -> Condition: the routing conditions, each edge carrying the
archetype field and the span it was read from). `kg/query.py`'s templates(target) keeps working: it reads
APPLICABLE_TO, HAS_PARAM, MEASURES and ANSWERS, all still here with the same meanings.

The shallow decision tree is therefore: a question and a target class pick candidate Protocols
(APPLICABLE_TO, ANSWERS); REQUIRES / PREFERRED_WHEN say when each candidate is the right one; HAS_STEP / NEXT
give the stages and HAS_SUBSTEP the detail under a stage, so a grading tree can score the two separately.

TODO(final): 3 of the 8 archetypes have a curated template, and those three are agent-curated, not yet checked by
a person; the other five contribute a Protocol node with no steps or parameters. See kg/protocols/README.md.

A Parameter's props hold the normalized value and unit plus `aid` (the exemplar it was read from) and `observed`
(every value seen across the exemplars, each with its AID and quote), so nothing in the graph is unattributable.
Archetypes without a curated template contribute a Protocol node with its purpose, BAO tags, question type and
rules, but no steps or parameters.

From Python: `from kg.protocols.build_db import build; nodes, edges = build()`.
"""
import argparse
import json
import math
from pathlib import Path

import yaml

from kg.graph_io import write_graph

HERE = Path(__file__).parent
OUT = HERE / "graph"
ARCHETYPES = HERE / "archetypes.yaml"
RULES = HERE / "rules.yaml"
CONDITIONS = HERE / "conditions.yaml"
TEMPLATES = HERE / "templates"
SOURCE_ARCH = "hand-curated from the NCATS Assay Guidance Manual, BAO (OLS4) and ChEMBL protein classes"
SOURCE_RULES = "NCATS Assay Guidance Manual (NCBI Bookshelf NBK53196)"
SOURCE_CONDITIONS = "hand-curated from the archetypes' own purpose text (quote per edge)"

# Controls named in the curated templates -> the Reagent node they share, with the BAO control role where one
# exists (BAO:0000079 negative control, BAO:0000080 positive control; checked in OLS4, 2026-11-07).
CONTROL_BAO = {"negative": "BAO:0000079", "positive": "BAO:0000080"}


def load_archetypes(path: Path = ARCHETYPES) -> dict[str, dict]:
    return {a["id"]: a for a in yaml.safe_load(path.read_text())}


def load_rules(path: Path = RULES) -> list[dict]:
    return yaml.safe_load(path.read_text())


def load_conditions(path: Path = CONDITIONS) -> list[dict]:
    return yaml.safe_load(path.read_text())


def load_templates(folder: Path = TEMPLATES) -> dict[str, dict]:
    found = {}
    for file in sorted(Path(folder).glob("*.json")):
        template = json.loads(file.read_text())
        found[template["id"]] = template
    return found


def _first(observed: list[dict]) -> dict:
    """The default value for a parameter: the first observation (the exemplars are listed most-canonical first)."""
    return observed[0]


def check_rule(rule: dict, experiment: dict) -> bool | None:
    """Evaluate a rule's `check` against an Experiment as a dict (wwtn.schema.Experiment.model_dump() plus any
    context values such as expected_ic50_uM). None = not checkable (no expression, or a value it needs is
    missing). Expressions are evaluated with no builtins and only the fields below in scope."""
    expression = rule.get("check")
    if not expression:
        return None
    scope = {"abs": abs, "log10": math.log10, "min": min, "max": max, "len": len, "any": any, "all": all,
             "round": round, **experiment}
    try:
        return bool(eval(expression, {"__builtins__": {}}, scope))  # noqa: S307 - rules.yaml is ours, not input
    except (KeyError, NameError, TypeError, ValueError, ZeroDivisionError):
        return None


def check_condition(condition: dict, experiment: dict) -> bool | None:
    """A routing condition's `check`, evaluated like a rule's: True / False, or None when the condition is not
    answerable from an Experiment (no expression, or a value it needs is missing) and the lab or the question
    has to answer it instead."""
    return check_rule(condition, experiment)


def build(archetypes: dict | None = None, templates: dict | None = None, rules: list[dict] | None = None,
          conditions: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    archetypes = archetypes if archetypes is not None else load_archetypes()
    templates = templates if templates is not None else load_templates()
    rules = rules if rules is not None else load_rules()
    conditions = conditions if conditions is not None else load_conditions()
    nodes, edges = [], []

    seen = set()

    def node(id, type, name, props=None, source=SOURCE_ARCH):
        if id in seen:   # shared nodes (a QuestionType, a control Reagent) are written once
            return
        seen.add(id)
        nodes.append({"id": id, "type": type, "name": name, "props": props or {}, "source": source})

    def edge(src, rel, dst, props=None, source=SOURCE_ARCH):
        edges.append({"src": src, "rel": rel, "dst": dst, "props": props or {}, "source": source})

    for rule in rules:
        node(rule["id"], "Rule", rule["text"].strip(), {
            "applies_to": rule["applies_to"], "check": rule.get("check"), "severity": rule.get("severity", "should"),
            "machine_checkable": bool(rule.get("check")),
            "agm_chapter": rule["source"]["chapter"], "agm_nbk": rule["source"]["nbk"],
            "url": f"https://www.ncbi.nlm.nih.gov/books/{rule['source']['nbk']}/",
            "quote": rule["source"]["quote"],
        }, source=SOURCE_RULES)

    for condition in conditions:
        node(condition["id"], "Condition", condition["text"].strip(), {
            "check": condition.get("check"), "machine_checkable": bool(condition.get("check")),
            # one entry per edge below: the archetype, the field and the span this condition was read from
            "derived_from": condition["from"],
        }, source=SOURCE_CONDITIONS)

    for id, archetype in archetypes.items():
        template = templates.get(id)
        bao = archetype.get("bao") or {}
        node(id, "Protocol", archetype["name"], {
            "purpose": " ".join(archetype["purpose"].split()),
            "readout_text": archetype.get("readout"),
            **{f"bao_{k}": v["id"] for k, v in bao.items()},
            "agm_chapters": archetype.get("agm", []),
            "kinase": bool(archetype.get("kinase")),
            "negative_control": bool(archetype.get("negative_control")),
            "curation": template["curation"] if template else "archetype only: no curated template yet",
            "has_template": bool(template),
            "pubchem_search": (archetype.get("pubchem") or {}).get("search", []),
            "exemplar_aids": [e["aid"] for e in template["exemplars"] if "aid" in e] if template else [],
            "robot_exemplar": archetype.get("robot_exemplar"),
        })

        question_type = archetype["question_type"]
        node(question_type, "QuestionType", question_type.split(":", 1)[1])
        edge(id, "ANSWERS", question_type)
        for class_id in archetype["applicable_to"]:
            edge(id, "APPLICABLE_TO", class_id)

        # the rest of the routing: REQUIRES = without this the template cannot be run, PREFERRED_WHEN = this is
        # what makes it the better choice. Both read off this archetype's own text, quote on the edge.
        for condition in conditions:
            for origin in condition["from"]:
                if origin["archetype"] != id:
                    continue
                edge(id, origin["relation"], condition["id"],
                     {"archetype_field": origin["field"], "quote": origin["quote"]}, SOURCE_CONDITIONS)

        readout_id = f"readout:{id.split(':', 1)[1]}"
        readout = template["readout"] if template else {"name": archetype["readout"],
                                                        "bao": bao.get("detection", {}).get("id")}
        node(readout_id, "Readout", readout["name"], {"bao": readout.get("bao")})
        edge(id, "MEASURES", readout_id)

        for rule in rules:
            if rule["applies_to"] == "all" or id in rule["applies_to"]:
                edge(id, "HAS_RULE", rule["id"], {"severity": rule.get("severity", "should")}, SOURCE_RULES)
                edge(rule["id"], "APPLIES_TO", id, {}, SOURCE_RULES)

        if not template:
            continue
        aids = ", ".join(str(e["aid"]) for e in template["exemplars"] if "aid" in e)
        source = f"agent-curated from PubChem AIDs {aids}"

        for name, parameter in template["parameters"].items():
            observed = parameter["observed"]
            default = _first(observed)
            param_id = f"{id}/param/{name}"
            node(param_id, "Parameter", name, {
                "value": default["value"], "unit": default.get("unit"),
                "aid": default.get("aid"), "quote": default.get("quote"),
                "observed": observed, "n_exemplars": len(observed),
            }, source)
            edge(id, "HAS_PARAM", param_id, {}, source)

        previous = None
        for i, step in enumerate(template["steps"], start=1):
            step_id = f"{id}/step{i}"
            substeps = step.get("substeps", [])
            node(step_id, "Step", step["text"], {
                "verb": step["verb"], "order": i, "optional": bool(step.get("optional")),
                "params": step.get("params", []), "evidence": step.get("evidence", []),
                "n_substeps": len(substeps),
            }, source)
            edge(id, "HAS_STEP", step_id, {}, source)
            if previous:
                edge(previous, "NEXT", step_id, {}, source)
            previous = step_id
            # One level deeper: the detail a step's own evidence already spells out. A sub-step has a `parent`
            # (a top-level step has none) and its `order` counts within that parent; HAS_STEP and NEXT stay at
            # the top level, so the ordered chain is unchanged.
            for j, substep in enumerate(substeps, start=1):
                substep_id = f"{step_id}/sub{j}"
                node(substep_id, "Step", substep["text"], {
                    "verb": substep["verb"], "order": j, "parent": step_id,
                    "optional": bool(substep.get("optional")),
                    "params": substep.get("params", []), "evidence": substep.get("evidence", []),
                }, source)
                edge(step_id, "HAS_SUBSTEP", substep_id, {"order": j}, source)

        for control in template["controls"]:
            reagent_id = control.get("reagent") or f"reagent:{control['name'][:40]}"
            node(reagent_id, "Reagent", control["name"], {
                "role": control["role"], "bao": CONTROL_BAO.get(control["role"]),
                "evidence": control.get("evidence", []),
            }, source)
            edge(id, "USES", reagent_id, {"role": control["role"]}, source)

    return nodes, edges


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the protocol knowledge graph.")
    parser.add_argument("--check", action="store_true", help="build and summarize without writing the CSVs")
    args = parser.parse_args()
    nodes, edges = build()
    counts = {}
    for n in nodes:
        counts[n["type"]] = counts.get(n["type"], 0) + 1
    rules = load_rules()
    conditions = load_conditions()
    checkable = sum(1 for r in rules if r.get("check"))
    checkable_conditions = sum(1 for c in conditions if c.get("check"))
    rels = {}
    for e in edges:
        rels[e["rel"]] = rels.get(e["rel"], 0) + 1
    print(f"{len(nodes)} nodes ({', '.join(f'{v} {k}' for k, v in sorted(counts.items()))}), {len(edges)} edges "
          f"({', '.join(f'{v} {k}' for k, v in sorted(rels.items()))}); "
          f"{checkable}/{len(rules)} rules and {checkable_conditions}/{len(conditions)} conditions "
          f"machine-checkable")
    if not args.check:
        write_graph(OUT, nodes, edges)
        print(f"wrote {OUT}/nodes.csv and {OUT}/edges.csv")


if __name__ == "__main__":
    main()
