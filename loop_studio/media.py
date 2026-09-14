"""FFmpeg media I/O. Original bytes are immutable; proxies never feed exports."""
from __future__ import annotations
import hashlib
import json
import math
import shutil
import subprocess
import time
from pathlib import Path
from .core import ident, validate


def run(args, cancel=None, timeout=1800, capture_log=False):
    # Capture to a temporary file to avoid a full stderr pipe deadlocking FFmpeg.
    import tempfile
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=errors)
        start = time.monotonic()
        while process.poll() is None:
            if (cancel and cancel.is_set()) or time.monotonic() - start > timeout:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise ValueError("Operation cancelled" if cancel and cancel.is_set() else "Media operation timed out")
            time.sleep(.05)
        errors.seek(0)
        if process.returncode:
            raise ValueError("Media processing failed: " + errors.read().decode(errors="replace")[-1400:])
        return errors.read() if capture_log else b""


def probe(path):
    data = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], timeout=30))
    videos = [s for s in data["streams"] if s["codec_type"] == "video"]
    if not videos:
        raise ValueError("File has no video stream")
    video = videos[0]
    duration = float(data.get("format", {}).get("duration", video.get("duration", 0)))
    if not math.isfinite(duration) or duration < .25:
        raise ValueError("Could not read a valid video duration")
    rotation = float(video.get("tags", {}).get("rotate", 0))
    for side in video.get("side_data_list", []):
        if "rotation" in side:
            rotation = float(side["rotation"])
    width, height = video["width"], video["height"]
    if round(rotation) % 180:
        width, height = height, width
    return {"duration": duration, "width": width, "height": height,
            "audio": any(s["codec_type"] == "audio" for s in data["streams"])}


def ingest(store, pid, upload, name, cancel=None, kind="clip"):
    still = False
    if kind == "reference":
        from PIL import Image
        try:
            with Image.open(upload) as picture:
                if picture.format in ("JPEG", "PNG", "WEBP"):
                    if picture.width * picture.height > 40_000_000:
                        raise ValueError("Reference images are limited to 40 megapixels")
                    meta = {"duration": 4.0, "width": picture.width, "height": picture.height, "audio": False}
                    still = True
        except (OSError, Image.DecompressionBombError):
            pass
    if not still:
        meta = probe(upload)
    if meta["duration"] > 600:
        raise ValueError("A video must be at most ten minutes")
    aid = ident()
    directory = store.directory(pid) / "media" / aid
    directory.mkdir(parents=True)
    original = directory / "original"
    try:
        shutil.move(str(upload), original)
        with original.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        source = original
        if still:
            from PIL import Image, ImageOps
            source = directory / "reference.png"
            with Image.open(original) as picture:
                ImageOps.exif_transpose(picture).convert("RGB").save(source)
        inputs = ["-loop", "1", "-i", str(source), "-t", "4"] if still else ["-i", str(source)]
        run(["ffmpeg", "-v", "error", "-y", *inputs, "-map", "0:v:0", "-map", "0:a:0?",
             "-vf", "scale=640:640:force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1,fps=24",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "25", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-ac", "2", "-ar", "48000", "-movflags", "+faststart", str(directory / "proxy.mp4")], cancel)
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(min(meta["duration"] / 3, 2)), "-i", str(directory / "proxy.mp4"),
             "-frames:v", "1", "-vf", "scale=400:-2", str(directory / "poster.jpg")], cancel)
        with store.lock:
            p = store.load(pid)
            asset = {"id": aid, "name": Path(name).name[:160], "kind": kind, "still": still, **meta, "sha256": digest,
                     "original": f"media/{aid}/original", "proxy": f"media/{aid}/proxy.mp4", "poster": f"media/{aid}/poster.jpg"}
            p["assets"][aid] = asset
            validate(p)
            p["version"] += 1
            store.save(p)
        return asset
    except BaseException:
        shutil.rmtree(directory, ignore_errors=True)
        raise


SIZES = {"landscape": (1920, 1080), "portrait": (1080, 1920), "square": (1080, 1080)}
LOOKS = {"natural": "null", "warm": "colorbalance=rs=.06:bs=-.04,eq=saturation=1.08",
         "cool": "colorbalance=rs=-.03:bs=.06", "mono": "hue=s=0"}


