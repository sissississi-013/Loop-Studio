import copy
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path
from PIL import Image
from loop_studio.core import Store
from loop_studio.providers import direct, model_json
from loop_studio.media import ingest


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(self.tmp.name);self.p=self.store.create()
        self.p['assets']={'a':{'id':'a','duration':20,'kind':'clip'},'b':{'id':'b','duration':10,'kind':'clip'}}
        self.p['analysis']={aid:{'mode':'model','description':'Fixture','candidates':[{'start':0,'end':3,'score':.7}]} for aid in self.p['assets']}
        self.store.save(self.p)
        for aid in ['a','b']:
            self.p=self.store.update(self.p['id'],self.p['version'],{'op':'add','asset_id':aid,'start':0,'end':5})

    def test_targeted_offline_revision_preserves_other_shots(self):
        before=copy.deepcopy(self.p)
        result=direct(self.store,self.p['id'],self.p,{'brief':'Make this shorter','target_shot_id':self.p['timeline'][0]['id']},threading.Event(),lambda _:None)
        self.assertLess(result['timeline'][0]['end'],5)
        self.assertEqual(result['timeline'][1],before['timeline'][1])
        self.assertEqual(self.store.load(self.p['id']),before)

    def test_model_cannot_change_untargeted_shots(self):
        reply={'shots':[{'asset_id':'a','start':1,'end':3,'caption':'A detail'}],'rationale':'Trim the selected shot'}
        with patch('loop_studio.providers.model_json',return_value=reply):
            result=direct(self.store,self.p['id'],self.p,{'brief':'A detail','target_shot_id':self.p['timeline'][0]['id'],'use_model':True},threading.Event(),lambda _:None)
        self.assertEqual(result['timeline'][1],self.p['timeline'][1])
        self.assertEqual(result['timeline'][0]['id'],self.p['timeline'][0]['id'])

    def test_invalid_model_ranges_leave_project_intact(self):
        reply={'shots':[{'asset_id':'a','start':19,'end':100}], 'rationale':'Bad'}
        with patch('loop_studio.providers.model_json',return_value=reply),self.assertRaises(ValueError):
            direct(self.store,self.p['id'],self.p,{'use_model':True},threading.Event(),lambda _:None)
        self.assertEqual(self.store.load(self.p['id']),self.p)

    def test_locked_shot_is_preserved_in_full_draft(self):
        self.p=self.store.update(self.p['id'],self.p['version'],{'op':'shot','shot_id':self.p['timeline'][1]['id'],'changes':{'locked':True}})
        result=direct(self.store,self.p['id'],self.p,{'brief':'fast'},threading.Event(),lambda _:None)
        self.assertEqual(result['timeline'][1],self.p['timeline'][1])

    def test_reference_image_original_is_preserved(self):
        path=Path(self.tmp.name)/'reference.png'
        Image.new('RGB',(200,100),(180,110,80)).save(path)
        original=path.read_bytes()
        asset=ingest(self.store,self.p['id'],path,'reference.png',kind='reference')
        self.assertTrue(asset['still'])
        self.assertEqual((self.store.directory(self.p['id'])/asset['original']).read_bytes(),original)

    def test_user_notes_override_model_description_in_direction(self):
        self.p=self.store.update(self.p['id'],self.p['version'],{'op':'notes','asset_id':'a','text':'A black swan, not a heron.'})
        reply={'shots':[{'asset_id':'a','start':0,'end':3,'caption':''}],'rationale':'A bird'}
        with patch('loop_studio.providers.model_json',return_value=reply) as model:
            direct(self.store,self.p['id'],self.p,{'use_model':True},threading.Event(),lambda _:None)
        self.assertIn('A black swan, not a heron.',model.call_args.args[0])

    def test_reference_pace_comes_from_full_duration_scene_changes(self):
        import subprocess
        from loop_studio.providers import sample_asset
        source=Path(self.tmp.name)/'reference-video.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:size=160x90:duration=2',
                        '-f','lavfi','-i','color=white:size=160x90:duration=2','-f','lavfi','-i','color=black:size=160x90:duration=2',
                        '-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]','-map','[v]',str(source)],check=True)
        asset=ingest(self.store,self.p['id'],source,'reference-video.mp4',kind='reference')
        result=sample_asset(self.store,self.p['id'],asset,threading.Event())
        self.assertEqual(len(result['detected_cuts']),2)
        self.assertAlmostEqual(result['reference_style']['shot_seconds'],2,delta=.1)

    def test_only_missing_asset_is_analyzed(self):
        del self.p['analysis']['b']
        self.store.save(self.p)
        def analyze_one(store,pid,use_model,cancel,progress,asset_ids):
            self.assertEqual(asset_ids,{'b'})
            p=store.load(pid);p['analysis']['b']={'mode':'signals','candidates':[{'start':0,'end':3,'score':1}]};store.save(p)
        with patch('loop_studio.providers.analyze',side_effect=analyze_one) as analysis:
            direct(self.store,self.p['id'],self.p,{'duration':6},threading.Event(),lambda _:None)
        analysis.assert_called_once()

    def test_short_highlight_becomes_preferred_length_valid_segment(self):
        self.p['analysis']['a']['candidates']=[{'start':1,'end':1.5,'score':1}]
        self.p['style']['shot_seconds']=1.25
        with patch('loop_studio.providers.model_json',return_value={'shots':[{'segment':0}]}):
            result=direct(self.store,self.p['id'],self.p,{'use_model':True,'duration':5},threading.Event(),lambda _:None)
        shot=result['timeline'][0]
        self.assertAlmostEqual(shot['end']-shot['start'],1.25)
        self.assertGreaterEqual(shot['start'],0)
        self.assertLessEqual(shot['end'],20)

    def test_unknown_segment_is_rejected(self):
        with patch('loop_studio.providers.model_json',return_value={'shots':[{'segment':999}]}):
            with self.assertRaisesRegex(ValueError,'segment IDs'):
                direct(self.store,self.p['id'],self.p,{'use_model':True},threading.Event(),lambda _:None)

    def test_full_model_draft_cannot_repeat_a_segment(self):
        with patch('loop_studio.providers.model_json',return_value={'shots':[{'segment':0},{'segment':0}]}):
            with self.assertRaisesRegex(ValueError,'repeats source footage'):
                direct(self.store,self.p['id'],self.p,{'use_model':True},threading.Event(),lambda _:None)

    def test_consecutive_source_shots_do_not_jump_backwards_unrequested(self):
        with patch('loop_studio.providers.model_json',return_value={'shots':[{'segment':1},{'segment':0}]}):
            with self.assertRaisesRegex(ValueError,'jump backwards'):
                direct(self.store,self.p['id'],self.p,{'use_model':True},threading.Event(),lambda _:None)
