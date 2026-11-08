"""Proposals in, protocols out: the executable end of the chain.

    python -m execution.generate agent/out/run1.jsonl --out execution/out/run1
    python -m execution.generate execution/examples/mic_selectivity.jsonl --simulate

Reads `ExperimentProposal` lines (what `agent/` writes), and for each one that proposes an experiment writes

    <out>/<question_id>/protocol.py              the OT-2 file
    <out>/<question_id>/protocol_run_sheet.md    the half the robot cannot do
    <out>/results.jsonl                          one ExecutionResult per proposal

`--simulate` additionally runs `opentrons_simulate` on each generated file and records whether it passed. It
needs the pinned environment (see execution/requirements-sim.txt); without it every result says so in `error`
rather than the run failing, because a missing simulator is a missing check, not a broken protocol.

A proposal that is `answerable_from_kb` produces no protocol and no result line: there is nothing to run.
A proposal the lab cannot run produces no protocol either - `check_feasible`'s violations go in `error`, so the
reason is recorded instead of a file that would fail on the robot.
"""
import argparse
from pathlib import Path

from wwtn.schema import ExecutionResult, ExperimentProposal, read_jsonl, write_jsonl

from .feasibility import check_feasible
from .lab import Lab
from .plate import plate_design
from .protocol import simulate, write_protocol


def generate(proposals_path: str | Path, out_dir: str | Path, lab: Lab | None = None,
             template: dict | None = None, run_simulator: bool = False) -> list[ExecutionResult]:
    """Generate a protocol per proposal and return the results; also writes `<out_dir>/results.jsonl`."""
    lab = lab or Lab.load()
    out = Path(out_dir)
    results: list[ExecutionResult] = []

    for proposal in read_jsonl(proposals_path, ExperimentProposal):
        if proposal.answerable_from_kb or proposal.experiment is None:
            continue
        experiment = proposal.experiment
        verdict = check_feasible(experiment, lab)
        if not verdict.feasible:
            results.append(ExecutionResult(question_id=proposal.question_id, protocol_path="",
                                           simulated_ok=False, error="; ".join(verdict.violations),
                                           warnings=verdict.warnings))
            continue

        design = plate_design(experiment, lab)
        written = write_protocol(design, out / proposal.question_id, experiment, lab, template)
        ok, error = True, None
        if run_simulator:
            ok, output = simulate(written["protocol"])
            error = None if ok else output.strip()[-2000:]      # the tail is where the simulator says why
        results.append(ExecutionResult(question_id=proposal.question_id, protocol_path=written["protocol"],
                                       run_sheet_path=written["run_sheet"], simulated_ok=ok, error=error,
                                       api_level=written["api_level"],
                                       warnings=list(written["warnings"]) + verdict.warnings))

    write_jsonl(out / "results.jsonl", results)
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("proposals", help="JSON Lines of ExperimentProposal (agent/out/<run>.jsonl)")
    parser.add_argument("--out", default="execution/out/run", help="output directory")
    parser.add_argument("--lab", default=None, help="a lab.yaml other than execution/lab.yaml")
    parser.add_argument("--template", default="kg/protocols/templates/bacterial_mic_broth.json",
                        help="the protocol template the run sheet quotes its off-robot steps from")
    parser.add_argument("--simulate", action="store_true", help="run opentrons_simulate on each protocol")
    args = parser.parse_args(argv)

    template = None
    if args.template and Path(args.template).exists():
        import json
        template = json.loads(Path(args.template).read_text(encoding="utf-8"))

    results = generate(args.proposals, args.out, Lab.load(args.lab), template, args.simulate)
    for result in results:
        state = ("ok" if result.simulated_ok else "FAILED") if args.simulate else "generated"
        print(f"{result.question_id}: {state}  {result.protocol_path or result.error}")
        for warning in result.warnings:
            print(f"    ! {warning}")
    print(f"{len(results)} result(s) -> {Path(args.out) / 'results.jsonl'}")
    return 0 if all(r.simulated_ok for r in results) or not args.simulate else 1


if __name__ == "__main__":
    raise SystemExit(main())
