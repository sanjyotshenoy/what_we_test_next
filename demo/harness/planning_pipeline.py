"""Validate cited experiment batches, compile pair-specific OT-2 runs, simulate.

Uses team contracts/compiler without modifying the team repository. The batch
envelope preserves compound identity absent from ExperimentProposal itself.
"""
from __future__ import annotations

from dataclasses import asdict
import csv
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
import re
import subprocess
import sys
from typing import Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from demo.harness.paths import ROOT, DEMO
TEAM = ROOT
from wwtn.schema import Experiment, ExperimentProposal, PanelMember, PlateLayout, write_jsonl
from execution.lab import Lab
from execution.feasibility import check_feasible
from execution.plate import plate_design, audit
from execution.protocol import to_ot2, run_sheet, unimplemented_steps
from kg.protocols.build_db import check_rule

RUNS = DEMO / 'harness/planning_runs'
TEMPLATE = TEAM / 'kg/protocols/templates/bacterial_mic_broth.json'
LAB = TEAM / 'execution/lab.yaml'
GRAPH = TEAM / 'kg/protocols/graph'
TEMPLATE_ID = 'proto:bacterial_mic_broth'
FIELDS = {'assay_type', 'readout', 'panel', 'top_concentration', 'concentration_unit',
          'dilution_factor', 'n_points', 'replicates', 'controls', 'medium',
          'incubation_C', 'incubation_h', 'atmosphere', 'well_volume_uL', 'layout'}
OPTIONAL_FIELDS = {'system', 'background', 'rationale'}


class StrictPanel(PanelMember):
    model_config = ConfigDict(extra='forbid')


class StrictLayout(PlateLayout):
    model_config = ConfigDict(extra='forbid')
    control_columns: list[str] = Field(description='Ordered control LABELS, not column numbers: ["growth control", "sterility control"]. The compiler places them in columns 11 and 12.')


class StrictExperiment(Experiment):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    top_concentration: float = Field(gt=0)
    concentration_unit: Literal['uM', 'nM', 'ug/mL', 'mg/L']
    panel: list[StrictPanel] = Field(min_length=1, max_length=8)
    layout: StrictLayout


class StrictProposal(ExperimentProposal):
    model_config = ConfigDict(extra='forbid')
    experiment: StrictExperiment
    answerable_from_kb: Literal[False]
    citations: list[str] = Field(description='Include proto:bacterial_mic_broth and exact retrieved evidence_id strings. Copy IDs verbatim; never rebuild them from sha256 or use search result IDs.')


class EvidenceLink(BaseModel):
    model_config = ConfigDict(extra='forbid')
    field: str
    kind: Literal['observed', 'derived', 'default', 'input']
    citations: list[str] = Field(default_factory=list, max_length=20)
    explanation: str = Field(min_length=1, max_length=2000)


class CompoundProposal(BaseModel):
    model_config = ConfigDict(extra='forbid')
    compound: str = Field(min_length=1, max_length=150)
    proposal: StrictProposal
    evidence_links: list[EvidenceLink] = Field(min_length=1, max_length=50,
        description='Must cover each experiment field: ' + ', '.join(sorted(FIELDS)))


class Batch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    template_id: Literal['proto:bacterial_mic_broth']
    compounds: list[CompoundProposal] = Field(min_length=1, max_length=8)
    open_questions: list[str] = Field(default_factory=list)


def session_dir(session):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', session):
        raise ValueError('Invalid session ID')
    return RUNS / session


