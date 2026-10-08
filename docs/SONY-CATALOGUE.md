# Native Sony catalogue expansion (0.7.0)

The native mask renderer implements Sony WIPE identifiers 1–12, 17, 18 and
21–24. The ten original panel shortcuts retain their numbers and geometry.
This adds opposite bars (2, 4), lower-corner boxes (7, 8), the remaining diagonal
fronts (10–12), and the expanding central cross (22). The reference is the
operator-supplied DVS/XVS catalogue; no SMPTE number is inferred for the cross.

Each pattern accepts manual/automatic progress, reversal, SOFT, BORDER, ASPECT,
position and repetition through the existing WIPE://SONY and WIPESONY commands.
The shader measures iris geometry in displayed-pixel aspect units. Masks only
reveal the two video pictures; they do not move or deform either picture.

Run `tools/validate_sony_catalogue.py --binary /path/to/casparcg --output /tmp/sony`
to sample actual captured frames against the defined geometry at three progress
positions. `tools/regression.py --sony --expanded-sony --rendered --synchronized`
also validates same-picture continuity, automatic/manual transitions, soft colour
partition and the existing synchronized rendered routes. Supply `--binary` and
`--output` there as well. The committed validation reports cover all 18 masks.

kavtor exposes Sony DME numbers 1001–1004 for incoming cardinal slides and
2601–2604 for outgoing/incoming cardinal pushes. These are application-level
aliases of the existing native primitives, not new engine syntax or masks.
Normal/reverse operation and T-bar use the corresponding entry directions.
No arbitrary Sony page/cube identifier is assigned to the generic 3D primitives.

Wedges (13–16, 19–20), enhanced figures, programmable patterns, diagonal DME,
page variants, multi-action PinP and mosaics remain pending. Their reference
identifiers must not be advertised as executable merely because they exist in
the imported inventory. This release introduces no new runtime dependencies.

## Standard, Enhanced and Rotary expansion (0.9.0)

Implemented masks now total 41: 1–24, 26, 27, 29, 49, 100–107 and 300–304.
VERTICES selects polygon 49's 3–64 vertices; ROUNDING sets rounded presets'
0–50% radius, default 15%. Parameters are atomic and validated before changing
a mask. Standard non-circular irises use raster-relative proportions; 24 remains
circular in pixels. Enhanced figures keep their natural proportions.

The engine retains the single-frame mask/border compositor. Captured same-picture,
soft/border and timed/manual tests pass for all 41 masks; separate captures verify
figure visibility, live polygon changes and origin updates. The imported pictograms
do not establish complete temporal curves, so exact Sony motion equivalence
remains an operator validation step.

Page back faces now show live video. MOVE poses may supply eight perspective
coordinates (UL, UR, LR, LL); older manifests retain identity. Native captures
verify cropped corner pinning and the corresponding MOVE endpoint geometry.
No additional runtime dependencies are introduced.

## Reviewed rotary completion (0.9.2)

The native catalogue totals 53 patterns. Added 150/151 side-pivot double fans;
156 central fan from 12; 158/160 opposed clockwise blades from 12/3;
162 four clockwise blades; 516/518 top/bottom pivot left-to-right fans;
604/606 bottom/top pivot double fans; 624 central fan from 9; and 661
opposed opening fans from 9 and 3. White in the reference pictogram is B.
Side/edge double fans progressively close the remaining A wedge.
REV reverses the exposure path; NORM/REV alternation remains panel logic.
All masks use their producer raster, including when displayed by the MV.

## Compound matrix completion (0.9.4)

250–257, 260–269 raise the implemented catalogue to 83 of the 116 known
mask patterns. Double/four-way patterns divide the tile grid into independent
regions; each traverses its snake/spiral over the full transition duration.
An odd grid dimension yields unequal region cell counts without changing
cell shape. The remaining 33 IDs are explicitly pending: 220–247, 270–274.
They are reserved and rejected by the renderer rather than aliased.

Waterfall 266/267 descends, with left/right lane staggering respectively.
268 proceeds rightwards from upper lanes; 269 leftwards from lower lanes,
following the operator's below-origin description. Neutral stagger is four
overlapping lanes; this is a project time law requiring operator confirmation,
not a measured Sony temporal curve.

## Symmetric matrix raster (0.10.1)

All square-cell grids are centered in the producer raster. Opposite edges
clip equally. For compound paths, an odd middle row/column belongs to both
traversal regions and exposes once either corresponding front reaches it.
Double/four-way regions thus retain actual mirror symmetry, including when
cell size does not divide the output dimensions. This supersedes 0.9.4's
unequal region-count treatment. Capture checks cover three sizes and both
odd/even grids, preserving the source image and its rendered monitor pixels.

## Centre-hinged doors and flip/tumble (0.12.0)

The reviewed DME catalogue increases from 44 to 54. Added 1045–1048,
1101–1104 and 1121–1122. Native video planes use perspective projection with
physical raster proportions; the flip changes texture from A to B at midpoint.
The prepared U2-style background is visible behind the plane. Both audio feeds
remain independently weighted even when a face is hidden.

Project defaults are explicit: one half-turn, centre pivot, constant angular
speed, camera 3.5 frame heights away; scaled flips reach 65% at midpoint.
Complex trajectories, hold bands and unknown multi-stage presets remain
reserved. 215 DME/Resizer catalogue IDs still require implementation/review.

## Edge-door interpretation correction (0.18.0)

Operator review assigns 1041–1044 to far-side entry and 1045–1048 to near-side
entry with the same left/right/top/bottom pivots. The previous centre-axis
interpretation of 1045–1048 is withdrawn. See `validate_sony_door_depth.py` for
NORM/REV texture and endpoint checks against native program and rendered MV.
