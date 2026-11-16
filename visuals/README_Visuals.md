# Basics

Three explanatory images show Sniplet's silence-cut logic using public stock footage. Real frame comparisons illustrate body and mouth tracking; audio waveforms, pause lengths and editing outcomes are schematic. These are visual explanations, not evidence of silence removal from the source video.

# Table of Contents

Basics · Table of Contents · Maintenance · What Belongs Here · How This Folder Works · How to Add or Edit · Changelog · Reminders · MISC

# Maintenance

Keep the source credit, illustration labels and PNG/SVG pairs together when updating or sharing these images. Do not imply endorsement by the person pictured.

# What Belongs Here

- `01-cut.png` / `.svg`: matching endpoints; keep 0.5 seconds of natural quiet.
- `02-keep.png` / `.svg`: body match with a mouth mismatch; leave the pause intact.
- `03-fillers.png` / `.svg`: optional adjacent filler extension, disabled by default.

PNG files are ready to share; SVG files are editable vector layouts with embedded source frames. All are 1600 × 1050.

# How This Folder Works

Frames come from [Man Talking While Looking at the Camera](https://www.pexels.com/video/man-talking-while-looking-at-the-camera-8048324/), by **Antoni Shkraba**, Pexels video 8048324. Retrieved 16 November 2026. [Pexels License](https://www.pexels.com/license/) permits use and modification; it prohibits implying endorsement. The stock frame content remains governed by that license, not the repository's MIT code license.

The downloaded asset is a 13.4-second, 1920 × 1080 video with no audio stream. Start/end frames: 7.8 / 8.6 seconds for the matching illustration, 8.2 / 9.4 seconds for the mouth mismatch. Actual Sniplet landmark comparisons generated the shown movement ratios; coordinates use its 854-pixel reference width. Invisible wrists are unmeasured. The matching pair also passed the sampled background check. Bars cap at 2×; numeric values remain uncapped.

Waveforms, “um,” silence lengths and cut outcomes are **illustrative**, not detected speech or pauses. The filler card reuses the matching pair to explain endpoint rechecking; it is not a real filler-removal test. No private interview frames were used.

# How to Add or Edit

Preserve earlier published versions in Git history. Verify source rights, recalculate any measured values, render all three final PNGs and inspect text, framing, waveform labels and cut markers before publishing.

# Changelog

16 November 2026: added the three-image visual guide, editable SVG layouts, source attribution and measurement/illustration boundaries.

# Reminders

Sniplet remains a lightly tested MVP. A visual match does not guarantee an imperceptible cut. Review real outputs with sound.

# MISC

The raw stock video is not distributed in this repository. Source link and timestamps above allow independent reproduction.
