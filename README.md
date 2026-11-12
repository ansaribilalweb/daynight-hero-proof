# Day → Night — hero proof (Phase 0)

Throwaway verdict piece for the ansaribilal.com homepage redesign. **Not the real site** — nothing here touches ansaribilal.com, its routes, blog or publishing engine.

**Technique:** scroll-scrubbed frame sequence. A flat-illustration desk scene is rendered programmatically (`gen_frames.py`, PIL) into WebP frames — 150 @1600×900 for desktop, 84 @960×540 for mobile. A pinned canvas maps scroll progress to frame index with rAF lerp smoothing; frames preload progressively behind a JPEG poster. The headline lives in the DOM and crossfades *"Sales agent by day."* → *"Builder by night."* in step with the scene. `prefers-reduced-motion` gets a static dusk frame with both lines stacked; no-JS gets the poster.

**Scene beats:** day (sun, sales-chart monitor + wall poster, phone) → sunset crossfade (screens morph chart → code, poster chart → `</>`) → night (stars, lit skyline, lamp cone on, code glowing, coffee steam).

**Payload:** desktop frames 3,324 KiB total · mobile frames 1,115 KiB · poster 97 KiB.

QA screenshots at 0/25/50/75/100% scroll were captured locally before publishing (`shoot_proof.py`).
