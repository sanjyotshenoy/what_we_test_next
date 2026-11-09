# Set up Project Ouroboros on a new device

This guide describes the repository as of 2026-11-09. Run commands from the
**repository root**, not from `demo/`. Read this before following old deployment
logs. For an existing Brev machine, use [the remote handoff](memory/REMOTE_HANDOFF.md)
instead of reinstalling or starting duplicate services.

## 1. Choose what you are setting up

| Goal | What you need | Entry point |
| --- | --- | --- |
| Historical replay from Git alone | Python dependencies and tracked replay | Private stage `/planner` in replay mode |
| Current dashboard and sequential walkthrough | Runtime plus the reviewed saved-result bundle below | Public viewer `/` and `/sequential` |
| Visitor-key live planning | Current dashboard, simulator, Paperclip login and each visitor's Nebius key | Public viewer `/planner` |
| Private operator / generating new saved examples | Full installer, your own Paperclip and Nebius credentials, OpenCode | Private stage `/planner` |

The public viewer and private stage are different servers. The public viewer runs
visitor-owned workers directly; it does not require a running OpenCode service.
The private stage operates a shared OpenCode session and must not be exposed
anonymously. The original `demo/index.html` and slide symlink are separate legacy
entry points; opening that file is not starting the current dashboard.

No local LLM weights or GPU inference are required. The simulator is software-only;
playing a protocol or the recorded robot video does not operate a physical robot.

## 2. Get the correct revision and prerequisites

Use a Linux ARM64 (`aarch64`/`arm64`) host for the full installation. The installer
explicitly rejects other platforms because its OpenCode binary is pinned for
Linux ARM64. An x86 Linux machine, Intel/Apple Mac or Windows device is not a
verified full-install target. Use the hosted dashboard in a browser, or have a
maintainer add and verify the appropriate platform manifest; do not bypass the
architecture or checksum checks. The Python-only replay path below does not need
that binary, but other operating systems remain unverified.

You need Git, Python 3.12, `uv` on PATH, internet access to the pinned downloads,
and enough writable disk for three environments and the saved artifacts.
Systemd and sudo are only needed for optional persistent Linux services. Browser
tests also need Chromium's OS dependencies. Use a checkout path without spaces or
shell-special characters; the service installers reject those paths.

```bash
git clone https://github.com/sanjyotshenoy/what_we_test_next.git
cd what_we_test_next
# Fetch/check out the maintainer's published demo revision before installing.
git fetch origin
git switch --track origin/demo/judge-rehearsal
git rev-parse HEAD
uname -sm
python3 --version
uv --version
```

If that branch is already checked out, use `git switch demo/judge-rehearsal`.
If the demo changes have been merged, use the maintainer-confirmed main commit
instead. A local commit on Brev is not available to a fresh clone until pushed;
confirm the release SHA rather than assuming remote main contains the latest UI.
Do not overwrite a dirty checkout or copy an old `.venv` from another device.

On an Ubuntu host missing prerequisites, one bootstrap route is:

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv pipx ca-certificates curl
pipx install uv
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.12
```

Run the Git clone steps after installing Git if necessary. `uv` can provide
Python 3.12 for the three environments even if the OS Python is older. If
`python3 --version` is older than 3.12, run the installer with
`uv run --no-project --python 3.12 python demo/install.py --dev` instead of
`python3 demo/install.py --dev`. Once installed, use `demo/.venv/bin/python`
for the Python snippets below so archive extraction uses Python 3.12 too.

## 3. Install dependencies

### Full supported installation

```bash
python3 demo/install.py --dev
demo/.venv/bin/python -m playwright install --with-deps chromium
```

The installer creates these independent environments:

| Location | Purpose |
| --- | --- |
| `demo/.venv` | Web apps, schema/compiler adapters, LLM client, tests with `--dev` |
| `demo/.venv-ot2` | Pinned Opentrons simulator, separate dependency versions |
| `demo/.venv-paperclip` | Pinned GXL Paperclip and retrieval dependencies |

It synchronizes the committed lockfiles, verifies the Paperclip wheel and
OpenCode archive checksums, and bootstraps the private agent/tool configuration.
It does not start services, transfer results, authenticate accounts, or run paid
inference. Without `--dev`, browser/development dependencies are not installed.
A changed upstream download must be reviewed; do not replace a checksum just to
make installation pass. Do not upgrade the OT-2 environment to Opentrons 9/10.

### Python-only historical replay

For a replay without OpenCode, Paperclip installation or new simulations:

```bash
uv venv --python 3.12 demo/.venv
uv pip sync --python demo/.venv/bin/python demo/requirements-dev.lock
```

This is a reduced setup, not a substitute for the full live-planning install.
Tracked KG CSVs are already in `kg/biology/graph_bacteria/`; no ChEMBL download is
needed to show the current full-KG pane. Check these files exist:

```bash
test -s kg/biology/graph_bacteria/nodes.csv
test -s kg/biology/graph_bacteria/edges.csv
```

## 4. Verify a source-only replay first

In a terminal at the repo root:

```bash
DEMO_REPLAY=1 STAGE_LOOPBACK_ONLY=1 STAGE_PORT=7102 \
  demo/.venv/bin/python -m demo.harness.stage.server
