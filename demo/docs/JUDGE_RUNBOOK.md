# Presenting the demo

Start at https://demo-o10eetwuq.gobrev.dev/sequential . Choose GLM, Kimi, Qwen or
DeepSeek, then one of the two scientific questions. All eight combinations have
verified precomputed trajectories. The workflow progresses automatically with
processing shimmer, follows new content by scrolling, and stays in light mode.
Long prose has Show more/less; click plate wells for concentration/volume details.
Selecting another question/model cancels the previous progression.

Question 1 designs ciprofloxacin MIC experiments across E. coli and P. aeruginosa.
Question 2 compares ciprofloxacin and tetracycline hydrochloride in E. coli. Both
use real graph identities and retrieved literature; assay settings are supplied
synthetic inputs. These are experiment plans, not new measured MICs or proof of a
biological winner. Known graph measurements are background, not missing-link claims.
The separate haspin example and synthetic compound card were removed.

The root https://demo-o10eetwuq.gobrev.dev/ is the full read-only artifact viewer.
Its default remains the earlier real-identity judge session. Use it for source
inspection, protocols, simulator downloads and the separate 30-second robot video.
The video is fixed, not live, and does not prove physical execution of the displayed
protocol. The sequential view does not play that video.

For a fresh run, trusted members use https://operator-o10eetwuq.gobrev.dev/ and
sign in with their allowlisted Brev account and follow **Live planning** (`/planner`).
The operator root uses the legacy panel layout to inspect the same eight saved
examples without starting inference. Live planning is one shared operator session:
coordinate before changing models, starting or stopping a run. The default is GLM-5.3.
New runs are private until reviewed/published; judges keep seeing approved results.
The older operator rehearsal presets remain software fixtures; they are distinct
from the new prompts in demo/examples/. No physical robot is controlled by this app.

If inference fails, keep using precomputed examples; never label a failed run as
successful. Supported compilation remains MIC broth microdilution with separate
compound/species protocols, growth and sterility controls. Four-antibiotic
single-plate references and step-3 rubric integration are not implemented here.

For recovery, ports, access, Codex Remote and ignored state, read
[REMOTE_HANDOFF.md](../memory/REMOTE_HANDOFF.md). For evidence and failed-attempt
history, read [PRECOMPUTED_EXAMPLES.md](PRECOMPUTED_EXAMPLES.md). No paid inference
is needed just to present or test the sequential view.

In the operator dashboard, **Entire KG** shows the complete bacterial compound–
organism network with measurement links grouped for readability; **Focus run**
shows the saved retrieved subgraph. Hover or tap nodes/edges for formatted details.
The molecule panel shows cached ChEMBL 2D structures and molfile downloads.
**Generated protocol** shows the selected protocol's saved simulator commands on
a 2D deck schematic. Play, step or scrub to highlight slots and plate wells. The
playback timing is illustrative; it is not physical execution. **Robot recording**
is the separate fixed video.

Drag the dividers between dashboard panes to resize them. **Focus** expands any
pane; **Restore** or Escape returns to the dashboard. Sizes are remembered in that
browser; **Reset layout** restores the default proportions. Divider arrow keys work
for keyboard resizing. Click a compound node to show its structure and exact graph
SMILES in the molecule pane; **Run compounds** returns to the saved-run molecules.
The drawing is generated locally and does not change the selected experiment.
