# MVP acceptance report

September 13, 2026. This report distinguishes working implementation from output-quality claims.

## Workflow refinement after user feedback

The initial alpha was rejected as insufficient. The new process is **Make my film → watch/compare → revise → keep → export**, with cached analysis, reference processing, explicit style preservation, validated segment selection and bounded repair. Read [the actual review cases](WORKFLOW_REVIEW.md) for failures, measured timings and limits. Thirty-six tests pass locally for this pass; the older results below are historical. These checks do not establish creator satisfaction.

## Implemented workflow

Local import → full-duration proxy → timestamped candidate windows → brief-based proposal → review → editable timeline → original-source export. Manual editing does not need a model, account or paid service. The core and studio UI are MIT licensed.

- Originals remain byte-identical. Projects support ten source clips / ten minutes, plus three image/video references.
- Trim, split, reorder, remove, per-shot volume and captions; position/content locks; version conflicts; saved projects; 100-step undo/redo; corrected footage notes.
- Landscape/portrait/square 1080p, 30 fps H.264/AAC export; original audio, generated soundtrack, basic color looks, title typeface/placement/background. Preview renders the same edit at a lower resolution.
- Offline full-duration image-signal sampling; optional OpenAI-compatible vision endpoint. Configured local models default on; remote models require opting in. The choice is visible and remembered per endpoint.
- Reference color suggestions and scene-change-based shot-length estimates, both editable. Selected-shot revisions preserve every untargeted shot. Proposals do not replace the timeline until applied.
- Local sample onboarding, cancellable queued media work, restart status, media byte ranges, loopback binding and cross-origin/Host protection.

## Verification

Twenty-one tests pass locally and on [GitHub Linux CI](https://github.com/sissississi-013/Loop-Studio/actions/runs/34790627993) for code commit `bf87c1d`. The test suite covers original hash preservation; an export trimmed at 13–14.5 seconds from a 15-second source; audio presence and full decode; no accumulated audio padding across ten cuts; rotated footage; clip count/duration limits; split/undo; locks and conflicts; malformed model ranges; scoped revisions; original reference images; reference cut timing; corrected notes; HTTP byte ranges and access checks; queued cancellation cleanup; restart recovery.

A fresh isolated Python environment installed the package. Browser checks exercised sample creation, draft generation/application, locks, captions, a targeted shorter-shot revision, preview and a new 1920×1080 export. Reference analysis/application and saving a corrected footage description were also verified through the UI. The layout was inspected at the narrow in-app browser width. This is not a formal accessibility audit or an exhaustive browser/device matrix.

A local real-media edit with three historical research clips rendered to a 9.0-second 1920×1080 MP4 with audio. The opening frame was visually inspected. These source clips and outputs are kept outside Git; they are not part of the public sample pack. Procedural sample clips are test material, not an aesthetic showcase.

## Actual local-model checks

Using an already-installed Ollama `gemma4:12b` model, with reasoning disabled:

1. Three synthetic clips were described, and a blue → tan → colorful-pattern brief produced that exact order and a validated 15-second proposal. End-to-end analysis/direction took 205.25 seconds on this machine.
2. Three real clips produced the requested horse → person → bird order, in 112.61 seconds. **The model misidentified a black swan as a heron and described the person inaccurately.** Its explanation claimed nine seconds, while the actual validated proposal was eight seconds. The studio displays calculated duration independently and labels the model explanation for review. Editable footage notes can correct descriptions before subsequent direction.
3. An initial thinking-enabled request timed out without changing the edit. Static frames sometimes returned no semantic highlights; fallback timing is explicitly labeled as signal-based.

These are development checks, not accuracy estimates or competitive aesthetic benchmarks. No new training, paid model API calls or cloud GPU jobs were used in this product build. Remote-provider compatibility uses the same documented JSON/vision contract, but no paid remote endpoint was live-tested here.

## Boundaries before a broader launch

This is a functional local alpha. Models can misunderstand footage, and sampled stills do not provide complete motion or audio understanding. There is no speech transcription, automatic subject tracking/cropping, HDR mastering, multilayer timeline, multicam or advanced animation. Reference transfer covers a basic color look and estimated pace, not exact cinematography, typography or a guarantee of taste. Output uses fit-to-canvas framing and 30 fps, so some sources show bars or frame-rate conversion.

The server is for one local user, not a public multi-tenant service. Keep its process running for jobs; model cancellation can wait for an in-flight request timeout. Back up the complete data directory. Creator interviews, common-footage competitor comparisons and a real creator sample gallery remain follow-up product validation.
