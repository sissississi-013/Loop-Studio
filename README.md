# Loop Studio

An open-source, local-first video editor: bring a few clips, describe a direction, review a proposed cut, and make it yours.

**Status: active MVP development.** The manual editor and original-source export work; optional model direction is being validated. This is not yet a replacement for a full professional editor. See [implementation gates](BUILD_STATUS.md) and [the competitor research](research/market-and-mvp.md).

## Run locally

Requires Python 3.12+, FFmpeg and ffprobe. Install FFmpeg through your system package manager (`brew install ffmpeg` on macOS; `sudo apt install ffmpeg fonts-dejavu-core` on Debian/Ubuntu).

```sh
git clone https://github.com/sissississi-013/Loop-Studio.git
cd Loop-Studio
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
loop-studio
```

Open http://127.0.0.1:8766. No login, subscription, telemetry or model key is required for manual editing. Project files and media live in `.loop-studio/`, which is excluded from Git. Back up that entire folder to preserve projects and originals. Use `loop-studio --data /path/to/library --port 8766` to choose a location.

1. Choose **Try with sample footage** or add your own clips.
2. **Explore the footage** produces timestamped candidate windows.
3. Enter a brief and choose **Make a first cut**. Review the proposal before applying it.
4. Select timeline shots to trim, reorder, caption, adjust volume or lock them. Add an opening title, color look and optional procedural soundtrack.
5. **Render preview** shows the actual composition. **Export film** renders from original footage at 1080p. The source monitor displays a lightweight proxy, without finishing effects.

## Optional models

The server accepts an OpenAI-compatible chat-completions endpoint with image input. It does not require the OpenAI service or SDK. Configure a vision model before starting:

```sh
export LOOP_MODEL_URL=http://localhost:11434/v1
export LOOP_MODEL=qwen3-vl:8b
# For a remote provider, use its HTTPS /v1 base URL and set LOOP_MODEL_KEY.
loop-studio
```

Install and run your chosen model server separately. For Ollama, see its [documented vision-compatible endpoint](https://docs.ollama.com/api/openai-compatibility). Check the model license and available memory yourself; Loop Studio does not download model weights automatically.

Enable **Use my vision model** in the studio to opt in. Sampled contact sheets, footage descriptions and the brief may be sent to the configured endpoint; a remote endpoint means these leave your computer. Keys stay in the server environment and are never saved in project files. Disabled means no model network requests.

Offline sampling evaluates brightness, edge detail and frame differences across the full duration. It **does not understand people, speech, story or aesthetics**. Offline drafting chooses one candidate per clip and recognizes fast/quick/energetic as pace hints. Model mode adds sampled visual descriptions and brief-based proposals; still-frame sampling cannot establish everything that happens between frames or in the audio.

## Current boundaries

- Ten source clips and ten minutes of source footage per project; 1 GB per upload. Draft length choices are suggestions; sparse or locked footage can produce a different duration.
- Landscape 1920×1080, portrait 1080×1920 and square 1080×1080, 30 fps, H.264/AAC. Footage fits inside the chosen canvas; automatic subject crops, HDR mastering and color-managed professional delivery are not implemented.
- Cuts, per-shot captions, an opening title, basic color looks and procedural soundtracks. No speech transcription, multilayer compositing, multicam, advanced transitions or keyframes yet.
- Reference videos can suggest an editable basic color look; exact pacing, typography and aesthetic transfer remain development work.
- Locks preserve shot contents and timeline position. Undo/redo retains the latest 100 edits. Exports save their timeline snapshot and remain associated with the version that produced them.
- Jobs run one at a time, can be cancelled and report interrupted work after a server restart. Keep the local server running for jobs to finish.
- This is a loopback-only, single-user development server, not a hardened multi-user hosting service.
- Sample footage is generated test material, not evidence of aesthetic quality. Creator evaluation and common-footage competitor benchmarks have not been performed.

## Development

```sh
python -m unittest discover -s tests -v
```

The core has no model-service dependency. Pillow renders text overlays so it also works with FFmpeg builds lacking the `drawtext` filter. Font files are read from the host and not redistributed. FFmpeg is an external dependency with its own licensing; it is not bundled here.

MIT-licensed project code. Historical CutLoop research was kept separate from this clean product repository; no private clips, credentials or training artifacts are included.