```

Open **http://127.0.0.1:7102/planner** and select the saved session in View. This
uses the four simulated protocols and evidence committed under `demo/replays/`.
Its provenance is in `demo/replays/provenance.json`: historical real retrieval and
simulation with synthetic assay inputs, not newly measured biology.
The modern root dashboard expects the newer sequential catalog, so use `/planner`
for this historical fallback. Replay mode rejects writes and needs no credentials.
Stop with Ctrl-C when finished.

Do not carry `DEMO_REPLAY=1` into the public/live service. It changes where saved
artifacts are read; it is not a public-viewer feature flag for disabling live runs.

## 5. Restore the current saved dashboard assets

### What Git does and does not contain

| Item | In Git? | Action on the new host |
| --- | --- | --- |
| UI, local JS vendors, fonts, two query presets, model/session catalog | Yes | Use the matching source revision |
| Biology/protocol KG and original historical replay | Yes | Keep checkout-relative paths |
| Eight current sequential session directories | No | Transfer reviewed artifacts or regenerate them |
| `demo/private/published_sessions.json` | No | Create a reviewed allowlist locally |
| Physical robot MP4/poster/recording metadata | No | Optional approved transfer |
| Credentials, OpenCode state/database, private run transcripts | No | Authenticate anew; do not transfer with the demo bundle |

`demo/sequential-models.json` maps eight session IDs to four model IDs. It contains
no protocol artifacts. A model dropdown can exist while the referenced runs are
missing. Installing dependencies alone cannot reproduce the full presentation.

### Export reviewed results on the existing host

Have a maintainer perform this on the source host. This creates an archive under
`/tmp`, containing only the eight catalog sessions already approved for public
viewing, their allowlisted artifacts and optional approved recording files. It
omits simulator diagnostic logs, credentials and the OpenCode database. Review the
selected evidence/publication rights before sharing; do not archive all of `demo/`.

```bash
demo/.venv/bin/python - <<'PY'
import json
import re
import tarfile
from pathlib import Path
from demo.harness.stage import planning_view

root = Path.cwd()
sessions = json.loads(Path('demo/sequential-models.json').read_text())['sessions']
published = json.loads(Path('demo/private/published_sessions.json').read_text())
assert set(sessions) <= set(published), 'Catalog contains unpublished sessions'
assert planning_view.RUNS == root / 'demo/harness/planning_runs', 'Unset DEMO_REPLAY'
files = set()
for session in sessions:
    data = planning_view.snapshot(session)
    assert data['batches'], f'Missing artifacts: {session}'
    base = planning_view.session_path(session)
    for path in base.glob('*.json'):
        if re.fullmatch(r'[0-9a-f]{64}\.json', path.name) and not path.is_symlink():
            files.add(path)
    for batch in data['batches']:
        manifest = batch['manifest']
        assert manifest['status'] == 'simulated', session
        assert manifest['runs'] and all(
            r['simulation']['status'] == 'passed' for r in manifest['runs']), session
        batch_id = manifest['batch_id']
        for name in planning_view.BATCH_FILES:
            files.add(planning_view.artifact_path(session, batch_id, name))
        for run in manifest['runs']:
            for name in planning_view.RUN_FILES - {'simulator.log'}:
                files.add(planning_view.artifact_path(
                    session, batch_id, f"{run['run_id']}/{name}"))