def font_path(family="sans"):
    # Explicit system fallback; no font files are redistributed.
    if family != "sans":
        choices = {"serif": ("/System/Library/Fonts/Supplemental/Georgia.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"),
                   "mono": ("/System/Library/Fonts/Menlo.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")}
        for path in choices.get(family, ()):
            if Path(path).exists():
                return path
    for candidate in ("/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                      "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"):
        if Path(candidate).exists():
            return candidate
    return None


def export(store, pid, project, cancel=None, progress=lambda _: None, preview=False, record=True):
    validate(project)
    if not project["timeline"]:
        raise ValueError("Add at least one shot to the timeline")
    eid = ident()
    directory = store.directory(pid) / "exports" / eid
    directory.mkdir(parents=True)
    width, height = SIZES[project["style"]["aspect"]]
    if preview:
        width, height = width // 3 * 2 // 2, height // 3 * 2 // 2
        width -= width % 2
        height -= height % 2
    fps = 30
    style = project["style"]
    font = font_path()
    paths = []
    thumbnails = []
    duration = 0
    timeline_time = 0
    try:
        for i, shot in enumerate(project["timeline"]):
            progress(f"Rendering shot {i + 1} of {len(project['timeline'])}")
            asset = project["assets"][shot["asset_id"]]
            source = store.directory(pid) / asset["original"]
            timeline_time += shot["end"] - shot["start"]
            seconds = (round(timeline_time * fps) - round(duration * fps)) / fps
            duration += seconds
            seek = shot["start"]
            if style.get("ascii_mode", "off") != "off":
                from .ascii_effect import render_ascii
                progress(f"Drawing ASCII frames for shot {i+1}")
                ascii_path = directory / f"ascii-{i}.mov"
                render_ascii(source, ascii_path, seek, seconds, style.get("ascii_columns",80), style['ascii_mode']=='green', cancel, asset['width']/asset['height'])
                source, seek = ascii_path, 0
            out = directory / f"shot-{i}.mov"
            filters = [f"scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2",
                       f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black", "setsar=1", f"fps={fps}", LOOKS[style["look"]]]
            title = style["title"] if i == 0 else ""
            caption = shot.get("caption", "")
            args = ["ffmpeg", "-v", "error", "-y", "-ss", str(seek), "-i", str(source)]
            if not asset["audio"]:
                args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
            overlay_index = 1 if asset["audio"] else 2
            if title or caption:
                overlay = directory / f"overlay-{i}.png"
                text_overlay(overlay, width, height, title, caption, style["title_size"], SIZES[style["aspect"]][0], style)
                args += ["-i", str(overlay)]
                video_args = ["-filter_complex", f"[0:v]{','.join(filters)}[base];[base][{overlay_index}:v]overlay=0:0:format=auto[v]", "-map", "[v]"]
            else:
                video_args = ["-vf", ",".join(filters), "-map", "0:v:0"]
            args += ["-t", str(seconds), *video_args, "-map", "0:a:0" if asset["audio"] else "1:a:0",
                     "-af", f"aresample=48000,apad,atrim=duration={seconds},asetpts=PTS-STARTPTS,volume={style['source_volume'] * shot.get('volume', 1)}",
                     "-c:v", "libx264", "-preset", "veryfast" if preview else "fast", "-crf", "24" if preview else "18",
                     "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(out)]
            run(args, cancel)
            paths.append(out)
            thumbnail = directory / f"shot-{i}.jpg"
            run(["ffmpeg", "-v", "error", "-y", "-ss", str(seconds/2), "-i", str(out), "-frames:v", "1", "-vf", "scale=240:-2", str(thumbnail)], cancel)
            thumbnails.append(f"exports/{eid}/shot-{i}.jpg")
        listing = directory / "concat.txt"
        listing.write_text("\n".join(f"file '{p.name}'" for p in paths))
        joined = directory / "joined.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(joined)], cancel)
        final = directory / "film.mp4"
        if style["music"] != "none":
            from .soundtrack import compose
            soundtrack = directory / "soundtrack.wav"
            compose(soundtrack, duration, style["music"], cancel)
            run(["ffmpeg", "-v", "error", "-y", "-i", str(joined), "-i", str(soundtrack),
                 "-filter_complex", f"[1:a]volume={style['music_volume']},afade=t=in:d=0.4,afade=t=out:st={max(0, duration-.8)}:d=0.8[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:latency=1[a]",
                 "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final)], cancel)
        else:
            joined.replace(final)
        info = probe(final)
        result = {"id": eid, "path": f"exports/{eid}/film.mp4", "version": project["version"], "preview": preview, "thumbnails": thumbnails, **info}
        (directory / "timeline.json").write_text(json.dumps(project, indent=2))
        if record:
            with store.lock:
                current = store.load(pid)
                current["exports"].append(result)
                store.save(current)
        for path in paths:
            path.unlink()
        for temporary in directory.glob("ascii-*.mov"):
            temporary.unlink()
        if joined.exists():
            joined.unlink()
        return result
    except BaseException:
        shutil.rmtree(directory, ignore_errors=True)
        raise


def text_overlay(path, width, height, title, caption, title_size, base_width, style=None):
    from PIL import Image, ImageDraw, ImageFont
    style = style or {}
    canvas = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(canvas)
    for text, is_title, size in ((title, True, title_size), (caption, False, 42)):
        if not text:
            continue
        font = font_path(style.get("font", "sans") if is_title else "sans")
        if not font:
            raise ValueError("Install DejaVu fonts or Arial to render text")
        size = max(10, round(size * width / base_width))
        while True:
            face = ImageFont.truetype(font, size)
            lines, line = [], ""
            for char in text:
                if char == "\n" or (line and draw.textlength(line + char, font=face) > width * .84):
                    lines.append(line)
                    line = "" if char == "\n" else char
                else:
                    line += char
            lines.append(line)
            content = "\n".join(lines)
            box = draw.multiline_textbbox((0, 0), content, font=face, spacing=4)
            text_width, text_height = box[2] - box[0], box[3] - box[1]
            if text_height <= height * .28 or size <= 10:
                break
            size -= 1
        position = style.get("title_position", "top-left") if is_title else "bottom-center"
        x = width * .08 if position.endswith("left") else (width - text_width) / 2
        y = height * .13 if position.startswith("top") else height * .88 - text_height
        align = "left" if position.endswith("left") else "center"
        if not is_title or style.get("title_background", False):
            draw.rounded_rectangle((x-10, y-6, x+text_width+10, y+text_height+10), radius=5, fill=(0, 0, 0, 95))
        draw.multiline_text((x-box[0]+1, y-box[1]+2), content, font=face, fill=(0,0,0,150), align=align, spacing=4)
        draw.multiline_text((x-box[0], y-box[1]), content, font=face, fill="white", align=align, spacing=4)
    canvas.save(path)
