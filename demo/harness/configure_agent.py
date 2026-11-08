"""Render absolute provider/prompt locations for this checkout only."""
import json
import subprocess
from pathlib import Path
DEMO = Path(__file__).resolve().parents[1]
OC = DEMO / 'harness/opencode'
config = json.loads((OC / 'opencode.json').read_text())
config['provider']['nebius']['npm'] = (DEMO / '.opencode/providers/nebius.mjs').as_uri()
for agent, filename in [('stage', 'agent_prompt.md'), ('planner', 'planner_prompt.md')]:
    config['agent'][agent]['prompt'] = (DEMO / 'harness/stage' / filename).read_text()
(OC / 'private').mkdir(parents=True, exist_ok=True, mode=0o700)
# Derive the tool's actual argument schema from the same validator used to compile.
# Supplying only an unconstrained record leaves the model guessing nested fields.
schema = subprocess.check_output([str(DEMO / '.venv/bin/python'), '-m',
    'demo.harness.planning_pipeline', 'schema'], cwd=DEMO.parent, text=True, timeout=15)
(OC / 'private/submission-schema.json').write_text(schema)
(OC / 'private/runtime.json').write_text(json.dumps(config, indent=2))
