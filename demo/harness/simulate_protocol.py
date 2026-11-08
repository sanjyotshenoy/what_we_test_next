"""Finite OT-2 simulation worker. Run under .venv-ot2, never on hardware."""
import hashlib
import json
from pathlib import Path
import sys
import traceback


def main():
    from opentrons import simulate
    source, destination = map(Path, sys.argv[1:3])
    result = {'status': 'failed', 'protocol_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    try:
        with source.open() as protocol:
            log, _ = simulate.simulate(protocol, file_name=source.name)
        result.update(status='passed', commands=len(log), runlog=log)
    except Exception:
        result['error'] = traceback.format_exc()
    destination.write_text(json.dumps(result, indent=2, default=str))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
