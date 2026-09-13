import tempfile
import unittest
from loop_studio.core import Store, Conflict


class TimelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        self.p = self.store.create()
        self.p['assets']['a'] = {'id': 'a', 'duration': 20}
        self.store.save(self.p)

    def edit(self, **operation):
        self.p = self.store.update(self.p['id'], self.p['version'], operation)
        return self.p

    def test_trim_persistence_undo_and_conflict(self):
        self.edit(op='add', asset_id='a', start=13, end=17)
        shot = self.p['timeline'][0]['id']
        self.edit(op='shot', shot_id=shot, changes={'start': 14})
        reloaded = Store(self.temp.name).load(self.p['id'])
        self.assertEqual(reloaded['timeline'][0]['start'], 14)
        with self.assertRaises(Conflict):
            self.store.update(self.p['id'], 0, {'op': 'undo'})
        self.edit(op='undo')
        self.assertEqual(self.p['timeline'][0]['start'], 13)
        self.edit(op='redo')
        self.assertEqual(self.p['timeline'][0]['start'], 14)

    def test_lock_protects_contents_and_position(self):
        self.edit(op='add', asset_id='a')
        self.edit(op='add', asset_id='a')
        first, second = self.p['timeline']
        self.edit(op='shot', shot_id=first['id'], changes={'locked': True})
        for op in ({'op': 'remove', 'shot_id': first['id']},
                   {'op': 'move', 'shot_id': second['id'], 'index': 0},
                   {'op': 'shot', 'shot_id': first['id'], 'changes': {'end': 1}},
                   {'op': 'proposal', 'timeline': []}):
            with self.assertRaises(ValueError):
                self.store.update(self.p['id'], self.p['version'], op)
        self.edit(op='shot', shot_id=first['id'], changes={'locked': False})
        self.edit(op='remove', shot_id=first['id'])

    def test_bad_trim_is_atomic(self):
        self.edit(op='add', asset_id='a')
        original = self.store.load(self.p['id'])
        for start in (21, -1, float('nan')):
            with self.assertRaises(ValueError):
                self.edit(op='shot', shot_id=self.p['timeline'][0]['id'], changes={'start': start})
        self.assertEqual(self.store.load(self.p['id']), original)

    def test_split_preserves_source_ranges_and_undo(self):
        self.edit(op='add', asset_id='a', start=10, end=18)
        self.edit(op='split',shot_id=self.p['timeline'][0]['id'],at=13)
        self.assertEqual([(s['start'],s['end']) for s in self.p['timeline']],[(10,13),(13,18)])
        self.edit(op='undo')
        self.assertEqual([(s['start'],s['end']) for s in self.p['timeline']],[(10,18)])

    def test_source_count_and_duration_limits(self):
        from loop_studio.core import validate
        self.p['assets']={str(i):{'id':str(i),'duration':60} for i in range(10)}
        validate(self.p)
        self.p['assets']['11']={'id':'11','duration':1}
        with self.assertRaises(ValueError):validate(self.p)
        del self.p['assets']['11']
        self.p['assets']['0']['duration']=61
        with self.assertRaises(ValueError):validate(self.p)
