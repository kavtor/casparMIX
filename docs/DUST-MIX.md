# Dust Mix and asymmetric wipe borders

Sony documents Dust Mix as a combination of a selected pattern with diamond dust,
with ratio, particle H/V size and flash rate. See [DVS-9000 manual,
pp.196–198](https://pro.sony/s3/cms-static-content/operation-manual/3704674111.pdf).
Our additional MIX variant interprets this concept as a dissolve blended with
small diamond-shaped reveals. It is not a measured reproduction of Sony's
random generator. Sony 270–274 catalogue IDs remain separately reserved.

```text
PLAY 3-1 route://2 RENDERED DUSTMIX 25 MANUAL 1 DUST_RATIO .5 H_SIZE .02 V_SIZE .02 FLASH_RATE 0
CALL 3-1 "PROGRESS .5"
CALL 3-1 "DUST_RATIO .75 H_SIZE .03 V_SIZE .03 FLASH_RATE 10"
```

DUST_RATIO is 0–1, H_SIZE/V_SIZE are .001–1 fractions of producer picture height,
and FLASH_RATE is 0–100 progress-indexed sequence steps. Defaults: 1/.02/.02/0 (0.19.1 onward).
Zero ratio is a normal dissolve. Frame-local progress drives both video masks;
there is no independently clocked HTML overlay. Fixed particles are reproducible;
flash advances deterministically as progress advances and holds/retraces with
manual progress. This time law is a project choice, not Sony clock equivalence.
The final endpoints are always exactly A/B. The audio crossfade uses normal
progress regardless of visual particle coverage; it is not multiplied per cell.

## Geometric colored trails

Sony distinguishes the softness of inner and outer border edges. See
[MVS-8000X manual, p.142](https://pro.sony/support/res/manuals/4567/1c69a0dc97b11fb0372df981503c3291/45673690M.pdf).
The project also allows placing the whole border on either side of the contour:

```text
PLAY 3-1 route://2 RENDERED WIPESONY 25 SONY 1 MANUAL 1 BORDER 10 BORDERCOLOR #00ff00 BORDER_SIDE -1 INNER_SOFT 15 OUTER_SOFT 0
```

BORDER_SIDE is -1 for inside incoming B, 0 for centered, +1 for outside B toward A.
The total hard width is preserved when moving the border to one side. INNER_SOFT
and OUTER_SOFT accept -1 (inherit SOFT) or 0–100. Default centered/inherit settings
retain the existing renderer's behavior. Asymmetric softness is ordered so the
A/color/B partition cannot produce a negative color band. This is a geometric
trail, not a temporal feedback/afterimage effect. Endpoint border visibility is
zero, and the border shares the exact mask distance/progress/raster with the wipe.

## Validation

`validate_dustmix.py` checks complementary pixels, endpoints, same-source
continuity, repeat/rewind, ratio-zero dissolve, live parameters, atomic invalid
rejection and pixel-identical wide rendered MV. `validate_dustmix_audio.py`
measures two independently identifiable tones at .25/.5/.75 progress.
`validate_asymmetric_border.py` measures side placement and softened color
partition, tests invalid updates/endpoints and compares PGM/MV captures.
Operator morphology and real sources remain separate acceptance checks.

Explicit lower ratios include a uniform dissolve by design. For pure dust use
DUST_RATIO 1. Older saved 50% preparations are preserved; use default recall or
set 100% in the operator UI. The 0.19.1 spatial regression supplements earlier
brightness checks, which did not detect inversion of a whole image half.
