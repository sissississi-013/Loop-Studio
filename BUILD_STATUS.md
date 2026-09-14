# Current work — workflow refinement ready for review

The user rejected the first alpha. The subsequent workflow pass is implemented and exercised on three concrete review cases; see WORKFLOW_REVIEW.md. This does not establish user acceptance or professional output quality.

Current server: port 8766, session 43145. Local vision gemma4:12b; planner nemotron-3-nano:4b; reasoning disabled. Final real-footage draft: eight seconds, 29.94 seconds pipeline time, no repeated source ranges. Thirty-seven tests pass locally. Code commit 72f958e passed GitHub Linux CI: https://github.com/sissississi-013/Loop-Studio/actions/runs/34798787019. The bounded workflow review heartbeat is now paused for user review. No jobs remain running. Runtime evidence remains ignored under .loop-studio/workflow-evidence. The original user project is unchanged.

The historical implementation-completion entries below describe the first alpha and must not override this current status.

# Implementation gates

Status: initial MVP implementation gates complete. This is a functional local alpha; creator validation and broader product scope remain follow-up work. See ACCEPTANCE.md.

- [x] G1 — Full-duration import: up to ten clips / ten minutes; original bytes retained, separate full-duration proxies, rotation/audio handling, persistent projects.
- [x] G2 — One editable timeline: trim, reorder, remove, locks, undo/redo, optimistic conflict protection and recovery after restart.
- [x] G3 — Original-source 1080p export: aspect ratios, soundtrack/source audio, typography/captions, consistent preview/export, cancellation and errors.
- [x] G4 — Footage analysis and direction: full-duration candidate windows; timestamped model descriptions/highlights through a pluggable provider; local offline fallback explicitly labeled; editable proposal from a natural-language brief.
- [x] G5 — References and revisions: optional reference-derived editable style, targeted changes preserve locked shots, clear model and privacy controls.
- [x] G6 — Usable studio: sample onboarding without login or payment, upload → brief → draft → adjust → export; manual workflow fully functional without a model.
- [x] G7 — Release checks: automated integration tests, real media decode and audio checks, browser workflow, accessible layout, reproducible setup, license, limitations, repository updated.

Human creator validation and competitive aesthetic benchmarks are follow-up research, not implementation gates that automated tests can satisfy.

## Recovery

Repository: /Users/sissi/Loop-Studio. Continue the first unfinished gate. Server port 8766 (old demo uses 8765). Runtime data belongs outside tracked source in `.loop-studio/`. No model training is required for this MVP. No new GPU jobs have been started for this product.

Automation: complete-loop-studio-mvp, now paused after completion (previously every 30 minutes). The prior cutloop-overnight-build automation is paused and must remain so.

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

## Release candidate

Twenty-one local tests pass in the isolated environment, without warnings. Wheel builds and includes the web assets and MIT license. A raw HTTP reference-image upload returned 202 and completed; local browser revision/title/caption export produced 1920×1080 output. Reference scene-cut timing is checked on a three-scene fixture.

Real model check: requested horse → person → bird ordering passed, but the model mislabeled the swan and incorrectly claimed a nine-second duration for an eight-second proposal. These errors are retained in ACCEPTANCE.md. Model explanations are explicitly reviewable, calculated duration is displayed separately, and corrected footage notes are saved/undoable and override descriptions in the direction context.

No task model request or GPU job remains running. The local Ollama server may keep its own model cache until its normal unload timeout. The Loop Studio server is session 93177 at port 8766. New release candidate GitHub CI and final browser reference check are the remaining G7 items.

## Completed implementation gate

All seven scoped implementation gates passed. Code commit `bf87c1d5299d3f9fa66e5fcb5aa73bfb918c3f5a` passed GitHub Linux CI: https://github.com/sissississi-013/Loop-Studio/actions/runs/34790627993. Twenty-one local tests also pass. Browser reference import/analysis/application changed the color look as expected, and a model footage note was corrected and saved through the UI. Real-footage preview was visually inspected with the updated title placement.

The heartbeat `complete-loop-studio-mvp` is now PAUSED at its implementation completion gate. Do not automatically restart or extend it into an endless polishing loop. The original hackathon heartbeat remains paused. Follow new user requests normally. No model request or task GPU job is running. The editor remains available on port 8766, session 93177.

This completion means the defined local alpha workflow is implemented and checked. It does not establish aesthetic superiority, accurate understanding of every clip, production hosting readiness, or parity with every competitor. The known model errors and product limits are explicitly recorded in ACCEPTANCE.md.
