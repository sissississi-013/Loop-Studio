"""Loopback-only HTTP server, bounded background jobs and range-served media."""
from __future__ import annotations
import argparse
import copy
import json
import mimetypes
import os
import re
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote
from .core import Store, Conflict, ident
from . import media


class Jobs:
    def __init__(self, root):
        self.path = Path(root) / 'jobs.json'
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.lock = threading.RLock()
        self.items = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.cancels = {}
        for job in self.items.values():
            if job['status'] in ('queued', 'running'):
                job.update(status='failed', message='Server restarted. Retry this operation; saved edits are intact.')
        self.save()

    def save(self):
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.items))
        tmp.replace(self.path)

    def submit(self, pid, name, fn, cleanup=None):
        with self.lock:
            if sum(j['status'] in ('queued', 'running') for j in self.items.values()) >= 12:
                raise ValueError('Job queue is full. Wait for current operations.')
            jid = ident()
            self.items[jid] = {'id': jid, 'project_id': pid, 'name': name, 'status': 'queued', 'message': 'Queued'}
            cancel = self.cancels[jid] = threading.Event()
            self.save()
        def progress(message):
            with self.lock:
                self.items[jid]['message'] = message
                self.save()
        def work():
            try:
                with self.lock:
                    self.items[jid]['status'] = 'running'
                    self.save()
                if cancel.is_set():
                    raise ValueError('Operation cancelled')
                result = fn(cancel, progress)
                with self.lock:
                    self.items[jid].update(status='completed', message='Ready', result=result)
            except Exception as exc:
                with self.lock:
                    self.items[jid].update(status='cancelled' if cancel.is_set() else 'failed', message=str(exc)[:1800])
            finally:
                if cleanup:
                    cleanup()
                with self.lock:
                    self.cancels.pop(jid, None)
                    self.save()
        self.pool.submit(work)
        return copy.deepcopy(self.items[jid])

    def cancel(self, jid):
        with self.lock:
            if jid in self.cancels:
                self.cancels[jid].set()
            return self.items[jid]

    def close(self):
        with self.lock:
            for event in self.cancels.values():
                event.set()
        self.pool.shutdown(wait=True, cancel_futures=False)


