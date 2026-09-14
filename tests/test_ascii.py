import tempfile,subprocess,unittest,hashlib,threading
from pathlib import Path
from PIL import Image
from loop_studio.core import Store
from loop_studio.media import ingest,export
from loop_studio.ascii_effect import render_ascii

class AsciiTests(unittest.TestCase):
    def test_effect_exports_video_audio_without_changing_original(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'clip.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=160x90:rate=30:duration=1','-f','lavfi','-i','sine=frequency=440:duration=1','-c:v','libx264','-c:a','aac','-shortest',str(source)],check=True)
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            store=Store(root/'projects');p=store.create();a=ingest(store,p['id'],source,'clip.mp4');p=store.load(p['id'])
            p=store.update(p['id'],p['version'],{'op':'add','asset_id':a['id'],'start':0,'end':1})
            p=store.update(p['id'],p['version'],{'op':'settings','style':{'ascii_mode':'green','ascii_columns':40}})
            result=export(store,p['id'],p,preview=True)
            self.assertTrue(result['audio']);self.assertAlmostEqual(result['duration'],1,delta=.04)
            self.assertEqual(hashlib.sha256((store.directory(p['id'])/a['original']).read_bytes()).hexdigest(),digest)
            frame=root/'frame.png';subprocess.run(['ffmpeg','-v','error','-i',str(store.directory(p['id'])/result['path']),'-frames:v','1',str(frame)],check=True)
            with Image.open(frame) as image:
                rgb=image.convert('RGB');self.assertGreater(sum(rgb.getpixel((x,y))[1]-rgb.getpixel((x,y))[0] for x in range(0,rgb.width,4) for y in range(0,rgb.height,4)),1000)
            restored=store.update(p['id'],p['version'],{'op':'undo'});self.assertEqual(restored['style']['ascii_mode'],'off')
    def test_invalid_ascii_mode_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(tmp);p=store.create()
            with self.assertRaises(ValueError):store.update(p['id'],0,{'op':'settings','style':{'ascii_mode':'unknown'}})
