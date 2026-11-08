#!/usr/bin/env python3
"""Install isolated Python runtimes and checksum-pinned agent/retrieval binaries.

Requires uv and Python 3.12. Linux aarch64 is the verified binary platform.
No authentication is copied, no services are started, no model is invoked.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

DEMO = Path(__file__).resolve().parent
ROOT = DEMO.parent


def run(*args):
    subprocess.run([str(a) for a in args], cwd=ROOT, check=True)


def download(url, path, digest):
    if not path.exists():
        temporary = path.with_suffix('.part')
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open('wb') as out:
            shutil.copyfileobj(response, out)
        temporary.replace(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError(f'Checksum mismatch for {path.name}; stop and review upstream, do not silently upgrade')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dev', action='store_true')
    args = parser.parse_args()
    if platform.system() != 'Linux' or platform.machine() not in ('aarch64', 'arm64'):
        parser.error('Pinned agent binary is Linux aarch64 only; use the hosted browser or review/add a platform manifest first')
    if not shutil.which('uv'):
        parser.error('Install uv first and put it on PATH')
    cache = DEMO / '.downloads'
    cache.mkdir(exist_ok=True)
    for name in ('.venv', '.venv-ot2', '.venv-paperclip'):
        if not (DEMO / name / 'bin/python').exists():
            run('uv', 'venv', '--python', '3.12', DEMO / name)
    run('uv', 'pip', 'sync', '--python', DEMO / '.venv/bin/python', DEMO / ('requirements-dev.lock' if args.dev else 'requirements.lock'))
    run('uv', 'pip', 'sync', '--python', DEMO / '.venv-ot2/bin/python', DEMO / 'requirements-sim.lock')
    manifest = json.loads((DEMO / 'harness/paperclip/install-manifest.json').read_text())
    wheel = cache / manifest['wheel_filename']
    download(manifest['source_url'], wheel, manifest['sha256'])
    run('uv', 'pip', 'sync', '--python', DEMO / '.venv-paperclip/bin/python', DEMO / 'requirements-paperclip.lock')
    run('uv', 'pip', 'install', '--no-deps', '--python', DEMO / '.venv-paperclip/bin/python', wheel)
    manifest = json.loads((DEMO / 'harness/opencode/install-manifest.json').read_text())
    archive = cache / manifest['asset']
    download(manifest['url'], archive, manifest['verified_sha256'])
    destination = DEMO / 'harness/opencode' / ('v' + manifest['version'])
    destination.mkdir(exist_ok=True)
    with tarfile.open(archive) as tar:
        tar.extractall(destination, filter='data')
    # The pinned OpenCode binary has an embedded Bun dependency installer.
    run(DEMO / 'harness/opencode_server.sh', 'debug', 'agent', 'planner')
    dependency = DEMO / '.opencode/node_modules/@ai-sdk/openai-compatible/dist/index.mjs'
    if not dependency.is_file():
        raise RuntimeError('OpenCode dependency bootstrap incomplete; inspect foreground debug output')
    print('Installed. Configure your own credentials; see demo/SETUP.md. No servers started.')


if __name__ == '__main__':
    main()
