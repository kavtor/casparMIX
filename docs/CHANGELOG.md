# Changelog

## 0.19.1 — CasparCG 2.5.1 stable

* Fix Dust Mix's incoming matte: a full-width role-1 texture must not invert its
  right half as if it were a packed A/B mask (issue #22).
* Keep opaque A under masked B in the packed path to prevent double attenuation.
* Default to pure particles (ratio 100%); a lower explicit ratio still blends
  with dissolve. Existing explicit preparations remain unchanged.
* New early-progress half-image regression reproduces the previous inversion;
  captured correction covers spatial continuity, packed/single masks, endpoints,
  rewind and rendered PGM/MV identity. No dependency changes.
* Soft-trail operator appearance remains deferred under issue #23.


## 0.19.0 — CasparCG 2.5.1 stable

* Add native DUSTMIX with ratio, independent particle H/V size and reproducible
  progress-indexed flash steps. Video masks stay complementary; audio uses one
  ordinary crossfade, independent of particle visibility (issue #19).
* Add centered/inner/outer wipe border placement and independent inner/outer
  softness on the same frame-local distance field (issue #20).
* Captures verify PGM/rendered MV RGB identity, endpoints, same-picture continuity,
  rewind, ratio-zero dissolve, live preparation and atomic invalid rejection.
* Existing symmetric defaults remain unchanged. No new dependencies.


## 0.18.2 — CasparCG 2.5.1 stable

* Correct Sony mosaic 269 origin from lower-right to upper-right (issue #17).
* Native captures check early corner occupancy, traversal, REV, live tile size
  and exact rendered program/multiview identity.
* Record operator morphology approval of spiral mosaics 206–213.
* 202/203 tile orientation remains under investigation; no speculative change.
* No added dependencies.

## 0.18.1 — CasparCG 2.5.1 stable

* Center the visible bounds of enhanced Sony 26 (heart), 27 (star) and 49
  (regular polygon) on POS, compensating asymmetric local geometry (issue #14).
* Captured native frames verify centering within one pixel for default/displaced
  origins and polygon counts 3, 4, 5, 6, 7, 8 and 64; rendered routes match exactly.
* Record operator morphology approval of Standard Wipes 1–24 and other Enhanced
  Wipes. Modifier approval is a separate step; corrected 26/27/49 await recheck.
* Correct 150, 151, 604 and 606 to reveal incoming B as a center-opening fan
  instead of the complement of a shrinking outgoing wedge (issue #15).
* No added dependencies; published older patches remain unchanged.

## 0.18.0 — CasparCG 2.5.1 stable

* Correct operator-reviewed Sony 1041–1044 to far-side hinged entry, and assign
  their former near-side entry to 1045–1048 (issue #9).
* Validate textured projection in NORM/REV, both endpoints and pixel-identical
  rendered program/multiview captures for all eight presets.
* No added dependencies. Historical release patches remain unchanged.

## 0.17.1 — CasparCG 2.5.1 stable

* Correct Sony SPLIT 1011–1013: NORM brings incoming pieces in, REV takes outgoing pieces out. A/B endpoints remain unchanged. GitHub issue #2.
* Native captures validate both directions, texture coordinates, rewind and exact program/multiview identity. Audio logic is unchanged; a separate CEF startup failure interrupted its additional validation.

## 0.17.0 — CasparCG 2.5.1 stable

* Add Sony 1201 Frame In: incoming texture grows from centre over stationary outgoing video. Linear size is a project default; Sony multi-stage/key-transition preparation is not implied. Native catalogue: 72 implemented, 197 reserved.
* Native captures validate texture, endpoints, reverse, rewind and exact program/multiview identity. No new renderer dependencies.
* Frame In also passed a 60-second 75 fps NDI qualification repeat; the initial run's transient delivery-window failure is preserved in evidence.
* Reproducible 1080p60/75 qualification now includes moving inputs, four M/Es, nested effects and actual PGM/MV NDI reception with SDK drop counters; see PERFORMANCE.md.

## 0.16.0 — CasparCG 2.5.1 stable

* Add Mirror 1355–1358: B grows from UL/UR/LR/LL with three reflected neighbouring tiles; the endpoint contains only normal B. Native catalogue: 71 implemented, 198 reserved. Motion awaits operator review.
* Lossless native captures validate reflected texture coordinates at four positions for every entry, program/multiview pixel identity, and single-copy audio crossfades. No new dependencies.

## 0.15.0 — CasparCG 2.5.1 stable

* Skip stage/audio work for reserved synchronized channels with no layers, consumers or live routes; activation and empty-reader behaviour remain intact.
* Allow bounded 200 ms recovery from transient clock stalls instead of rebasing after one late frame. Expose per-channel produce/mix/consume/frame milliseconds.
* Cache native graphics definitions on SCENE updates and avoid copying/serializing static nodes on every frame; VALUES still animates meters independently. Add cached antialiased left/right triangle primitives for transport indicators.
* Real configured-load measurement improves from 39.6 fps / 0.792x media advance to 50 fps / 1.00x. Sustained overload remains bounded and may reduce output rate; no claim of unlimited real-time capacity.
* Version file changes now trigger CMake reconfiguration. FFmpeg/CEF versions remain unchanged.

## 0.14.1 — CasparCG 2.5.1 stable

* Correct planar pivots according to operator feedback: 1051–1054 and 1055–1058 both use LL, UL, UR, LR, retaining clockwise/counterclockwise motion.
* 1061–1064 starts the side-centre of B on UL/left/CCW, UR/right/CW, LR/right/CCW or LL/left/CW of A, moving the hinge to its final full-frame side position.
* Preserve 1068 unchanged; captures revalidate endpoints, reversal, UV samples and program/MV identity.

## 0.14.0 — CasparCG 2.5.1 stable

* Add 13 interpreted planar Sony DME presets: 1051–1058 corner-pivot rotary scale entries, 1061–1064 lateral rotary entries and 1068 low-centre full-turn scale entry. Native catalogue total: 67; 202 IDs remain reserved.
* Incoming video is geometrically transformed in physical raster coordinates. AUTO, reversible manual progress and REV preserve endpoints, UV content and program/rendered MV identity. These pivots/time laws are documented project interpretations requiring operator review.
* Door 1041–1048 interpretation review remains deferred. Dependency versions are unchanged.

## 0.13.0 — CasparCG 2.5.1 stable

* Add atomic MIXER ALPHAKEY preparation: LINEAR/CHROMA alpha inversion, Rec.709 LUMA extraction with adjustable black/white thresholds and an independent normal/inverted rectangle mask. Existing colour INVERT and CHROMA commands retain their behaviour.
* Processing belongs to logical layers; sources remain reusable. Native captures cover alpha/luma/chroma inversion, both mask senses, strict atomic parameter rejection and exact program/MV equality. No new dependencies.

## 0.12.0 — CasparCG 2.5.1 stable

* Add centre-hinged doors 1045–1048 and live-video flip/tumble 1101–1104, 1121–1122. The reviewed DME catalogue now contains 54 presets.
* Flip faces switch A/B at the edge-on position over an independently prepared background. Hidden faces retain their normal audio crossfade contribution. Scaled variants contract to 65% at midpoint; opposite-sense variants remain distinct.
* Native captures verify endpoints, reversible progress, REV, perspective UV mapping, exact program/MV equality and audio amplitude ratios. Angular curves/camera distance are documented project defaults awaiting operator review. No new dependencies.

## 0.11.0 — CasparCG 2.5.1 stable

* Add native NAM and SUPER MIX video operators inspired by the Sony manual. NAM selects the whole higher-luminance pixel; SUPER MIX adds weighted signals with independently adjustable midpoint gains. Audio remains a normal crossfade.
* Both effects support timed and reversible manual progress, plus live gain changes. Complete rendered inputs are combined in sibling layers; no HTML producer or CPU video readback is introduced.
* Captures validate midpoint RGB, gain changes, endpoints and exact program/rendered multiview equality. No new dependencies.

## 0.10.1 — CasparCG 2.5.1 stable

* Center mosaic grids so opposite clipped edges have equal physical dimensions. Double/four-way paths share a middle row or column on odd grids instead of assigning it asymmetrically.
* Independent traversal checks pass for all 18 compound masks at 10%, 20% and 25% cell sizes. Required horizontal/vertical symmetries match pixel for pixel, as do program and rendered multiview captures.
* DME geometry and protocol are unchanged; no new dependencies.

## 0.10.0 — CasparCG 2.5.1 stable

* Add 44 reviewed native Sony DME primitives: Slide 1001–1008, Split 1011–1013, Squeeze 1021–1031, edge Doors 1041–1044, Split Slide 1384–1385, two-channel Slide 2601–2608 and two-channel Squeeze 2621–2628.
* Video textures are transformed/projected directly. Split draws preserve one audio contribution; no game engine, HTML or video readback is introduced.
* Presets share timed/manual progress, time-reversed geometry and independent background producers. Unknown/reserved Sony IDs never fall back to ZOOM.
* Captures validate all endpoints and program/MV pixel identity. Gradient textures verify Squeeze and Door UV mappings; representative REV captures pass.
* All 269 predefined DME/Resizer IDs are reserved in the catalogue; unresolved effects return an explicit pending error. Defaults are project choices awaiting operator review, not measured Sony temporal curves.

## 0.9.4 — CasparCG 2.5.1 stable

* Add double snakes 250–257, double/four-way spirals 260–265 and staggered waterfalls 266–269. Independent rectangular regions normalize their traversal time, including unequal edge-cell counts.
* Reserve karaoke/undecoded mosaic 220–247 and random/dust 270–274 with an explicit pending-implementation error. They never fall back to another shape.
* Capture checks validate all 18 new masks against independent traversal schedules and compare final program/MV pixels.
* Four overlapping lanes is a project default for waterfalls; exact Sony phase timing is not documented. All changes use the existing GPU compositor; no additional dependency.

## 0.9.3 — CasparCG 2.5.1 stable

* Add mosaic snakes 200–203 and corner spirals 206–213. Tile ranking runs on the GPU without auxiliary HTML or CPU-generated masks.
* TILESIZE accepts integer 2–50 percent of producer height, default 10. Cells remain square in physical pixels, with clipped edge cells.
* Pixel captures validate traversal against independently enumerated paths, live size changes and rendered program/MV identity.
* Softness and border widths are capped to half a cell and affect the exterior union frontier rather than internal cell seams.
* No new build or runtime dependency.

## 0.9.2 — CasparCG 2.5.1 stable

* Complete the reviewed rotary group: 150, 151, 156, 158, 160, 162, 516, 518, 604, 606, 624 and 661.
* Symmetric fans and rotating two/four-blade pinwheels use constant angular motion in producer raster coordinates.
* All twelve support manual progress, reverse, origin, aspect, multi, softness and the native border. No HTML producer or extra runtime dependency.
* Captures verify monotonic coverage, complementary reverse, SOFT/BORDER and exact rendered program/multiview pixel identity.

## 0.9.1 — CasparCG 2.5.1 stable

* Preserve the producer raster aspect in Sony masks when their draw trees are routed into differently shaped channels. Circle and rotary geometry no longer depends on the monitor raster.
* Widen the heart, star and arrow slightly; normalize polygon bounds to equal width and height at neutral aspect.
* Validate rendered program routes against independent output with exact RGB pixel comparisons for eight iris/polygon cases and six native DME cases.
* No new build or runtime dependencies.

## 0.6.0 — CasparCG 2.5.1 stable

* Add procedural corner-page and incoming-scroll deformation of live video.
* Batch depth-sorted mesh triangles in the existing GPU renderer with smooth
  lighting and a neutral backside. Geometry stays independent of OpenGL.
* Add an independent, audio-muted DME background producer and clock-preserving
  live background replacement. No new library dependencies.

## 0.5.0 — CasparCG 2.5.1 stable

* Add native MOVE scene interpolation and a minimal textured 3D cube/zoom path.
* Add manual native PUSH/SLIDE primitives; legacy timed commands are unchanged.
* Absolute progress supports reversible T-bar scrubbing with readiness gates and
  destination handoff. Scene geometry is prepared once, sampled on the GPU frame path.
* No new build or runtime dependencies.

## 0.4.2 — CasparCG 2.5.1 stable

* Retain a single cached static graphics sheet. The experimental tiled draw tree
  was withdrawn pending an uncontended benefit measurement. High total-GPU
  readings during the experiment were dominated by another application.
  Meter target updates remain separate; typography and startup/error fixes remain.

## 0.4.1 — CasparCG 2.5.1 stable

* Keep GRAPHICS transparent before the first scene arrives and when a scene has
  no nodes. A live startup race exposed an unchecked empty scene reference.
* Extend the capture harness with a deliberate startup gap before SCENE.

## 0.4.0 — CasparCG 2.5.1 stable

* Add opt-in `GRAPHICS` scenes: reusable cached FreeType text and rectangles,
  stereo-meter building blocks, grouped attack/release, local clock and heartbeat
  watchdog conditions. No mixer, M/E or kavtor-specific layout is built into the producer.
* Bake static graphics in independent dirty regions only when visible content changes; level-only updates
  retain tiny cached GPU resources instead of uploading the whole overlay.
* Add atomic bounded scene/value parsing and bounded text/animation caches.
* Return AMCP failure replies for asynchronously rejected producer calls instead
  of leaving clients waiting for an absent reply.
* Add FreeType and a TrueType font dependency for native graphics. Existing
  producers and the HTML module remain available.

## 0.3.1 — CasparCG 2.5.1 stable

* Add `COLORBARS EBU75|EBU100|SMPTESD|SMPTEHD` using the existing FFmpeg source
  filters. Generate one channel-resolution static image and reuse its GPU upload.
  No continuously running decoder or HTML producer is required.
* Correct the BT.601 inverse matrix Cr contribution to green from -0.509 to
  -0.714136 (and refine Cb precision). Color-bar captures exposed the tint error.
* Compare captured bars with FFmpeg references, including a small-raster RP 219
  path with explicit BT.709 conversion. No new package dependency.

## 0.3.0 — CasparCG 2.5.1 stable

* Add explicit progressive `sync-group` channel configuration. Group members use
  a common rational software clock and evaluate source channels before their
  dependent channels, regardless of channel number.
* Cross-channel routes inside a group use the current presentation epoch;
  rendered routes complete the current GPU mix without the legacy pipeline delay.
  Independent channels retain their existing scheduling and buffering.
* Reject cyclic cross-channel dependencies, mismatched frame rates, cross-domain
  inputs and hardware-clock consumers. Preserve local layer snapshot routes.
  Severe overload rebases the software deadline rather than accumulating a burst.
* Add moving-frame identity checks for nested routes, CUT and MIX, plus shared-clock
  audio and Sony-wipe regressions. This is internal software synchronization,
  not external genlock, PTP or ST 2110 compliance.

## 0.2.2 — CasparCG 2.5.1 stable

* Discard pending image/audio output frames while a channel has no rendering
  demand. Resuming a rendered route no longer publishes the pipeline head
  retained from its previous activation.
* Moving-frame captures reproduce and distinguish idle-resumption artifacts from
  steady route latency. The latter remains two frames in the measured 720p50
  graph; this release does not claim frame synchronization between channels.
* Document the existing upstream OMT draft and hardware-backed ST 2110 work.
  Transport integrations remain deferred, with no new package dependencies.

## 0.2.1 — CasparCG 2.5.1 stable

* Avoid per-frame native wipe tokenization/string conversion/future creation.
  Reuse border-color frames until their actual color changes.
* Consume nested OpenGL render sublayers by move rather than copying their item
  and texture vectors at every composition depth. This reduces CPU-side work;
  no percentage GPU-load improvement has been established.

* Correct native iris geometry for output display aspect and repeated cell aspect.
  At neutral ASPECT, square, diamond and circle have equal displayed dimensions.
* Add approximately one pixel of derivative-based antialiasing to hard edges and
  drawn contours; SOFT remains a separate adjustable effect.
* Full-resolution progressive 720p50 captures measure circle 294x294, square
  256x256 and diamond 398x398 at progress 0.2. ASPECT 2 produces twice the width
  relative to height. Existing border, route and audio regressions pass.

## 0.2.0 — CasparCG 2.5.1 stable

* Fix invalid one-frame transition interpolation. The isolated same-picture route
  reproduction showed nine changed frames with 0.1.0 and none with this build.
* Add GPU-only rendered composition routes. Captured nested half-opacity
  compositions remain unchanged when mixed into another channel.
* Add ten confirmed Sony wipe shapes, manual/timed progress, live softness, border,
  aspect, repeat and position controls. Borders can be drawn in the same shader
  geometry as the wipe, with a gap mode retained as an explicit alternative.
* Add isolated lossless video/audio regression tooling. These checks cover the
  named reproductions; they do not guarantee all sources, formats or legacy HTML
  paths are flash-free. No new engine dependencies.

## 0.1.0 — CasparCG 2.5.1 stable

* Wait for actual routed frame content before declaring a route ready. In the
  captured wipe startup reproduction, the original server showed two unwanted
  incoming frames; the patched build showed none. This is not a general guarantee
  against every flash or a fix for composition flattening.
* Update audio meter state on consumer-free channels using the audio mixer alone.
  Consumer-free sine metering and recorded routed audio were verified locally.
  Removing meter-only Art-Net consumers reduced observed whole-system GPU load
  from roughly 57% to 29–32%; these figures are workload-specific.
* Identify the patch version in the build banner without changing the upstream
  numeric version. Interlaced operation and consumer hot-plug need broader testing.
