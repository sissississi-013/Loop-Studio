import hashlib
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from loop_studio.core import Store
from loop_studio.media import ingest, export, probe


@unittest.skipUnless(shutil.which('ffmpeg'), 'FFmpeg required')
class MediaTests(unittest.TestCase):
    def test_full_duration_original_export_and_sound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'input.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=160x90:rate=15:duration=15',
                            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=15', '-c:v', 'libx264', '-c:a', 'aac',
                            '-pix_fmt', 'yuv420p', '-shortest', str(source)], check=True)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            store = Store(root / 'projects')
            p = store.create('Integration')
            a = ingest(store, p['id'], source, 'my film.mp4')
            self.assertEqual(a['sha256'], digest)
            self.assertGreater(probe(store.directory(p['id']) / a['proxy'])['duration'], 14.9)
            p = store.load(p['id'])
            p = store.update(p['id'], p['version'], {'op': 'add', 'asset_id': a['id'], 'start': 13, 'end': 14.5})
            p = store.update(p['id'], p['version'], {'op': 'settings', 'style': {'title': "Hello: 100% 'world'", 'music': 'pulse'}})
            result = export(store, p['id'], p)
            self.assertEqual((result['width'], result['height']), (1920, 1080))
            self.assertTrue(result['audio'])
            self.assertAlmostEqual(result['duration'], 1.5, delta=.12)
            video = store.directory(p['id']) / result['path']
            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-f', 'null', '-'], check=True)
            # Non-silent audio survives the original-source cut and music mix.
            raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(video), '-vn', '-f', 's16le', '-'])
            self.assertGreater(len(set(raw)), 100)
            self.assertEqual(hashlib.sha256((store.directory(p['id']) / a['original']).read_bytes()).hexdigest(), digest)

    def test_cancel_import_removes_partial_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=red:size=64x64:duration=2', str(path)], check=True)
            store = Store(Path(tmp) / 'projects')
            p = store.create()
            cancel = threading.Event()
            cancel.set()
            with self.assertRaisesRegex(ValueError, 'cancelled'):
                ingest(store, p['id'], path, 'input.mp4', cancel)
            self.assertFalse(store.load(p['id'])['assets'])

    def test_ten_silent_shots_do_not_accumulate_audio_padding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'silent.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=blue:size=64x64:rate=30:duration=1',str(source)],check=True)
            store=Store(root/'projects');p=store.create();asset=ingest(store,p['id'],source,'silent.mp4')
            p=store.load(p['id'])
            for _ in range(10):p=store.update(p['id'],p['version'],{'op':'add','asset_id':asset['id'],'start':0,'end':.5})
            result=export(store,p['id'],p,preview=True)
            self.assertAlmostEqual(result['duration'],5,delta=.06)
            self.assertTrue(result['audio'])

    def test_rotation_is_normalized_in_proxy_and_preserved_in_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source.mp4';rotated=root/'rotated.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=160x90:duration=1',str(source)],check=True)
            subprocess.run(['ffmpeg','-v','error','-i',str(source),'-c','copy','-metadata:s:v:0','rotate=90',str(rotated)],check=True)
            metadata=__import__('json').loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(rotated)]))
            if not metadata['streams'][0].get('side_data_list'):
                # New FFmpeg releases use an explicit display matrix input option.
                subprocess.run(['ffmpeg','-v','error','-y','-display_rotation','90','-i',str(source),'-c','copy',str(rotated)],check=True)
            digest=hashlib.sha256(rotated.read_bytes()).hexdigest()
            store=Store(root/'projects');p=store.create();asset=ingest(store,p['id'],rotated,'rotated.mp4')
            self.assertEqual(asset['sha256'],digest)
            proxy=probe(store.directory(p['id'])/asset['proxy'])
            self.assertGreater(proxy['height'],proxy['width'])
            self.assertGreater(asset['height'],asset['width'])
