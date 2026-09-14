# Loop Studio

An open-source, local-first video editor: bring a few clips, describe a direction, review a proposed cut, and make it yours.

**Status: active MVP development.** The manual editor, original-source export and optional local vision direction have passed initial integration checks. This is not yet a replacement for a full professional editor. See [implementation gates](BUILD_STATUS.md) and [the competitor research](research/market-and-mvp.md).

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

Open http://127.0.0.1:8766 for the landing page, or http://127.0.0.1:8766/studio to edit. No login, subscription, telemetry or model key is required for manual editing. Project files and media live in `.loop-studio/`, which is excluded from Git. Back up that entire folder to preserve projects and originals. Use `loop-studio --data /path/to/library --port 8766` to choose a location.

1. Add your clips, or choose **Try with sample footage** to explore the controls.
2. Describe your film, optionally choose a mood or add a reference, then press **Make my film**. It analyzes missing footage, plans the cut and renders a playable draft in one job.
3. Watch the draft and **Compare current cut**. The review shows actual shot thumbnails, calculated length and repeated-footage warnings. Ask for a change and preview the revision before choosing **Keep this cut**.
4. Trim, reorder, caption or lock individual shots. Expand **The finishing touches** to adjust titles, color, typography and the original procedural music bed.
5. **Export film** saves pending form edits and renders from original footage at 1080p. Your saved edit stays intact while you explore draft alternatives; keeping a draft is undoable.

## Interface and ASCII

The landing page has an animated character orbit and a **Character lab** with Orbit/Wave modes, motion controls, density adjustment and downloadable text frames. Reduced-motion preferences are respected. Its dark, restrained visual direction takes inspiration from [Moonshot](https://www.moonshot.ai/), with original Loop artwork and branding.

The editor uses a media library, central viewer, Director/Inspector/ASCII tabs and a persistent timeline. Drag shots to reorder, change timeline zoom, click the ruler to seek, or use the Inspector for exact trims, captions and locks. Space plays/pauses outside form controls. The audio lane describes the current source/music mix; it is not a separate editable multitrack audio system.

In the **ASCII** tab, choose **Paper terminal** or **Phosphor**, adjust character columns, and click **Preview treatment**. The whole film is converted frame by frame to characters, with original audio, titles and captions composed into the result. The effect is included in 1080p exports, saved per project and undoable. Choose **Off** to restore normal footage. Rendering is local and does not require a model or a new dependency beyond Pillow and FFmpeg.

## Optional models

The server accepts an OpenAI-compatible chat-completions endpoint with image input. It does not require the OpenAI service or SDK. Configure a vision model before starting:

```sh
export LOOP_MODEL_URL=http://localhost:11434/v1
export LOOP_MODEL=qwen3-vl:8b
# Optional for thinking models when supported by your endpoint:
# export LOOP_MODEL_REASONING=none
# Optional: a faster text-only model for planning, already installed in your server:
# export LOOP_PLANNER_MODEL=your-text-model
# For a remote provider, use its HTTPS /v1 base URL and set LOOP_MODEL_KEY.
loop-studio
```

Install and run your chosen model server separately. For Ollama, see its [documented vision-compatible endpoint](https://docs.ollama.com/api/openai-compatibility). Check the model license and available memory yourself; Loop Studio does not download model weights automatically.

**Use local / connected vision director** defaults on for a configured loopback endpoint and off for a remote endpoint. Your choice is remembered for that endpoint. Sampled contact sheets, footage descriptions and the brief may be sent to the configured endpoint; a remote endpoint means these leave your computer. Keys stay in the server environment and are never saved in project files. Disabled means no model network requests.

Offline sampling evaluates brightness, edge detail and frame differences across the full duration. It **does not understand people, speech, story or aesthetics**. Offline drafting selects non-overlapping scored windows from available cached analysis and supports basic pace hints. Offline revisions support shorter, longer, mute and reverse order; unsupported story instructions produce a clear error. Model mode adds sampled visual descriptions and brief-based proposals. You can correct footage notes before drafting; still-frame sampling cannot establish everything that happens between frames or in the audio.

## Current boundaries

- Ten source clips and ten minutes of source footage per project; 1 GB per upload. Draft length choices are suggestions; sparse or locked footage can produce a different duration.
- Landscape 1920×1080, portrait 1080×1920 and square 1080×1080, 30 fps, H.264/AAC. Footage fits inside the chosen canvas; automatic subject crops, HDR mastering and color-managed professional delivery are not implemented.
- Cuts, per-shot captions, an opening title, basic color looks and procedural soundtracks. No speech transcription, multilayer compositing, multicam, advanced transitions or keyframes yet.
- Up to three reference images/videos can suggest an editable basic color look. Reference videos also estimate shot length from scene changes; exact typography and aesthetic transfer remain development work.
- Locks preserve shot contents and timeline position. Undo/redo retains the latest 100 edits. Exports save their timeline snapshot and remain associated with the version that produced them.
- Jobs show progress, reject duplicate draft requests for the same project, run one at a time, can be cancelled and report interrupted work after a server restart. Keep the local server running for jobs to finish.
- This is a loopback-only, single-user development server, not a hardened multi-user hosting service.
- Sample footage is generated test material, not evidence of aesthetic quality. Creator evaluation and common-footage competitor benchmarks have not been performed. See [the acceptance report](ACCEPTANCE.md) for measured checks and model errors.

## Development

```sh
python -m unittest discover -s tests -v
```

The core has no model-service dependency. Pillow renders text overlays so it also works with FFmpeg builds lacking the `drawtext` filter. Font files are read from the host and not redistributed. FFmpeg is an external dependency with its own licensing; it is not bundled here.

MIT-licensed project code. Historical CutLoop research was kept separate from this clean product repository; no private clips, credentials or training artifacts are included.