def make_server(root, port):
    store = Store(Path(root) / 'projects')
    jobs = Jobs(root)
    web = Path(__file__).parent / 'web'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # Never log query strings or media names.
            pass

        def safe_origin(self):
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if self.headers.get('Host') not in allowed:
                raise PermissionError('Invalid Host')
            origin = self.headers.get('Origin')
            if origin and origin not in {f'http://{h}' for h in allowed}:
                raise PermissionError('Cross-origin requests are not allowed')
            if self.headers.get('Sec-Fetch-Site') == 'cross-site':
                raise PermissionError('Cross-site requests are not allowed')

        def json(self, value, status=200):
            body = json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def body(self):
            if self.headers.get_content_type() != 'application/json':
                raise ValueError('Expected application/json')
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 2_000_000:
                raise ValueError('Invalid request length')
            return json.loads(self.rfile.read(length))

        def file(self, path):
            if not path.is_file():
                raise FileNotFoundError('File not found')
            size = path.stat().st_size
            start, end, status = 0, size - 1, 200
            requested = self.headers.get('Range')
            if requested:
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
                if not match or not any(match.groups()):
                    raise ValueError('Invalid byte range')
                first, last = match.groups()
                start = int(first) if first else max(0, size - int(last))
                end = min(size - 1, int(last)) if first and last else size - 1
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header('Content-Range', f'bytes */{size}')
                    self.end_headers()
                    return
                status = 206
            self.send_response(status)
            self.send_header('Content-Type', mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(end - start + 1))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; media-src 'self' blob:; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            if status == 206:
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.end_headers()
            with path.open('rb') as handle:
                handle.seek(start)
                remaining = end - start + 1
                while remaining:
                    block = handle.read(min(1024 * 1024, remaining))
                    if not block:
                        break
                    self.wfile.write(block)
                    remaining -= len(block)

        def do_GET(self):
            try:
                self.safe_origin()
                path = unquote(urlparse(self.path).path)
                parts = path.strip('/').split('/')
                if path == '/api/config':
                    from .providers import config
                    return self.json(config())
                if path == '/api/projects':
                    return self.json(store.list())
                if len(parts) == 3 and parts[:2] == ['api', 'projects']:
                    return self.json(store.load(parts[2]))
                if path == '/api/jobs':
                    with jobs.lock:
                        return self.json(list(jobs.items.values()))
                if len(parts) >= 4 and parts[0] == 'files':
                    base = store.directory(parts[1]).resolve()
                    target = (base / '/'.join(parts[2:])).resolve()
                    if not target.is_relative_to(base) or parts[2] not in ('media', 'exports', 'analysis'):
                        raise PermissionError('Invalid file path')
                    return self.file(target)
                target = (web / ('index.html' if path == '/' else path.lstrip('/'))).resolve()
                if not target.is_relative_to(web.resolve()):
                    raise PermissionError('Invalid file path')
                self.file(target)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as exc:
                self.error(exc)

        def error(self, exc):
            status = 409 if isinstance(exc, Conflict) else 403 if isinstance(exc, PermissionError) else 404 if isinstance(exc, (FileNotFoundError, KeyError)) else 400
            self.json({'error': str(exc)[:1800]}, status)

        def do_POST(self):
            try:
                self.safe_origin()
                path = urlparse(self.path).path
                parts = path.strip('/').split('/')
                if path == '/api/projects':
                    return self.json(store.create(self.body().get('name', 'Untitled film')), 201)
                if len(parts) == 4 and parts[:2] == ['api', 'jobs'] and parts[3] == 'cancel':
                    self.body()
                    return self.json(jobs.cancel(parts[2]))
                if len(parts) != 4 or parts[:2] != ['api', 'projects']:
                    raise ValueError('Unknown endpoint')
                pid, action = parts[2:]
                p = store.load(pid)
                if action == 'upload':
                    length = int(self.headers.get('Content-Length', 0))
                    if not 0 < length <= 1_000_000_000:
                        raise ValueError('Upload must be between 1 byte and 1 GB')
                    folder = store.directory(pid) / 'incoming'
                    folder.mkdir(exist_ok=True)
                    upload = folder / ident()
                    self.connection.settimeout(90)
                    try:
                        with upload.open('wb') as handle:
                            remaining = length
                            while remaining:
                                block = self.rfile.read(min(1024 * 1024, remaining))
                                if not block:
                                    raise ValueError('Upload interrupted')
                                handle.write(block)
                                remaining -= len(block)
                        name = unquote(self.headers.get('X-Filename', 'clip.mp4'))
                        kind = self.headers.get('X-Asset-Kind', 'clip')
                        if kind not in ('clip', 'reference'):
                            raise ValueError('Invalid asset kind')
                        def process(cancel, progress):
                            try:
                                progress('Making a full-duration preview; originals stay intact')
                                return media.ingest(store, pid, upload, name, cancel, kind)
                            finally:
                                upload.unlink(missing_ok=True)
                        return self.json(jobs.submit(pid, 'Import', process, lambda: upload.unlink(missing_ok=True)), 202)
                    except BaseException:
                        upload.unlink(missing_ok=True)
                        raise
                data = self.body()
                if action == 'edit':
                    return self.json(store.update(pid, data['version'], data['operation']))
                if action == 'export':
                    if data.get('version') != p['version']:
                        raise Conflict('Reload before exporting the latest edits')
                    return self.json(jobs.submit(pid, 'Preview' if data.get('preview') else 'Export',
                        lambda c, progress: media.export(store, pid, p, c, progress, bool(data.get('preview')))), 202)
                if action == 'analyze':
                    from .providers import analyze
                    return self.json(jobs.submit(pid, 'Analyze footage', lambda c, progress: analyze(store, pid, bool(data.get('use_model')), c, progress)), 202)
                if action == 'direct':
                    from .providers import direct
                    if data.get('version') != p['version']:
                        raise Conflict('Reload before requesting a draft')
                    return self.json(jobs.submit(pid, 'Draft edit', lambda c, progress: direct(store, pid, p, data, c, progress)), 202)
                if action == 'sample':
                    from .samples import sample
                    return self.json(jobs.submit(pid, 'Create sample footage', lambda c, progress: sample(store, pid, c, progress)), 202)
                raise ValueError('Unknown project action')
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as exc:
                self.error(exc)

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.jobs = jobs
    return server


def main():
    parser = argparse.ArgumentParser(description='Loop Studio local editor')
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--data', default=os.environ.get('LOOP_DATA_DIR', '.loop-studio'))
    args = parser.parse_args()
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        parser.error('Install FFmpeg and ffprobe first')
    server = make_server(args.data, args.port)
    print(f'Loop Studio ready at http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.jobs.close()


if __name__ == '__main__':
    main()
