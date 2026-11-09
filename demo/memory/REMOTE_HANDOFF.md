# Brev / Codex Remote handoff

Current as of 2026-11-09. Read [MEMORY.md](MEMORY.md) first; earlier deployment and
credential-setup history is in [REMOTE_HANDOFF_HISTORY.md](REMOTE_HANDOFF_HISTORY.md).
This file is operational guidance, not permission to change access policies.

For migration or a fresh device, follow [NEW_DEVICE_SETUP.md](../NEW_DEVICE_SETUP.md).
It distinguishes tracked source from the ignored saved artifacts/media and includes
reviewed export/import and validation. Do not clone private credential directories.

## Resume work

Host `brev-o10eetwuq`, Brev instance `biohackdemo`, directory
`/home/ubuntu/what_we_test_next`, branch `demo/judge-rehearsal`. Select that workspace
in Codex Remote. Always check `git status --short --branch` before editing. Preserve
uncommitted work; never reset or switch the shared VM checkout to an older clone.
Current sequential/runtime checkpoint is `55d8759`, plus later documentation commits.
The user subsequently authorized pushing demo/judge-rehearsal; it is now on
GitHub at sanjyotshenoy/what_we_test_next. No main merge was performed. The push
used the companion host because Brev uses a read-only Git deploy key.

Codex executable: `/home/ubuntu/.local/bin/codex` (not always on noninteractive PATH).
At verification, `app-server daemon version` reported running, CLI/server 0.167.0,
backend pid. Process includes --remote-control; `login status` reported ChatGPT login.
This verifies host readiness, not the user's mobile connection. No fresh pairing
code was generated and no remote-control/permission settings were changed.

Read-only checks:

```bash
/home/ubuntu/.local/bin/codex app-server daemon version
/home/ubuntu/.local/bin/codex login status
git status --short --branch
systemctl is-active wwtn-opencode wwtn-stage wwtn-viewer
systemctl is-active wwtn-viewer-forward.socket wwtn-operator-forward.socket
curl -fsS http://127.0.0.1:7100/api/health
curl -fsS http://127.0.0.1:7200/api/health
```

Official Remote usage: https://developers.openai.com/blog/mastering-codex-remote-for-engineering
For a client-side failure, check the selected host/workspace and the app's connection
state before restarting anything. Remote sessions may be doing active work.

## Network and services

| Component | Listener / forwarding | Lifecycle |
| --- | --- | --- |
| OpenCode | 127.0.0.1:4096 | wwtn-opencode enabled, active |
| Operator | 127.0.0.1:7100 | wwtn-stage enabled, active |
| Judge + sequential | 127.0.0.1:7200 | wwtn-viewer enabled, active |
| Judge ingress | socket 7201 → 127.0.0.1:7200 | wwtn-viewer-forward.socket enabled, active |
| Operator ingress | socket 7101 → 127.0.0.1:7100 | wwtn-operator-forward.socket active, **not enabled** |

Forward services use systemd-socket-proxyd. Brev HTTPS destination ports are 7201
and 7101, not the loopback app ports. Brev handles public TLS and operator login;
Caddy is not installed or active. Never expose 4096. Do not start legacy tmux
launchers alongside systemd services. Public `/planner` now starts bounded visitor-key runs; no saved Nebius key is available to them.

- Public dashboard: https://demo-o10eetwuq.gobrev.dev ; walkthrough: /sequential;
  visitor-key planning: /planner; old read-only results: /results.
  Brev port ID `nport-3LpUrWC1nR7XkrW1qZjTltSuEce`, anonymous enabled.
- Operator: https://operator-o10eetwuq.gobrev.dev ; Brev port ID
  `nport-3LpWC4Pv7dAgipVm7b6lXSq48kZ`, anonymous disabled, two current org members.
  Email allowlist does not automatically track future membership.

**Reboot gap:** the operator forward socket was started for testing but not enabled.
After reboot the operator URL may return 503 even when the backend is healthy.
Inspect it; starting the existing socket (`sudo systemctl start
wwtn-operator-forward.socket`) restores the existing route. No reboot was tested.
Changing boot policy or audience should be an explicit operational decision.

When investigating 503, check service/listener/forwarder before changing Brev ports.
Use a browser User-Agent for external probes: bare urllib can get a separate
Cloudflare 403. Signed-out operator requests should redirect to Brev authentication;
viewer /api/prompt POST should return 405 and /api/keys should return 404.

## Updating and publishing

Coordinate with the operator. Static sequential assets are read per request; changes
do not need an operator restart. Changes to public_view.py or its allowlist require
only `sudo systemctl restart wwtn-viewer`. Never restart OpenCode or stage during a
live run. Check /api/health for idle first. Stage restart loses in-memory selection,
not saved artifacts. The independent viewer remains usable during inference.

Publication requires reviewed session artifacts plus an entry in ignored
`demo/private/published_sessions.json`. To include that session in the sequential
model picker, also map it to its verified model in `demo/sequential-models.json`.
The current viewer has ten sessions; sequential maps eight. Keep published sessions
immutable; new experiments need new sessions. Preserve the two original default
sessions unless deliberately replacing the judge presentation.

Inference uses Nebius; current live operator default remains GLM-5.3 low reasoning.
Four models are used by the precomputed examples. No local 5090 inference is needed.
Credentials already exist under demo/.env, harness/opencode/private and
harness/paperclip/private; never show contents or overwrite authentication during
updates. Source secret name is NEBIUS_API_KEY in Brev Secrets. Do not copy secrets
into Git, handoffs, public snapshots or browser assets.

Ignored planning artifacts, private receipts, media and auth must be backed up
through approved private storage; Git bundles transfer code only. The original
four-antibiotic reference and old failures are preserved in history. Current
validation and scientific limitations are in MEMORY.md and PRECOMPUTED_EXAMPLES.md.

Public BYOK ownership is in memory. Restarting wwtn-viewer cancels active public
runs and expires their private results; coordinate before future restarts. Public
workers never use private OpenCode credentials. See MEMORY.md for bounds and the
uncompleted paid rehearsal. No credential file is required for public Nebius use.

## Current public visitor policy — 2026-11-09

No dashboard visitor-slot cap or inactivity expiry. Earlier 30-slot admission and
its heartbeat/busy page were removed at user request. Per-browser request
throttling (600/minute) remains, with stale accounting discarded independently of
access. The two concurrent public live-run cap, start-rate limits, visitor-owned
results, private-result expiry and key isolation remain unchanged. See the
[verification log](../docs/11-09-2026.md). Do not restore the old visitor cap from
historical notes. Service restart still loses in-memory private live results.
