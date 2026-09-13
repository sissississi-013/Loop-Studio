import json
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from loop_studio.server import make_server, Jobs


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.server=make_server(self.tmp.name,0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown();self.server.server_close();self.server.jobs.close();self.thread.join()

    def request(self,path,data=None,headers={}):
        if data is not None:
            headers={'Content-Type':'application/json',**headers};data=json.dumps(data).encode()
        return urllib.request.urlopen(urllib.request.Request(self.base+path,data,headers),timeout=5)

    def test_origin_host_and_traversal(self):
        for headers in ({'Origin':'https://evil.example'},{'Host':'evil.example'},{'Sec-Fetch-Site':'cross-site'}):
            with self.assertRaises(urllib.error.HTTPError) as err:
                self.request('/api/projects',{'name':'forbidden'},headers)
            self.assertEqual(err.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError):self.request('/%2e%2e/AGENTS.md')
        with self.request('/api/projects') as response:self.assertEqual(json.load(response),[])

    def test_range_and_conflict(self):
        with self.request('/api/projects',{'name':'HTTP'}) as response:p=json.load(response)
        asset=Path(self.tmp.name)/'projects'/p['id']/'media'/'test.bin';asset.parent.mkdir();asset.write_bytes(b'0123456789')
        with self.request(f"/files/{p['id']}/media/test.bin",headers={'Range':'bytes=2-5'}) as response:
            self.assertEqual(response.status,206);self.assertEqual(response.read(),b'2345')
        with self.request(f"/files/{p['id']}/media/test.bin",headers={'Range':'bytes=-3'}) as response:self.assertEqual(response.read(),b'789')
        with self.request(f"/api/projects/{p['id']}/edit",{'version':0,'operation':{'op':'settings','name':'Edited'}}):pass
        with self.assertRaises(urllib.error.HTTPError) as err:
            self.request(f"/api/projects/{p['id']}/edit",{'version':0,'operation':{'op':'undo'}})
        self.assertEqual(err.exception.code,409)

    def test_restart_marks_interrupted_job(self):
        root=Path(self.tmp.name)/'separate';root.mkdir()
        (root/'jobs.json').write_text(json.dumps({'j':{'status':'running','message':'Working'}}))
        jobs=Jobs(root)
        try:self.assertEqual(jobs.items['j']['status'],'failed')
        finally:jobs.close()