media = root / 'demo/harness/stage/static/media'
for name in ('ot2-recorded-30s.mp4', 'ot2-recorded-poster.jpg', 'recording.json'):
    path = media / name
    if path.is_file() and not path.is_symlink():
        files.add(path)
archive = Path('/tmp/ouroboros-saved-results.tar.gz')
with tarfile.open(archive, 'w:gz') as bundle:
    for path in sorted(files):
        assert path.is_relative_to(root) and not path.is_symlink()
        bundle.add(path, arcname=str(path.relative_to(root)), recursive=False)
archive.chmod(0o600)
print('Created reviewed-artifact archive:', archive)
PY
sha256sum /tmp/ouroboros-saved-results.tar.gz
```

Transfer that archive using an approved authenticated channel such as SSH/SCP.
Compare the SHA-256 on both hosts. The export does not include the two additional
historical sessions in Brev's allowlist; eight catalog sessions reproduce the
current four-model/two-query walkthrough. Do not copy credentials or deploy keys.

### Import on the new host

Run this in a fresh checkout, after transferring the archive to `/tmp`:

```bash
sha256sum /tmp/ouroboros-saved-results.tar.gz
demo/.venv/bin/python - <<'PY'
from pathlib import Path
import tarfile
root = Path.cwd()
assert (root / 'demo/sequential-models.json').is_file(), 'Run from repository root'
with tarfile.open('/tmp/ouroboros-saved-results.tar.gz') as bundle:
    for item in bundle.getmembers():
        assert item.isfile(), 'Only regular artifact files are expected'
        target = (root / item.name).resolve()
        assert target.is_relative_to(root / 'demo/harness/planning_runs') or \
            target.is_relative_to(root / 'demo/harness/stage/static/media')
        assert not target.exists(), f'Refusing to overwrite {item.name}'
    bundle.extractall(root, filter='data')
PY
```

This requires Python 3.12's tar extraction filter. Never extract an untrusted
archive or replace existing saved sessions to “fix” a hash mismatch.

Create the local allowlist only after validating every restored session. This
fails if artifacts are missing or protocol/report hashes disagree:

```bash
demo/.venv/bin/python - <<'PY'
import json
from pathlib import Path
from demo.harness.stage.planning_view import snapshot
sessions = list(json.loads(Path('demo/sequential-models.json').read_text())['sessions'])
for session in sessions:
    data = snapshot(session)
    assert data['batches'], f'No batches: {session}'
    for batch in data['batches']:
        manifest = batch['manifest']
        assert manifest['status'] == 'simulated', session
        assert manifest['runs'] and all(
            r['simulation']['status'] == 'passed' for r in manifest['runs']), session
folder = Path('demo/private')
folder.mkdir(mode=0o700, exist_ok=True)
path = folder / 'published_sessions.json'
with path.open('x') as stream:
    stream.write(json.dumps(sessions, indent=2) + '\n')
path.chmod(0o600)
print('Verified and allowlisted', len(sessions), 'saved sessions')
PY
```

If you have no approved bundle, use the historical replay in section 4. To create
new examples, configure the private operator first and run the paid precompute
workflow described in [PRECOMPUTED_EXAMPLES.md](docs/PRECOMPUTED_EXAMPLES.md) and
`python -m demo.harness.precompute_examples --help` using `demo/.venv/bin/python`.
New runs have new IDs. Review evidence/model identity and hash-verified simulations,
then update both the local publication allowlist and the catalog mapping. Do not
label a newly generated run with an old session ID or another model's identity.

## 6. Start the public dashboard locally

Unset replay mode and start only the public viewer:

```bash
unset DEMO_REPLAY
DEMO_PUBLISHED_SESSIONS_FILE="$PWD/demo/private/published_sessions.json" \
  PUBLIC_VIEW_PORT=7200 demo/.venv/bin/python -m demo.harness.stage.public_view