def source_revision():
    try:
        return subprocess.check_output(['git', '-C', str(TEAM), 'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return 'unversioned source archive; see input/schema hashes'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(payload)
    os.replace(temporary, path)


def rule_report(experiment):
    with (GRAPH / 'nodes.csv').open() as stream:
        nodes = {row['id']: row for row in csv.DictReader(stream)}
    with (GRAPH / 'edges.csv').open() as stream:
        edges = list(csv.DictReader(stream))
    report = []
    for edge in edges:
        if edge['src'] == TEMPLATE_ID and edge['rel'] == 'HAS_RULE':
            node = nodes[edge['dst']]
            props = json.loads(node['props'])
            result = check_rule(props, experiment.model_dump())
            report.append({'rule': node['id'], 'source': node['source'],
                           'severity': json.loads(edge['props']).get('severity', 'should'),
                           'status': 'needs_review' if result is None else ('passed' if result else 'failed')})
    return report


def evidence_for(session):
    found = {}
    for path in session_dir(session).glob('*.json'):
        record = json.loads(path.read_text())
        if record.get('mode') != 'demo':
            continue
        result = record.get('result', {})
        identifier = result.get('evidence_id')
        if record.get('tool') == 'literature_read' and identifier:
            digest = hashlib.sha256(result['passage'].encode()).hexdigest()
            expected = f"paper:{record['args']['paper_id']}:L{result['start']}-L{result['end']}:{digest[:12]}"
            if digest == result.get('sha256') and identifier == expected:
                found[identifier] = record
        elif record.get('tool') == 'biology_lookup' and identifier:
            from demo.harness.biology import graph_hashes
            payload = {k: v for k, v in result.items() if k not in ('evidence_id', 'sha256')}
            digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            if identifier == 'biology:' + digest and result.get('sha256') == digest and result.get('source_hashes') == graph_hashes():
                found[identifier] = record
        elif record.get('tool') == 'planning_context' and identifier == TEMPLATE_ID:
            hashes = result.get('source_hashes', {})
            if all(hashes.get(str(p.relative_to(ROOT))) == sha(p) for p in (TEMPLATE, LAB)):
                found[identifier] = record
    return found


def validate(batch, evidence):
    errors = []
    if batch.open_questions:
        errors.append('Resolve open_questions before compilation: ' + '; '.join(batch.open_questions))
    if TEMPLATE_ID not in evidence:
        errors.append('Call planning_context in this session; context must match current files')
    names, questions = set(), set()
    count = 0
    for item in batch.compounds:
        prefix = item.compound
        proposal, ex = item.proposal, item.proposal.experiment
        def reject(message):
            errors.append(f'{prefix}: {message}')
        if item.compound.casefold() in names or proposal.question_id in questions:
            reject('Compound identities and question IDs must be unique')
        names.add(item.compound.casefold()); questions.add(proposal.question_id)
        cited = set(proposal.citations)
        if TEMPLATE_ID not in cited:
            reject('Cite the selected protocol template')
        if cited - evidence.keys():
            reject('Unknown/unread citation IDs: ' + ', '.join(sorted(cited - evidence.keys()))
                   + '. Copy exact retrieved evidence_id strings from: ' + ', '.join(sorted(evidence)))
        linked = {link.field for link in item.evidence_links}
        unknown = linked - FIELDS - OPTIONAL_FIELDS
        if FIELDS - linked or unknown:
            reject(f'Evidence links must cover experiment fields; missing={sorted(FIELDS-linked)}, unknown={sorted(unknown)}')
        for link in item.evidence_links:
            if set(link.citations) - cited:
                reject(f'{link.field}: evidence links must be in proposal.citations')
            if link.kind != 'input' and not link.citations:
                reject(f'{link.field}: {link.kind} needs retrieved citations')
            if link.kind == 'observed' and not any(c.startswith('paper:') or (c.startswith('biology:') and evidence.get(c, {}).get('result', {}).get('measurements')) for c in link.citations):
                reject(f'{link.field}: observed values need a read paper passage or retrieved KG measurement')
        if not re.search(r'\bMIC\b|broth microdilution', ex.assay_type, re.I):
            reject('Only MIC broth microdilution is implemented by this compiler')
        if not re.search(r'absorbance|turbidity|\bOD\s*\d*\b', ex.readout, re.I):
            reject('This MIC compiler requires an absorbance/turbidity readout')
        if ex.dilution_factor != 2:
            reject('Current transfer compiler supports only 2-fold dilution')
        for field in ('top_concentration', 'well_volume_uL', 'incubation_C', 'incubation_h'):
            value = getattr(ex, field)
            if value is None or not math.isfinite(value) or value <= 0:
                reject(f'{field} must be positive and finite')
        if not 1 <= ex.n_points <= 10 or not 1 <= ex.replicates <= 8:
            reject('Supported per-pair plate: 1–10 concentrations and 1–8 requested replicates')
        if ex.layout.plate_format != 96 or ex.layout.series_axis != 'columns' or ex.layout.replicates_axis != 'rows':
            reject('Only 96-well column series / row replicates are implemented')
        expected_controls = ['growth control', 'sterility control']
        if ex.controls != expected_controls:
            reject('experiment.controls must equal ["growth control", "sterility control"]. Extra controls need an explicit implementation; do not omit a required control.')
        if ex.layout.control_columns != expected_controls:
            reject('experiment.layout.control_columns must contain the LABELS ["growth control", "sterility control"], not numbers such as ["11", "12"]. Keep valid experiment.controls unchanged.')
        if not ex.medium or not ex.atmosphere:
            reject('Specify medium and incubation atmosphere')
        for rule in rule_report(ex):
            if rule['severity'] == 'must' and rule['status'] == 'failed':
                reject(f"Required protocol rule failed: {rule['rule']}")
        if ex.atmosphere and ex.atmosphere not in Lab.load(LAB).atmospheres():
            reject('Requested incubation atmosphere is not available')
        species_names = [s.name.casefold() for s in ex.panel]
        if len(set(species_names)) != len(species_names):
            reject('Duplicate species in panel')
        for species in ex.panel:
            tolerance = species.oxygen_tolerance
            # The upstream renderer embeds labels inside a Python docstring.
            # Keep source-derived labels from escaping that string during simulation.
            if (len(species.name) > 200 or any(ord(c) < 32 for c in species.name)
                    or '\\' in species.name or '"""' in species.name or "'''" in species.name):
                reject('Species labels must be short plain text without control characters, backslashes or triple quotes')
            if not species.name.strip() or not species.reason.strip() or tolerance == 'unknown':
                reject('Each species needs a name, reason and explicit oxygen tolerance')
            if tolerance == 'aerobe' and ex.atmosphere != 'aerobic':
                reject(f'{species.name}: requested atmosphere conflicts with aerobe tolerance')
            if 'anaerobe' in tolerance and ex.atmosphere != 'anaerobic':
                reject(f'{species.name}: requested atmosphere conflicts with anaerobe tolerance')
        count += len(ex.panel)
    if count > 24:
        errors.append('At most 24 compound–species runs per batch')
    return errors


def submit(batch, session):
    try:
        parsed = Batch.model_validate(batch)
    except ValidationError as exc:
        return {'status': 'rejected', 'errors': exc.errors(include_url=False, include_input=False)}
    evidence = evidence_for(session)
    errors = validate(parsed, evidence)
    if errors:
        return {'status': 'rejected', 'errors': errors}
    lab = Lab.load(LAB)
    template = json.loads(TEMPLATE.read_text())
    prepared = []
    for item in parsed.compounds:
        ex = item.proposal.experiment
        for member in ex.panel:
            # A physical 8-channel dispense fills all rows. Record surplus rows
            # explicitly; do not relabel them as requested independent replicates.
            physical = ex.model_copy(deep=True, update={'panel': [member], 'system': member.name, 'replicates': 8})
            verdict = check_feasible(physical, lab)
            design = plate_design(physical, lab)
            problems = verdict.violations + audit(design)
            protocol = to_ot2(design, physical, lab)
            problems += unimplemented_steps(template, protocol.ops)
            # API ceiling warning is informational; any compiler resource warning
            # is blocking rather than silently producing a partial protocol.
            problems += [w for w in protocol.warnings if not w.startswith('lab.yaml declares apiLevel')]
            if problems:
                errors.extend(f'{item.compound} / {member.name}: {p}' for p in problems)
            prepared.append((item, member, physical, verdict, design, protocol))
    if errors:
        return {'status': 'rejected', 'errors': errors}
    batch_id = uuid.uuid4().hex[:16]
    directory = session_dir(session) / 'batches' / batch_id
    directory.mkdir(parents=True)
    save(directory / 'batch.json', parsed.model_dump())
    write_jsonl(directory / 'proposals.jsonl', [x.proposal for x in parsed.compounds])
    save(directory / 'evidence.json', {c: evidence[c] for x in parsed.compounds for c in x.proposal.citations})
    save(directory / 'rules.json', {x.compound: rule_report(x.proposal.experiment) for x in parsed.compounds})
    entries = []
    for index, (item, member, physical, verdict, design, protocol) in enumerate(prepared, 1):
        run_id = f'run-{index:03}'
        sub = directory / run_id
        sub.mkdir()
        identity = {'compound': item.compound, 'species': member.model_dump(),
                    'question_id': item.proposal.question_id}
        mapping = {'A1': {'liquid': 'medium', 'identity': physical.medium},
                   'A2': {'liquid': 'compound', 'identity': item.compound},
                   'A3': {'liquid': 'inoculum', 'identity': member.name}}
        (sub / 'protocol.py').write_text('# Run identity: ' + json.dumps(identity) + '\n' + protocol.code)
        requested = item.proposal.experiment.replicates
        allocation = {'requested_rows': 'ABCDEFGH'[:requested], 'surplus_rows': 'ABCDEFGH'[requested:],
                      'note': 'Surplus technical wells are physically filled; not counted as requested replicates.'}
        plate_data = asdict(design)
        # Team internals retain legacy *_uM names even for mass units. Export
        # unit-neutral values so a future UI cannot accidentally label µg/mL as µM.
        plate_data['top_final'] = plate_data.pop('top_final_uM')
        for well in plate_data['wells']:
            well['prepared_concentration'] = well.pop('prepared_uM')
            well['final_concentration'] = well.pop('final_uM')
        save(sub / 'plate.json', {'identity': identity, 'unit': design.unit, 'allocation': allocation,
                                  'design': plate_data, 'audit_errors': []})
        save(sub / 'sources.json', mapping)
        sheet = f'# {run_id}: {item.compound} / {member.name}\n\n'
        sheet += 'Separate physical run. Replace/load the labeled source liquids and consumables before this run.\n\n'
        sheet += f'Requested replicate rows: {allocation["requested_rows"]}; surplus technical rows: {allocation["surplus_rows"] or "none"}.\n\n'
        sheet += 'Source identities:\n' + '\n'.join(f'- {k}: {v["identity"]}' for k, v in mapping.items()) + '\n\n'
        sheet += run_sheet(design, physical, lab, template)
        sheet += '\n## Proposal conditions (authoritative for this design)\n\n'
        sheet += f'Medium: {physical.medium}; incubation: {physical.incubation_C} C / {physical.incubation_h} h / {physical.atmosphere}; readout: {physical.readout}.\n'
        sheet += 'Template descriptions are precedents, not additional executed operations. The template reference-antibiotic control is not implemented by this two-control compiler.\n'
        (sub / 'run_sheet.md').write_text(sheet)
        entries.append({'run_id': run_id, **identity, 'allocation': allocation,
                        'protocol': f'{run_id}/protocol.py', 'protocol_sha256': sha(sub / 'protocol.py'),
                        'plate': f'{run_id}/plate.json', 'sources': f'{run_id}/sources.json',
                        'run_sheet': f'{run_id}/run_sheet.md', 'tip_columns': protocol.tip_columns,
                        'tip_racks_loaded': protocol.tipracks,
                        'reservoir_mL': protocol.reservoir_mL,
                        'warnings': protocol.warnings + verdict.warnings,
                        'simulation': {'status': 'not_run'}})
    manifest = {'artifact_version': 1, 'schema_sha256': sha(TEAM / 'wwtn/schema.py'), 'batch_id': batch_id, 'status': 'compiled', 'runs': entries,
                'team_commit': source_revision(),
                'input_hashes': {'batch': sha(directory / 'batch.json'), 'lab': sha(LAB), 'template': sha(TEMPLATE),
                                'protocol_nodes': sha(GRAPH / 'nodes.csv'), 'protocol_edges': sha(GRAPH / 'edges.csv')},
                'execution': 'separate sequential run per compound–species pair; reload sources and consumables between runs',
                'review': ['Citation identity/field coverage checked; scientific entailment and user-input claims are not automatically verified.',
                           'See rules.json: uncheckable rules require review; they are not counted as passed.',
                           'Lab assumptions remain warnings. No physical robot run or measurement performed.',
                           'Reference-antibiotic control from the source template is not included; biological review remains required.'],
                'resources': {'plates_total': len(entries), 'tip_columns_total': sum(r['tip_columns'] for r in entries),
                              'fresh_tip_rack_loads': sum(r['tip_racks_loaded'] for r in entries),
                              'listed_tip_racks': sum(int(r.get('count', 0)) for r in lab.labware('tiprack')),
                              'note': 'Resource feasibility is checked per run. Aggregate supplies must be available; tips are consumed, not reused.'}}
    save(directory / 'manifest.json', manifest)
    return {'status': 'compiled', 'batch_id': batch_id, 'run_count': len(entries),
            'manifest': str(directory / 'manifest.json'), 'simulation': 'not_run',
            'execution': manifest['execution'], 'review': manifest['review']}


def simulate_batch(batch_id, session):
    if not re.fullmatch(r'[a-f0-9]{16}', batch_id):
        raise ValueError('Invalid batch ID')
    directory = session_dir(session) / 'batches' / batch_id
    manifest = json.loads((directory / 'manifest.json').read_text())
    for entry in manifest['runs']:
        path = directory / entry['protocol']
        if sha(path) != entry['protocol_sha256']:
            raise ValueError('Protocol changed after compilation; submit a new batch')
        if entry['simulation']['status'] == 'passed':
            continue
        report = path.parent / 'simulation.json'
        try:
            completed = subprocess.run([str(DEMO / '.venv-ot2/bin/python'), '-m', 'demo.harness.simulate_protocol',
                                        str(path), str(report)], cwd=ROOT, capture_output=True, text=True, timeout=30)
            (path.parent / 'simulator.log').write_text(completed.stdout + completed.stderr)
            result = json.loads(report.read_text()) if report.exists() else {}
            ok = completed.returncode == 0 and result.get('status') == 'passed' and result.get('protocol_sha256') == entry['protocol_sha256']
            entry['simulation'] = {'status': 'passed' if ok else 'failed', 'report': str(report.relative_to(directory)),
                                   'commands': result.get('commands'), 'error': None if ok else 'See simulator.log'}
        except subprocess.TimeoutExpired as exc:
            def text(value):
                return value.decode(errors='replace') if isinstance(value, bytes) else (value or '')
            (path.parent / 'simulator.log').write_text(text(exc.stdout) + text(exc.stderr))
            entry['simulation'] = {'status': 'timeout', 'error': 'Simulator exceeded 30s; investigate environment before retrying'}
        except OSError as exc:
            entry['simulation'] = {'status': 'failed', 'error': type(exc).__name__}
        manifest['status'] = 'simulation_incomplete'
        save(directory / 'manifest.json', manifest)
        if entry['simulation']['status'] != 'passed':
            break  # no blind retries or repeated timeouts for every pair
    if all(r['simulation']['status'] == 'passed' for r in manifest['runs']):
        manifest['status'] = 'simulated'
    save(directory / 'manifest.json', manifest)
    return {'batch_id': batch_id, 'status': manifest['status'],
            'runs': [{'run_id': r['run_id'], **r['simulation']} for r in manifest['runs']],
            'note': 'Simulator success checks software execution, not biological validity or physical execution.'}


if __name__ == '__main__':
    try:
        if sys.argv[1] == 'schema':
            print(json.dumps(Batch.model_json_schema()))
            sys.exit(0)
        tool, args, session = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]
        from demo.harness.budget import consume
        consume(tool, session)
        if tool == 'planning_submit':
            out = submit(args['batch'], session)
        elif tool == 'planning_simulate':
            out = simulate_batch(args['batch_id'], session)
        else:
            raise ValueError('Unknown pipeline tool')
        print(json.dumps(out, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({'status': 'error', 'error': type(exc).__name__, 'message': str(exc)}))
        sys.exit(1)
