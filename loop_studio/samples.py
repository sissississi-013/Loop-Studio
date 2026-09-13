"""Procedural onboarding clips, generated locally; no downloaded assets."""
from .media import run, ingest


def sample(store, pid, cancel, progress):
    p = store.load(pid)
    if p['assets']:
        raise ValueError('Create a fresh project for the sample')
    folder = store.directory(pid) / 'incoming'
    folder.mkdir(exist_ok=True)
    sources = [('Opening — color study', 'testsrc2=size=640x360:rate=24:duration=8', 220),
               ('Middle — soft blue', 'color=c=0x809ab2:size=640x360:rate=24:duration=8', 277),
               ('Closing — warm light', 'color=c=0xcbb197:size=640x360:rate=24:duration=8', 330)]
    for index, (name, source, frequency) in enumerate(sources):
        progress(f'Generating sample {index+1}/3')
        upload = folder / f'sample-{index}.mp4'
        try:
            run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', source, '-f', 'lavfi', '-i', f'sine=frequency={frequency}:duration=8',
                 '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(upload)], cancel)
            ingest(store, pid, upload, name+'.mp4', cancel)
        finally:
            upload.unlink(missing_ok=True)
    return {'clips': 3, 'note': 'Synthetic test footage for learning controls, not an aesthetic showcase.'}
