"""Recording is optional, range-seekable, and restricted to exact media files."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase
from demo.harness.stage import recording


class RecordingTests(AioHTTPTestCase):
    async def get_application(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        override = patch.object(recording, 'MEDIA', self.root)
        override.start(); self.addCleanup(override.stop)
        app = web.Application()
        app.add_routes(recording.routes())
        return app

    async def test_missing_recording_does_not_break_demo(self):
        response = await self.client.get('/api/recording')
        self.assertEqual(await response.json(), {'available': False})

    async def test_exact_media_only_and_seeking(self):
        video = self.root / 'ot2-recorded-30s.mp4'
        video.write_bytes(b'0123456789')
        (self.root / 'recording.json').write_text(json.dumps({
            'duration_seconds': 30, 'speed_multiplier': 25.1,
            'label': 'Recorded OT-2 demonstration', 'provenance': 'Separate recording'}))
        response = await self.client.get('/api/recording')
        self.assertTrue((await response.json())['available'])
        response = await self.client.get('/media/ot2-recorded-30s.mp4', headers={'Range': 'bytes=2-5'})
        self.assertEqual(response.status, 206)
        self.assertEqual(await response.read(), b'2345')
        for path in ('recording.json', 'encoding.mp4', 'IMG_2874.mov'):
            response = await self.client.get('/media/' + path)
            self.assertEqual(response.status, 404)
        video.unlink(); video.symlink_to(self.root / 'recording.json')
        self.assertEqual((await self.client.get('/media/ot2-recorded-30s.mp4')).status, 404)
