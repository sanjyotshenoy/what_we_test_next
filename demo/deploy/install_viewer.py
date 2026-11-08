"""Install a loopback-only prepared-results viewer. Does not open public access.

Requires a reviewed demo/private/published_sessions.json. Refuses to replace an
existing service. Run from the repository root as python -m demo.deploy.install_viewer.
"""
import json
import os
from pathlib import Path
import pwd
import subprocess
import tempfile

from demo.deploy.install_services import ROOT
from demo.harness.stage import planning_view


def main():
    if os.getuid() == 0:
        raise SystemExit('Run as the VM account; sudo only installs the service.')
    config = ROOT / 'demo/private/published_sessions.json'
    sessions = json.loads(config.read_text())
    if not isinstance(sessions, list) or not sessions:
        raise SystemExit('A nonempty reviewed session list is required')
    for session in sessions:
        snapshot = planning_view.snapshot(session)
        if not snapshot['batches'] or any(b['manifest']['status'] != 'simulated' or
                any(r['simulation']['status'] != 'passed' for r in b['manifest']['runs'])
                for b in snapshot['batches']):
            raise SystemExit('Every selected batch must have verified simulation results')
    user = pwd.getpwuid(os.getuid()).pw_name
    if any(c not in '/-_.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' for c in str(ROOT)):
        raise SystemExit('Unsupported checkout path')
    content = f'''[Unit]
Description=WWTN private judge results viewer
After=network-online.target
[Service]
Type=simple
User={user}
WorkingDirectory={ROOT}
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
Restart=on-failure
RestartSec=5
Environment=DEMO_PUBLISHED_SESSIONS_FILE={config}
ExecStart={ROOT}/demo/.venv/bin/python -m demo.harness.stage.public_view
[Install]
WantedBy=multi-user.target
'''
    name = 'wwtn-viewer.service'
    if (Path('/etc/systemd/system') / name).exists():
        raise SystemExit('Viewer service exists; review before replacing it.')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / name
        path.write_text(content)
        subprocess.run(['systemd-analyze', 'verify', str(path)], check=True)
        subprocess.run(['sudo', '-n', 'install', '-m', '644', str(path), '/etc/systemd/system/'], check=True)
    subprocess.run(['sudo', '-n', 'systemctl', 'daemon-reload'], check=True)
    print('Installed, not started. Viewer binds only 127.0.0.1:7200.')


if __name__ == '__main__':
    main()
