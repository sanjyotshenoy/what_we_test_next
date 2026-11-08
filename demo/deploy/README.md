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

Use a service manager with restart-on-failure and a non-root account for the Python
services. Keep logs private and bounded. Preserve ignored credentials and artifacts
when updating the checkout; never reset a dirty VM checkout. Pin the deployed Git
commit, retain the preceding commit for rollback, and back up private state through
the operator's approved storage rather than Git. The existing tmux launcher survives
SSH disconnects, but does not provide reboot recovery.

<!-- TODO(final): Deployment is not production-certified. Public hostname, audience
policy, TLS/auth external verification, service-manager installation and a successful
fresh autonomous rehearsal remain required. Independent visitor runs need per-user
session ownership, concurrency limits and an enforced inference-spend budget. -->
