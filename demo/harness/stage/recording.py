"""Serve only the reviewed fixed recording, with browser byte-range support."""
import json
from pathlib import Path
from aiohttp import web

MEDIA = Path(__file__).parent / 'static/media'
FILES = {'ot2-recorded-30s.mp4', 'ot2-recorded-poster.jpg'}


def media_path(name):
    path = MEDIA / name
    if name not in FILES or path.is_symlink() or not path.is_file():
        raise web.HTTPNotFound()
    return path


async def info(request):
    try:
        media_path('ot2-recorded-30s.mp4')
        data = json.loads((MEDIA / 'recording.json').read_text())
        return web.json_response({'available': True, 'url': '/media/ot2-recorded-30s.mp4',
            'poster': '/media/ot2-recorded-poster.jpg',
            'duration_seconds': data['duration_seconds'], 'speed_multiplier': data['speed_multiplier'],
            'label': data['label'], 'provenance': data['provenance']})
    except (OSError, ValueError, KeyError, web.HTTPNotFound):
        return web.json_response({'available': False})


async def video(request):
    return web.FileResponse(media_path(request.match_info['name']))


def routes():
    return [web.get('/api/recording', info), web.get('/media/{name}', video)]
