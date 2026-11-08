# Demo deployment

The active deployment is Brev-managed HTTPS, with a public dashboard/sequential
viewer with visitor-key planning and an authenticated shared operator. See the authoritative
[handoff](../memory/REMOTE_HANDOFF.md) for exact endpoints, ports, IDs, health commands
and the operator-forwarder reboot gap. Historical Caddy examples here are optional
new-host templates, not the running deployment; do not apply them to this VM.

The Python apps bind loopback (operator 7100, viewer 7200, OpenCode 4096). Separate
systemd socket proxies expose forwarding ports 7101/7201 to Brev ingress. Brev
terminates HTTPS and enforces the operator email allowlist. Viewer access is public
by user instruction; operator anonymous access remains disabled. Do not publish
OpenCode or change app bindings to fix an ingress problem.

The viewer has no OpenCode connection. Saved viewing serves only explicitly
published sessions and allowlisted assets/downloads. `/planner` accepts a visitor's
Nebius key for a bounded isolated process, with no credential persistence or
fallback to private team keys. Only `/api/runs` and owner-authorized stop routes
accept POST; old private operator command routes remain unavailable. Global read
limit: 600 requests/minute. Public runs: two concurrent, one per browser, sixteen
model turns, fifteen minutes; five starts/browser/hour and twenty globally/hour.
Results belong to an HttpOnly-cookie browser identity and expire after an hour or
service restart. No raw transcripts or simulator stderr logs are exposed.

To publish a new result, review its actual model identity, evidence, proposal,
protocol hashes and simulator reports. Add its session to ignored
`demo/private/published_sessions.json`, and (for sequential) its model mapping to
`demo/sequential-models.json`. Restart only wwtn-viewer. Never edit a published
session to continue experimentation. Eight new verified sessions plus two historical
judge sessions are currently allowed. Do not expose credential directories.

For a new host, `python -m demo.deploy.install_services` / `install_viewer` prepare
private units and refuse to overwrite existing ones. They do not reproduce all
Brev ingress settings or ignored artifacts/media automatically. Read their help and
SETUP.md; never run the old tmux launcher alongside existing systemd services.

Services are active/enabled; operator ingress socket is active but disabled at boot.
Reboot recovery has not been tested. Domain review, hardware validation, paid public-run rehearsal and stronger OS-level tenant isolation remain open. No production
certification is claimed. Preserve ignored credentials/artifacts and never reset a
dirty checkout during deployment.
