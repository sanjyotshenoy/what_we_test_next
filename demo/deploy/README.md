# Private operator and authenticated results viewer

The operator UI is a single shared session, not a multi-user application. Keep
7100 (operator) and 4096 (OpenCode) on loopback. Do not publish them through Brev.

The separate results viewer on loopback port 7200 has no OpenCode connection,
accepts no writes, and serves only explicitly selected sessions. It exposes neither
key/model management, raw transcripts, simulator stderr logs, nor arbitrary static
files. Its global 600 requests/minute ceiling and two-second snapshot cache bound
repeated polling; this is a small-team demo, not a large-scale service.

## Preparing publication

1. Review the exact artifacts to share, including retrieved passages and proposals.
   Put only their session IDs in a JSON list at `demo/private/published_sessions.json`.
   An empty/missing list fails closed. Start a new session to keep subsequent private
   work out of a previously published session.
2. From the repo root run:
   `DEMO_PUBLISHED_SESSIONS_FILE=demo/private/published_sessions.json demo/.venv/bin/python -m demo.harness.stage.public_view`.
   The default data root is the live artifact directory. Set `DEMO_REPLAY=1` to use
   the packaged synthetic replay directory instead; the two roots are not combined.
3. Configure a dedicated HTTPS hostname and a strong viewer password in the operator's
   secret manager. Generate its hash with Caddy's interactive `caddy hash-password`.
   Supply the hostname and hash through `DEMO_HOSTNAME` and
   `DEMO_VIEWER_PASSWORD_HASH` to the Caddy service; do not put plaintext passwords
   in commands, Git, or chat. Validate the supplied Caddyfile before starting it.
4. Expose only Caddy's required HTTP/HTTPS listeners after authorization and DNS/TLS
   checks. Do not expose 7200 directly: authentication is performed by Caddy.
5. Verify anonymously that results/downloads require authentication, then verify
   authenticated access, denied mutations, session isolation and certificate trust
   from outside the VM. A Brev-managed HTTPS URL needs a separately reviewed proxy
   configuration; do not assume its forwarding preserves the boundary above.

`python3 demo/deploy/install_services.py` installs (but does not start) private
systemd units as the VM account, using sudo only for unit installation. It refuses
to overwrite existing units. After the checkout-owned tmux launcher is stopped,
`sudo systemctl enable --now wwtn-opencode wwtn-stage` enables restart-on-failure
and reboot recovery, with a private umask and loopback-only stage binding. Unit
files record the checkout path: regenerate/review them if the checkout moves.

Keep logs private and bounded. Preserve ignored credentials and artifacts
when updating the checkout; never reset a dirty VM checkout. Pin the deployed Git
commit, retain the preceding commit for rollback, and back up private state through
the operator's approved storage rather than Git. The existing tmux launcher survives
SSH disconnects, but does not provide reboot recovery.

<!-- TODO(final): Deployment is not production-certified. Public hostname, audience
policy, TLS/auth external verification and a successful
fresh autonomous rehearsal remain required. Independent visitor runs need per-user
session ownership, concurrency limits and an enforced inference-spend budget. -->

## Historical Brev checkpoint before judge preparation (2026-11-08)

29 tests passed on the ARM64 VM, including public route boundaries, unpublished
session denial, download boundaries, request limiting, browser layout and evidence
argument validation. Private systemd services were installed, enabled, and verified
healthy with listeners only on 127.0.0.1:7100 and 127.0.0.1:4096. Reboot/crash
recovery is configured but has not been tested by rebooting the shared instance.

Two authenticated autonomous rehearsals failed before compilation. The second,
`ses_e45ae9206ffeUX7erdKXyRnDpu`, successfully retrieved context and literature,
then hit citation validation followed by malformed tool-call JSON. No autonomous
simulation success is claimed; the earlier four successful simulations were direct
backend tests. No automatic model fallback or further model retries were started.
The public results viewer and Caddy have not been started on the VM; the operator
must choose the hostname/access policy and review sessions before publication.

## Current judge checkpoint (supersedes the earlier service state)

The loopback-only viewer is now installed/enabled as `wwtn-viewer.service`, alongside
the operator and OpenCode. It serves two explicitly reviewed successful autonomous
sessions, with the real-graph software rehearsal selected first. The operator also
opens that saved result after restart through `DEMO_DEFAULT_SESSION` in its systemd
`presentation.conf` drop-in. See [judge runbook](../docs/JUDGE_RUNBOOK.md).

For a new host, `python -m demo.deploy.install_viewer` validates that the reviewed
allowlist has completed, hash-verified simulations, then installs (but does not
start) the loopback viewer unit. It refuses to overwrite an existing unit. Copy
approved artifacts/media through private storage; credentials are not viewer data.
No Caddy, public hostname, TLS certificate or external access was configured.
