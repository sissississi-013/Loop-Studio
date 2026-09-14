# Workflow improvement after the first alpha was rejected

The user asked for a better process. This pass evaluates footage → playable draft → review → revision → keep → export. It does not equate passing tests with good taste or user acceptance.

## Changes

- **Make my film** analyzes missing footage, plans and renders a draft in one action. Existing analysis is reused. Import progress remains visible and drafting waits for all uploads.
- The saved timeline is unchanged until **Keep this cut**. Review uses rendered shot thumbnails, a current-cut comparison, calculated duration and focused feedback. Kept previews and unaccepted drafts survive reload/project switching. Stale drafts cannot be kept.
- Configured local model mode defaults on; remote mode requires opting in. A separate text planner can reuse vision analysis. Models select validated, distinct source segments. Invalid plans receive one bounded repair; failures preserve the edit.
- References are read inside the main workflow. Their basic look and measured cut timing can guide a draft. Explicit finishing choices persist and take precedence; revisions preserve the draft's finishing.
- Presets, adaptive default duration and original chord/percussion beds support brief interpretation. Offline story limitations remain explicit. Jobs show progress, cancellation and retry.
- Frame rounding follows cumulative timeline time, avoiding drift across fractional-frame cuts.

## Actual review cases — September 13, 2026

### 1. Existing real footage and a music-video brief

Used copies of three local clips totaling 10.2 seconds. The user's original project and footage were preserved. Cached gemma4:12b descriptions were reused; nemotron-3-nano:4b planned locally.

Observed failures drove fixes: the large planner timed out; a lighter planner invented out-of-range trims; a first segment-based draft was only two seconds; enlarged candidates overlapped. The final pipeline uses distinct validated ranges and duration checks. A final eight-second request rendered to **8.0 seconds in 17.08 seconds**, with no overlapping ranges. Frames and full video decode were checked. No semantic accuracy or aesthetic score is implied.

Browser checks covered current/draft comparison, asking for a shorter opening, keeping, reload and 1080p export. The focused offline revision took 2.3 seconds and changed only the opening. The kept timeline equaled the reviewed proposal. That intermediate export was 1920×1080 with audio. Later cumulative-frame timing fixes passed an integration check using ten fractional-frame cuts.

### 2. Ten fresh clips

Imported ten locally generated three-second clips through HTTP, with no existing analysis. All ten stored originals matched their input hashes. The offline 20-second draft completed in **8.98 seconds**; the complete fixture/import/draft check took 12.05 seconds. It contained no repeated source ranges and did not mutate the saved timeline. A duplicate draft request was rejected.

The browser loaded its persisted draft, saved a newly typed brief through the main action, displayed render progress, and cancelled another draft. The completed run before cancellation took 7.13 seconds; cancellation left the saved brief and timeline intact. The first attempt to click Cancel lost the race to a completed render; a new run was cancelled successfully. Synthetic footage validates mechanics, not aesthetic quality.

### 3. Reference and revision recovery

A generated six-second reference with two scene cuts was uploaded. The main action analyzed it without a separate analysis step and applied the measured **two-second** cut length. Its neutral signal-based color suggestion was preserved; the offline estimator did not infer a monochrome treatment from that reference.

An unsupported offline sunset instruction failed explicitly, leaving the edit intact. The first model recovery incorrectly returned multiple shots for a selected-shot request. The conflicting full-film instruction was removed, and this invalid response now qualifies for one bounded repair. A subsequent local-model revision completed in **25.68 seconds**, shortened only the selected opening and preserved the locked shot and every unrelated shot.

## Verification and remaining limits

Thirty-six automated tests pass locally, including source/lock safety, reference analysis inside drafting, persisted explicit finishing, draft-style preservation during revision, duplicate segment rejection, bounded repair, duration budgets and fractional-frame export timing. JS syntax and repository whitespace checks pass. CI is checked after publishing this milestone.

The films and evidence stay in the ignored local data directory. No cloud compute or paid model calls were used. Models still mislabel footage and may produce weak sequencing. Sampled stills do not provide continuous motion/audio understanding. Music is a simple procedural bed, not a professional score or beat-matched edit. Reference handling is basic color/cut timing, not aesthetic transfer. Human review and common-footage comparisons remain necessary.

This is a reviewable workflow improvement, not proof that the user is satisfied. Once the published checks finish, pause this bounded review loop for user review rather than silently treating the entire product vision as complete.
