# Private judge demo

Public access stays closed. These addresses are loopback on Brev; use the team's
private connection/port forwarding to view them from a laptop.

- Prepared judge view: `http://127.0.0.1:7200` (`wwtn-viewer.service`).
- Private operator: `http://127.0.0.1:7100` (`wwtn-stage.service`).
- Internal OpenCode: `127.0.0.1:4096`; never publish this API.

## Presenting

Start in the prepared judge view. It opens a completed real-graph software
rehearsal: ciprofloxacin against E. coli and P. aeruginosa. Show the actual ChEMBL
MIC observations and Paperclip passage in the evidence notebook, switch between
the two generated runs, inspect wells, and download a protocol or simulator report.
The proposal rationale visibly labels the assay settings as synthetic test inputs.
The graph entities and retrieved evidence are real; biological applicability has
not been established for unspecified strains.

Play the **Robot recording** panel: it is a fixed 30-second, silent, 25.1× version
of the supplied 12-minute-33-second recording. It loops until paused and supports
seeking/full screen. Playback has no relationship to agent or simulator state.
It is not a live feed or proof that the displayed generated protocol ran physically.
The local copy removes a Drive/network dependency during the presentation.

To demonstrate a fresh run, open the private operator, select **New session**, then
**Load real-graph rehearsal**, then **Run planning agent**. The alternative
**Load software rehearsal** uses two synthetic compounds and two synthetic species.
Both presets supply assay parameters explicitly so the planner can complete a
software test without inventing laboratory settings. Watch the context, evidence,
submission and simulation tools in Agent activity. New designs run only in the
simulator. A rejected submission, truncated response or stopped agent is not a pass.

Judges continue seeing the prepared results while the operator runs new requests.
The viewer does not automatically expose every new session. Keep it on the prepared
results if a live provider or retrieval call fails. Do not describe saved results as
newly generated. The robot video remains available independently.

## Supported scope

The current compiler supports MIC broth microdilution, two-fold dilution, a 96-well
plate, and growth/sterility controls. Multiple compound/species combinations become
separate sequential runs. The simulator checks compatible generated OT-2 Python;
it does not support arbitrary experimental methods or establish biological validity.
Emmy's supplied four-antibiotic single-plate reference and Jimmy's rubric remain
separate references. This demo does not claim to implement that layout or grade it.

## Private operation and recovery

Read-only readiness checks, from the repository root:

```bash
systemctl is-active wwtn-opencode wwtn-stage wwtn-viewer
curl -fsS http://127.0.0.1:7100/api/health
curl -fsS http://127.0.0.1:7200/api/health
curl -fsS http://127.0.0.1:7200/api/recording
ss -ltn '( sport = :4096 or sport = :7100 or sport = :7200 or sport = :80 or sport = :443 )'
```

The three demo listeners must be on `127.0.0.1` only. No Caddy/TLS listener is
installed by this work. The services are enabled and restart on failure. Do not
start the historical tmux launcher alongside them. Do not restart OpenCode or the
operator during a run: use Stop first and verify `agent_status` is `idle`.
The viewer is independent of both and continues serving saved artifacts.

The viewer's explicit session allowlist is ignored
`demo/private/published_sessions.json`. Review artifacts before changing it, then
restart only `wwtn-viewer`. The operator's prepared starting session is set through
`DEMO_DEFAULT_SESSION` in its systemd `presentation.conf` drop-in. It selects saved
artifacts for viewing; a new prompt starts its own new session.

Media is intentionally not committed: original `demo/.downloads/IMG_2874.mov`,
clip/poster/manifest under ignored `demo/harness/stage/static/media/`. To regenerate
on this VM with ffmpeg/ffprobe installed:

```bash
demo/.venv/bin/python -m demo.harness.prepare_video demo/.downloads/IMG_2874.mov
```

The runtime doesn't need ffmpeg; it serves the prepared MP4 with byte-range
support. Copy the ignored media and approved result artifacts separately when
moving hosts; a Git clone alone does not contain them. Never copy private keys
into the repository or the viewer.

<!-- TODO(final): Domain review, strain selection, additional control support,
benchmark grading integration and any future external HTTPS/auth publication
remain separate work. Public access must stay closed until explicitly authorized. -->
