"""Read-only, session-scoped stage view of real planner artifacts."""
import hashlib
import json
from pathlib import Path
import re
import os

from demo.harness.paths import ROOT, DEMO
RUNS = DEMO / ('replays' if os.environ.get('DEMO_REPLAY') == '1' else 'harness/planning_runs')
TOKEN = re.compile(r'[A-Za-z0-9_-]{1,100}')
BATCH_FILES = {'batch.json', 'manifest.json', 'proposals.jsonl', 'evidence.json', 'rules.json'}
RUN_FILES = {'protocol.py', 'plate.json', 'sources.json', 'run_sheet.md', 'simulation.json', 'simulator.log'}


def session_path(session):
    if not TOKEN.fullmatch(session):
        raise ValueError('Invalid session')
    path = (RUNS / session).resolve()
    if path.parent != RUNS.resolve():
        raise ValueError('Invalid session path')
    return path


def read_json(path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def artifact_path(session, batch, filename):
    base = session_path(session)
    if not re.fullmatch(r'[a-f0-9]{16}', batch):
        raise ValueError('Invalid batch')
    bits = filename.split('/')
    allowed = filename in BATCH_FILES or (len(bits) == 2 and re.fullmatch(r'run-\d{3}', bits[0]) and bits[1] in RUN_FILES)
    path = (base / 'batches' / batch / filename).resolve()
    if not allowed or not path.is_relative_to(base) or not path.is_file():
        raise ValueError('Unknown artifact')
    return path


def snapshot(session):
    base = session_path(session)
    records = [read_json(p) for p in sorted(base.glob('*.json')) if p.is_file() and not p.is_symlink()]
    evidence = [r for r in records if isinstance(r, dict) and r.get('tool') in
                ('planning_context', 'literature_search', 'literature_read', 'biology_lookup')]
    evidence.sort(key=lambda r: r.get('retrieved_at', ''))
    batches = []
    for path in sorted(base.glob('batches/*/manifest.json'), key=lambda p: p.stat().st_mtime):
        if not re.fullmatch(r'[a-f0-9]{16}', path.parent.name):
            continue
        if path.resolve() != path or not path.is_relative_to(base):
            continue
        manifest = read_json(path)
        if not isinstance(manifest, dict) or not isinstance(manifest.get("runs"), list):
            continue  # a writer has not finished yet; next poll will see it
        def batch_read(name, default=None):
            try:
                return read_json(artifact_path(session, path.parent.name, name), default)
            except ValueError:
                return default
        payload = {'manifest': manifest, 'batch': batch_read('batch.json'),
                   'rules': batch_read('rules.json', {}), 'runs': []}
        for run in manifest.get('runs', []):
            if not isinstance(run, dict):
                continue
            rid = run.get('run_id', '')
            if not re.fullmatch(r'run-\d{3}', rid):
                continue
            def read(name):
                try:
                    return read_json(artifact_path(session, path.parent.name, f'{rid}/{name}'))
                except ValueError:
                    return None
            report = read('simulation.json')
            # Never give a stale success badge to edited/missing protocol bytes.
            valid = False
            try:
                protocol = artifact_path(session, path.parent.name, f'{rid}/protocol.py')
                digest = hashlib.sha256(protocol.read_bytes()).hexdigest()
                valid = (digest == run.get('protocol_sha256') and isinstance(report, dict)
                         and report.get('protocol_sha256') == digest and report.get('status') == 'passed')
            except ValueError:
                pass
            if run.get('simulation', {}).get('status') == 'passed' and not valid:
                run['simulation'] = {'status': 'stale', 'error': 'Protocol/report hash mismatch or missing artifact'}
                manifest['status'] = 'simulation_incomplete'
            payload['runs'].append({'run_id': rid, 'plate': read('plate.json'),
                                    'sources': read('sources.json'), 'simulation': report if valid else None})
        batches.append(payload)
    return {'session': session, 'evidence': evidence, 'batches': batches}


def sessions():
    result = []
    for base in RUNS.iterdir() if RUNS.exists() else []:
        if not base.is_dir() or base.is_symlink() or not TOKEN.fullmatch(base.name):
            continue
        paths = [p for p in base.glob('batches/*/manifest.json') if p.resolve() == p and re.fullmatch(r'[a-f0-9]{16}', p.parent.name)]
        if not paths:
            continue
        latest = max(paths, key=lambda p: p.stat().st_mtime)
        manifest = read_json(latest, {})
        if not isinstance(manifest, dict) or not isinstance(manifest.get('runs'), list):
            continue
        result.append({'session': base.name, 'updated': latest.stat().st_mtime,
                       'run_count': len(manifest.get('runs', [])),
                       'status': manifest.get('status', 'unknown')})
    return sorted(result, key=lambda r: r['updated'], reverse=True)[:50]
