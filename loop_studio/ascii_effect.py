"""Streaming, local ASCII video conversion. Originals never change."""
import subprocess
from PIL import Image, ImageDraw, ImageFont


def render_ascii(source, target, start, duration, columns, green=False, cancel=None, aspect=16/9):
    columns = int(columns)
    rows = max(8, min(240, round(columns * (8/14) / aspect)))
    font = ImageFont.load_default(size=12)
    cell_w, cell_h = 8, 14
    width, height = columns*cell_w, rows*cell_h
    ramp = ' .:-=+*#%@'
    glyphs = []
    for char in ramp:
        tile=Image.new('RGB',(cell_w,cell_h),(5,7,6))
        ImageDraw.Draw(tile).text((0,0),char,font=font,fill=(172,255,190) if green else (235,239,231))
        glyphs.append(tile)
    decode = subprocess.Popen(['ffmpeg','-v','error','-ss',str(start),'-i',str(source),'-t',str(duration),'-vf',f'fps=30,scale={columns}:{rows}', '-f','rawvideo','-pix_fmt','gray','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    encode = subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{width}x{height}','-r','30','-i','pipe:0','-ss',str(start),'-i',str(source),'-t',str(duration),'-map','0:v','-map','1:a?','-c:v','libx264','-preset','ultrafast','-crf','16','-c:a','pcm_s16le',str(target)],stdin=subprocess.PIPE,stderr=subprocess.DEVNULL)
    try:
        while True:
            if cancel and cancel.is_set():raise ValueError('Operation cancelled')
            raw=decode.stdout.read(columns*rows)
            if not raw:break
            if len(raw)!=columns*rows:raise ValueError('Incomplete ASCII video frame')
            frame=Image.new('RGB',(width,height))
            for i,value in enumerate(raw):frame.paste(glyphs[min(9,value*10//256)],((i%columns)*cell_w,(i//columns)*cell_h))
            encode.stdin.write(frame.tobytes())
        encode.stdin.close()
        if decode.wait(timeout=20) or encode.wait(timeout=30):raise ValueError('ASCII rendering failed')
    finally:
        for process in (decode,encode):
            if process.poll() is None:process.kill()
            process.wait()
        decode.stdout.close()
        if not encode.stdin.closed:encode.stdin.close()
