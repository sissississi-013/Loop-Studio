import copy
import tempfile
import threading
import unittest
from unittest.mock import patch
from loop_studio.core import Store, Conflict
from loop_studio.workflow import make_film, accept_film, revise_offline, review


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(self.tmp.name);self.p=self.store.create()
        self.p['assets']={'a':{'id':'a','duration':12},'b':{'id':'b','duration':12}}
        self.p['analysis']={k:{'mode':'signals','description':'Fixture','candidates':[{'start':0,'end':3,'score':1}]} for k in self.p['assets']}
        self.store.save(self.p)
        for aid in ['a','b']:
            self.p=self.store.update(self.p['id'],self.p['version'],{'op':'add','asset_id':aid,'start':0,'end':3})

    def test_rendered_proposal_leaves_edit_untouched_until_kept(self):
        before=copy.deepcopy(self.p)
        with patch('loop_studio.workflow.export',return_value={'path':'exports/test/film.mp4','duration':6,'thumbnails':[]}) as render:
            result=make_film(self.store,self.p['id'],self.p,{'duration':6},threading.Event(),lambda _:None)
        self.assertEqual(self.store.load(self.p['id']),before)
        self.assertFalse(render.call_args.kwargs['record'])
        self.assertTrue(result['preview'])
        kept=accept_film(self.store,self.p['id'],self.p['version'],result)
        self.assertEqual(kept['timeline'],result['timeline'])
        self.assertEqual(kept['accepted_preview']['version'],kept['version'])
        with self.assertRaises(Conflict):accept_film(self.store,self.p['id'],self.p['version'],result)

    def test_shorten_opening_preserves_rest_of_draft(self):
        result=revise_offline(self.p,{'feedback':'Make the opening shorter'})
        self.assertAlmostEqual(result['timeline'][0]['end'],2.1)
        self.assertEqual(result['timeline'][1],self.p['timeline'][1])
        self.assertEqual(self.store.load(self.p['id']),self.p)

    def test_unsupported_offline_revision_is_not_silently_ignored(self):
        with self.assertRaisesRegex(ValueError,'Enable your vision model'):
            revise_offline(self.p,{'feedback':'End with a sunset'})

    def test_review_reports_measured_duration_and_repeated_footage(self):
        result=review(self.p,[self.p['timeline'][0],self.p['timeline'][0]],30)
        self.assertEqual(result['duration'],6)
        self.assertEqual(len(result['notes']),2)

    def test_brief_style_is_previewed_then_accepted_atomically(self):
        with patch('loop_studio.workflow.export',return_value={'path':'exports/test/film.mp4'}) as render:
            result=make_film(self.store,self.p['id'],self.p,{'duration':6,'brief':'An energetic music video'},threading.Event(),lambda _:None)
        self.assertEqual(result['style']['music'],'pulse')
        self.assertEqual(self.store.load(self.p['id'])['style']['music'],'none')
        kept=accept_film(self.store,self.p['id'],self.p['version'],result)
        self.assertEqual(kept['style']['music'],'pulse')
        undone=self.store.update(kept['id'],kept['version'],{'op':'undo'})
        self.assertEqual(undone['style'],self.p['style'])

    def test_manual_preset_adjustments_are_respected(self):
        self.p['style'].update(font='serif',music='pulse')
        with patch('loop_studio.workflow.export',return_value={'path':'exports/test/film.mp4'}):
            result=make_film(self.store,self.p['id'],self.p,{'duration':6,'mood':'bright'},threading.Event(),lambda _:None)
        self.assertEqual(result['style']['font'],'serif')

    def test_duration_budget_trims_final_shot_without_touching_saved_edit(self):
        proposal={'version':self.p['version'],'timeline':copy.deepcopy(self.p['timeline']),'mode':'model','rationale':'test'}
        with patch('loop_studio.workflow.direct',return_value=proposal), patch('loop_studio.workflow.export',return_value={'path':'test.mp4'}):
            result=make_film(self.store,self.p['id'],self.p,{'duration':5},threading.Event(),lambda _:None)
        self.assertEqual(result['duration'],5)
        self.assertEqual(result['timeline'][1]['end'],2)
        self.assertEqual(self.store.load(self.p['id']),self.p)

    def test_invalid_plan_gets_exactly_one_repair(self):
        from loop_studio.providers import InvalidProposal
        with patch('loop_studio.workflow.direct',side_effect=InvalidProposal('invalid segment',{'shots':[]})) as planner:
            with self.assertRaises(InvalidProposal):
                make_film(self.store,self.p['id'],self.p,{'duration':6},threading.Event(),lambda _:None)
        self.assertEqual(planner.call_count,2)
        self.assertEqual(planner.call_args.args[3]['repair']['error'],'invalid segment')
        self.assertEqual(self.store.load(self.p['id']),self.p)

    def test_explicit_style_survives_new_brief_and_reload(self):
        self.p=self.store.update(self.p['id'],self.p['version'],{'op':'settings','style':{'music':'none','shot_seconds':4},'explicit_style_keys':['music','shot_seconds']})
        self.p=self.store.load(self.p['id'])
        with patch('loop_studio.workflow.export',return_value={'path':'test.mp4'}):
            result=make_film(self.store,self.p['id'],self.p,{'duration':6,'brief':'An energetic music video'},threading.Event(),lambda _:None)
        self.assertEqual(result['style']['music'],'none')
        self.assertEqual(result['style']['shot_seconds'],4)

    def test_reference_is_read_inside_single_action(self):
        self.p['assets']['ref']={'id':'ref','kind':'reference','duration':6}
        self.store.save(self.p)
        def analyze_reference(store,pid,use_model,cancel,progress,asset_ids):
            self.assertEqual(asset_ids,{'ref'})
            p=store.load(pid);p['analysis']['ref']={'reference_style':{'look':'mono','shot_seconds':2}};store.save(p)
        with patch('loop_studio.workflow.analyze',side_effect=analyze_reference), patch('loop_studio.workflow.export',return_value={'path':'test.mp4'}):
            result=make_film(self.store,self.p['id'],self.p,{'duration':6},threading.Event(),lambda _:None)
        self.assertEqual(result['style']['shot_seconds'],2)
        self.assertEqual(result['style']['look'],'mono')

    def test_revision_keeps_unaccepted_draft_finishing(self):
        with patch('loop_studio.workflow.export',return_value={'path':'test.mp4'}):
            result=make_film(self.store,self.p['id'],self.p,{'duration':6,'draft_timeline':self.p['timeline'],'draft_style':{'look':'mono','music':'pulse'},'feedback':'Make the opening shorter','brief':'energetic music video'},threading.Event(),lambda _:None)
        self.assertEqual(result['style']['look'],'mono')
        self.assertEqual(result['style']['music'],'pulse')
