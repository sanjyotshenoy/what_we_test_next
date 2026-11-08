"""Persistent per-session tool attempt limits, including failed/cancelled calls."""
import fcntl
import json
import re
from demo.harness.paths import DEMO

RUNS = DEMO / 'harness/planning_runs'
LIMITS = {'planning_context': 3, 'literature_search': 3, 'literature_read': 6,
          'planning_submit': 3, 'planning_simulate': 1, 'biology_lookup': 3}


def consume(tool, session):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', session):
        raise ValueError('Invalid session ID')
    directory = RUNS / session
    directory.mkdir(parents=True, exist_ok=True)
    # One locked file avoids lost counts when the agent calls tools concurrently.
    with (directory / '.tool-budget').open('a+') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.seek(0)
        content = stream.read()
        counts = json.loads(content) if content else {}
        if counts.get(tool, 0) >= LIMITS[tool]:
            raise ValueError(f'{tool} attempt budget exhausted; stop and review this session')
        counts[tool] = counts.get(tool, 0) + 1
        stream.seek(0); stream.truncate()
        json.dump(counts, stream)
        stream.flush()
