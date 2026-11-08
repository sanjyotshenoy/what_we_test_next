"""Install reboot/restart recovery for the PRIVATE backend only (Ubuntu/systemd).

Run as the VM account, not root. Requires sudo for unit installation. Does not
install Caddy, publish results, open ports, or start the new services.
"""
import os
from pathlib import Path
import pwd
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def units(root, user):
    # systemd escaping differs from shell escaping; constrain paths rather than guess.
    if any(c not in '/-_.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' for c in str(root)):
        raise ValueError('Unsupported characters in checkout path')
    common = f'''[Service]
Type=simple
User={user}
WorkingDirectory={root}
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
Restart=on-failure
RestartSec=5
TimeoutStopSec=30
Environment=STAGE_LOOPBACK_ONLY=1
'''
    return {
        'wwtn-opencode.service': '[Unit]\nDescription=WWTN private OpenCode\nAfter=network-online.target\nWants=network-online.target\n'
        + common + f'ExecStart={root}/demo/harness/opencode_server.sh\n\n[Install]\nWantedBy=multi-user.target\n',
        'wwtn-stage.service': '[Unit]\nDescription=WWTN private operator UI\nAfter=network-online.target wwtn-opencode.service\nRequires=wwtn-opencode.service\n'
        + common + f'ExecStart={root}/demo/.venv/bin/python -m demo.harness.stage.server\n\n[Install]\nWantedBy=multi-user.target\n',
    }


if __name__ == '__main__':
    if os.getuid() == 0:
        raise SystemExit('Run as the VM account; sudo is used only to install units.')
    user = pwd.getpwuid(os.getuid()).pw_name
    with tempfile.TemporaryDirectory() as folder:
        files = []
        for name, content in units(ROOT, user).items():
            path = Path(folder) / name
            path.write_text(content)
            files.append(str(path))
        subprocess.run(['systemd-analyze', 'verify', *files], check=True)
        for path in files:
            dest = Path('/etc/systemd/system') / Path(path).name
            if dest.exists():
                raise SystemExit(f'{dest.name} exists; review before replacing it.')
        for path in files:
            subprocess.run(['sudo', '-n', 'install', '-m', '644', path, '/etc/systemd/system/'], check=True)
    subprocess.run(['sudo', '-n', 'systemctl', 'daemon-reload'], check=True)
    print('Units installed, not started. Stop the checkout tmux launcher before enabling services.')