```

In another terminal:

```bash
curl -fsS http://127.0.0.1:7200/api/health
curl -fsS http://127.0.0.1:7200/api/precomputed
```

Open these routes:

| URL | Expected behavior |
| --- | --- |
| `http://127.0.0.1:7200/` | Ouroboros operator-layout dashboard with saved traces |
| `http://127.0.0.1:7200/sequential` | Original sequential walkthrough |
| `http://127.0.0.1:7200/planner` | Two editable query presets and visitor API-key form |
| `http://127.0.0.1:7200/results` | Older read-only artifact/results view |

Check all four model choices and both traces per model, KG, compound structures,
plates, generated-protocol animation and simulator status. The physical video is
optional and distinct from the selected generated protocol. A missing video must
not be described as a failed simulation. Press F for fullscreen outside inputs;
the theme, resizable panes and focus controls should work.

The public service has no visitor-slot cap or dashboard inactivity timeout.
It retains 600 requests/minute per browser, excluding static dashboard assets.
Live runs remain bounded: two globally, one per browser, 20 starts/hour globally,
five starts/hour per browser, 16 model turns and 15 minutes per run. Private live
results expire after one hour or server restart. These are separate policies.

## 7. Enable visitor-key live planning

The public planner never falls back to a saved Nebius key. Visitors enter their
own key in the form; the worker receives it through stdin and uses it in memory.
Do not add a provider key to the public systemd unit, `.env`, URL or command line.
No OpenCode service is needed for this path.

The **host still needs its own Paperclip authentication** for literature tools;
visitor Nebius keys do not authenticate retrieval. After the full install:

```bash
demo/harness/paperclip.sh login
demo/harness/paperclip.sh search -s papers 'broth microdilution' -n 1 --json
```

Use your own account and review any retrieval/provider charges. The wrapper stores
login state in ignored `demo/harness/paperclip/private/`. Do not print or commit
those files. Keep `demo/.venv-ot2` installed for actual protocol simulation.

For an explicitly authorized paid rehearsal, visit `/planner`, choose a query,
enter your own key and start a run. Check actual streamed output, workflow stage
highlights, validation/compiler results and simulation hashes. Provider reasoning
appears only if the selected provider/model returns it. Verify Interrupt and
switching back to a saved trace. A synthetic automated test is not proof that your
new machine's paid provider and retrieval accounts work end to end.

## 8. Optional private operator

Only needed for the older shared planning workflow or independent precomputation.
Use the full installer and a separate private endpoint. In two terminals:

```bash
# Terminal A, repo root
demo/harness/opencode_server.sh
```

```bash
# Terminal B, repo root
STAGE_LOOPBACK_ONLY=1 HARNESS_NEBIUS_MODEL=zai-org/GLM-5.3 \
  demo/.venv/bin/python -m demo.harness.stage.server
```

Open `http://127.0.0.1:7100/planner` and use its Keys panel to configure your own
Nebius credentials. This private UI persists its key profiles; it is not the
public BYOK form. Paperclip authentication from section 7 is also needed. Explicitly
select the intended model before a paid run. The older tmux launcher's fallback
model differs, so do not assume every launcher selects GLM by default.

OpenCode listens only on `127.0.0.1:4096`. Never publish this port. Keep private
operator access behind authentication or an SSH tunnel, for example from your
laptop with your own SSH hostname:

```bash
ssh -N -L 7100:127.0.0.1:7100 your-user@your-host
```

Do not run tmux launchers alongside systemd or foreground servers on the same
ports. No part of a new-host install should copy the old OpenCode auth database,
server password, SSH private key or Nebius profiles.

## 9. Optional persistent Linux services and HTTPS

Stop the corresponding foreground processes first. Run these installers as the
normal VM user, not root; their sudo steps install units. They require noninteractive
sudo authorization and refuse to replace existing unit files.

```bash
sudo -v
# Public dashboard only:
demo/.venv/bin/python -m demo.deploy.install_viewer
sudo systemctl enable --now wwtn-viewer
systemctl is-active wwtn-viewer

# Optional private operator and OpenCode:
demo/.venv/bin/python -m demo.deploy.install_services
sudo systemctl enable --now wwtn-opencode wwtn-stage
systemctl is-active wwtn-opencode wwtn-stage
```

