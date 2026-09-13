# Implementation gates

Status: active build. This is a new product checkout, not the completed hackathon prototype.

- [ ] G1 — Full-duration import: up to ten clips / ten minutes; original bytes retained, separate full-duration proxies, rotation/audio handling, persistent projects.
- [ ] G2 — One editable timeline: trim, reorder, remove, locks, undo/redo, optimistic conflict protection and recovery after restart.
- [ ] G3 — Original-source 1080p export: aspect ratios, soundtrack/source audio, typography/captions, consistent preview/export, cancellation and errors.
- [ ] G4 — Footage analysis and direction: full-duration candidate windows; timestamped model descriptions/highlights through a pluggable provider; local offline fallback explicitly labeled; editable proposal from a natural-language brief.
- [ ] G5 — References and revisions: optional reference-derived editable style, targeted changes preserve locked shots, clear model and privacy controls.
- [ ] G6 — Usable studio: sample onboarding without login or payment, upload → brief → draft → adjust → export; manual workflow fully functional without a model.
- [ ] G7 — Release checks: automated integration tests, real media decode and audio checks, browser workflow, accessible layout, reproducible setup, license, limitations, repository updated.

Human creator validation and competitive aesthetic benchmarks are follow-up research, not implementation gates that automated tests can satisfy.

## Recovery

Repository: /Users/sissi/Loop-Studio. Continue the first unfinished gate. Server port 8766 (old demo uses 8765). Runtime data belongs outside tracked source in `.loop-studio/`. No model training is required for this MVP. No new GPU jobs have been started for this product.

Automation: complete-loop-studio-mvp, active, every 30 minutes. The prior cutloop-overnight-build automation is paused and must remain so.

## Milestone 1 — September 13, 2026

Implemented: immutable originals and separate full-duration proxies; versioned saved projects; timeline trim/reorder/remove/locks/undo/redo; original-source 1080p rendering with audio, title, captions and basic looks; local browser editor; generated sample onboarding; job queue/cancellation/restart status; offline full-duration sampling and a configurable vision endpoint adapter.

Verification so far: five automated tests pass, including a cut at 13–14.5 seconds from a 15-second source, decoded 1920×1080 export with non-silent audio, exact original hash preservation, atomic invalid-trim rejection, locks, conflicts and undo recovery. JS syntax passes. Browser sample import and offline draft creation work. Real vision endpoint, reference/style revisions, ten-clip limits and broader UI/export QA remain unfinished; do not mark all gates complete.

Local server: port 8766, launched with /Users/sissi/usagi/.venv/bin/python (session 63621). New checkout packaging must still be verified in its own fresh environment.

## Milestone 2 — local model and revision checks

- Fresh isolated `.venv` installs successfully; packaging discovery was fixed after the initial install check caught an error.
- Added still-image references, source-range splitting, selected-shot revisions, typeface/title placement/background controls, and protection against discarding unapplied form changes.
- Local Ollama `gemma4:12b` vision endpoint is available. A simple vision request passed. A full three-clip analysis plus requested blue → tan → test-pattern order passed, 15-second valid proposal, 205.25 seconds total. Initial thinking-enabled call timed out; `LOOP_MODEL_REASONING=none` is used locally. This is pretrained inference, not training or aesthetic validation.
- Static clips may return no highlights; preserved visual descriptions now explicitly label signal-selected fallback windows. Model failure does not alter the timeline.
- Real-media three-shot 9-second 1920×1080 export passed; source files remain local and ignored. A real-media model check is running. These historical research clips are not included as public onboarding media.
- Seventeen tests pass, covering original hashes, cuts beyond 12 seconds, audio across ten cuts, rotation, source limits, split/undo, locks, invalid model output, targeted revisions, references, byte-range serving, Host/Origin protection and restart status. JS syntax passes. GitHub Actions workflow added; remote run still needs checking after push.
- Current server port 8766, isolated `.venv`, session 95736, model configured but unchecked by default. No cloud GPU jobs or paid API calls started.
- Remaining release work: finish real-media/model and browser revision/export checks; final source audit and push; read GitHub CI results; record honest acceptance report and pause the build heartbeat if all implementation gates pass.
