# Loop Studio visual direction

Reference: https://www.moonshot.ai/, inspected September 13, 2026. Borrowed the tone of a near-black canvas, quiet typography, thin borders and orbital imagery. Loop's logo, artwork, copy and implementation are original; no Moonshot assets are bundled.

## Two surfaces

- `/`: spacious landing page, animated ASCII orbit, studio introduction, open-source story and interactive character lab. Orbit/Wave, density, pause/resume and save-text controls work locally. Motion respects the operating-system reduced-motion preference.
- `/studio`: compact editing workspace inspired by the media/viewer/inspector/timeline organization of Final Cut and CapCut. Panels scroll independently on desktop. The timeline remains available at the bottom; on narrow screens panels stack. The Inspector edits exact shot data; Director creates proposals; ASCII controls actual rendered effects.

## Actual ASCII footage

The effect samples each source frame into a luminance grid and replaces cells with cached character glyphs. White and phosphor-green palettes, 40–120 columns, and source aspect ratio are supported. Streaming conversion bounds working memory. The converted shot goes through the same color/title/caption/audio composition path as normal video. Intermediates are local and removed after successful rendering. Originals remain untouched.

The ASCII look is intentionally coarse. It is a whole-film effect; per-shot effects and independent audio tracks are not implemented. Timeline thumbnails show source footage, while rendered previews show the treatment. The A1 strip labels the current mix and does not pretend to show a measured waveform.

## Verified

39 automated tests, JavaScript syntax checks, real eight-second 1080p ASCII export with audio, browser route navigation, character-mode/pause controls, shot inspector and timeline zoom. Desktop screenshots and true 390×844 mobile emulation were inspected; both pages have viewport-matching document widths. Private review footage/screenshots are outside Git.
