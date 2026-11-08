"""Make the fixed, silent OT-2 recording for the demo; no network or robot access.

Run from the repo root: python -m demo.harness.prepare_video SOURCE.mov
Requires ffmpeg and ffprobe. Large media stays in the ignored demo media directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from demo.harness.paths import DEMO

MEDIA = DEMO / 'harness/stage/static/media'
SOURCE_URL = 'https://drive.google.com/file/d/1a286W82oSFBIyOaE4UKroC3fk-dl8c7y/view'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe', '-v', 'error',
        '-show_entries', 'format=duration,size', '-of', 'json', str(path)], text=True))['format']


def prepare(source, seconds=30):
    if not 5 <= seconds <= 120:
        raise ValueError('Choose a clip length between 5 and 120 seconds')
    duration = float(probe(source)['duration'])
    if duration < seconds:
        raise ValueError('Source must be at least as long as the requested clip')
    MEDIA.mkdir(parents=True, exist_ok=True)
    clip = MEDIA / 'ot2-recorded-30s.mp4'
    temporary = MEDIA / 'encoding.mp4'
    speed = duration / seconds
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', str(source),
        '-map', '0:v:0', '-vf', f'setpts=PTS/{speed},fps=30,scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2',
        '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart', '-t', str(seconds), '-y', str(temporary)], check=True, timeout=1800)
    temporary.replace(clip)
    write_manifest(source, clip, duration, speed)


def write_manifest(source, clip, duration, speed):
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-ss', '5', '-i', str(clip),
        '-frames:v', '1', '-y', str(MEDIA / 'ot2-recorded-poster.jpg')], check=True, timeout=30)
    manifest = {'source_url': SOURCE_URL, 'source_sha256': digest(source),
        'source_duration_seconds': duration, 'duration_seconds': float(probe(clip)['duration']),
        'speed_multiplier': speed, 'sha256': digest(clip), 'audio': False,
        'label': 'Recorded OT-2 demonstration',
        'provenance': 'User-supplied physical robot recording. Separate from every generated protocol and simulation shown here.'}
    temporary = MEDIA / 'recording.tmp'
    temporary.write_text(json.dumps(manifest, indent=2) + '\n')
    temporary.replace(MEDIA / 'recording.json')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    prepare(args.source)
