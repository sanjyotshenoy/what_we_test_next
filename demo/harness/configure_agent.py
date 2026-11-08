"""Render absolute provider/prompt locations for this checkout only."""
import json
from pathlib import Path
DEMO = Path(__file__).resolve().parents[1]
OC = DEMO / 'harness/opencode'
config = json.loads((OC / 'opencode.json').read_text())
config['provider']['nebius']['npm'] = (DEMO / '.opencode/providers/nebius.mjs').as_uri()
for agent, filename in [('stage', 'agent_prompt.md'), ('planner', 'planner_prompt.md')]:
    config['agent'][agent]['prompt'] = (DEMO / 'harness/stage' / filename).read_text()
(OC / 'private').mkdir(parents=True, exist_ok=True, mode=0o700)
(OC / 'private/runtime.json').write_text(json.dumps(config, indent=2))