The viewer installer validates the local allowlist and simulation artifacts before
installation. These commands install loopback services only: they do **not** create
DNS, TLS, Brev ports, access rules, forwarding sockets or a tunnel. Service units
embed this checkout's path; reinstall/review units if the checkout moves.

For remote access, first verify localhost, then configure your host's HTTPS ingress
to forward the dashboard hostname to `127.0.0.1:7200`. Preserve the public Host and
Origin so same-origin POST checks and Secure cookies work. Public visitor keys
must travel over HTTPS. Do not expose ports 4096 or 7100 anonymously. If you expose
the private operator, give it a separate authenticated hostname.

On the existing Brev deployment, socket proxies forward 7201 → 7200 and 7101 →
7100, and Brev terminates HTTPS. Those forwarding units, hostnames and audience
settings are **not created by these installers** and must be provisioned for a
new Brev instance. See [the handoff](memory/REMOTE_HANDOFF.md); copying its old
URLs or port IDs cannot configure a new host. The checked-in Caddyfile is an
optional authenticated-viewer template, not the current Brev configuration.

## 10. Verification, restarts and troubleshooting

From the repo root, after installing `--dev` and Chromium:

```bash
demo/.venv/bin/python -m unittest \
  demo.harness.test_public_view demo.harness.test_public_runs \
  demo.harness.test_public_dashboard demo.harness.test_live_dashboard \
  demo.harness.test_planning_pipeline demo.harness.test_reliability
demo/.venv-paperclip/bin/python -m unittest demo.harness.test_planning_evidence
```

Some browser tests skip if the exact saved fixtures are missing; a skipped test is
not a successful full-dashboard verification. Check the test report. For a real
local compiler/simulator check with synthetic inputs and no LLM call:

```bash
demo/.venv/bin/python -m demo.harness.smoke --simulate
```

This writes ignored test artifacts. It verifies the direct backend, not agent
autonomy, biological validity or robot execution.

| Symptom | Check |
| --- | --- |
| Dashboard has no traces | Correct revision, restored session directories, local allowlist and matching catalog IDs |
| `DEMO_PUBLISHED_SESSIONS_FILE` missing | Supply the absolute local allowlist path or use the installed viewer unit |
| Simulation marked stale | Original protocol/report/manifest hashes; restore original bytes, never force a pass |
| Full KG is unavailable | Tracked bacterial CSVs present at checkout-relative paths |
| Public live run fails retrieving papers | Host Paperclip login, network and installed retrieval environment |
| New run gets 429 | Live concurrency/start-rate limits or browser request budget; there is no visitor-slot cap |
| Busy page left open after an update | Refresh; old admission pages are no longer served |
| HTTPS endpoint fails but localhost works | Ingress target, TLS, Host/Origin forwarding, audience rules; do not expose OpenCode to fix this |
| Wrong process on a port | Inspect `ss -ltn`; stop only the known launcher/service or select a different port |
| Simulator fails to import | Use the separate pinned `demo/.venv-ot2`, not the app environment |

Before restarting `wwtn-viewer`, ensure no live run is active: the restart cancels
public workers and loses private in-memory ownership/results. Check the operator
and public worker processes without dumping their environment or stdin. Static UI
changes are served from disk; backend changes require a viewer restart. Never
restart the private operator/OpenCode during an active private run.

Back up only approved saved-result artifacts through private storage; keep their
provenance and exact hashes. Do not `git add -f` ignored credentials, media, runtime
state or visitor artifacts to make a fresh clone appear complete.

## Validation status of this guide

Commands and paths were checked against the installer, launchers, routes, artifact
validator and pinned manifests. A temporary Git-only checkout (no private state or
current saved-result directories) served the historical replay in Chromium: four
hash-verified protocols and 96 wells, with writes disabled. The exact export/import
and validation snippets also restored all eight current sessions in temporary
storage without credentials. Both checks used the existing installed Python
environment; they do not prove fresh dependency installation on another device. The full install is verified historically on
Linux ARM64. A current clean-machine dependency download and paid public run have
not been repeated for this documentation change.

TODO(final): Rehearse the complete fresh-host installation and visitor-key paid
workflow on the destination hardware before calling that deployment presentation-ready.
