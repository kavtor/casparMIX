# Additive engine commands

## Isolated rendered compositions

`PLAY 3-1 route://2 RENDERED MIX 25`

`RENDERED` is opt-in and accepts whole-channel routes only. The source channel is
mixed into a GPU texture before it enters the destination draw tree. Destination
opacity, keys and transitions act on the completed picture, not its individual
layers. Audio travels as one mixed frame. Source channels render on demand even
without output consumers; they skip CPU video readback in that case. Existing raw
routes retain upstream behavior. Self-routes are rejected. Clients must prevent
indirect cycles. Normal channel buffering still applies; this is not a zero-latency
or cross-channel frame-lock guarantee.

## Native Sony wipes

`PLAY 3-1 route://2 RENDERED WIPESONY 25 SONY 23 SOFT 25 BORDER 10 BORDERCOLOR #ffffff`

Duration is an integer number of frames (1–10000). No HTML template is involved.
The outgoing picture is retained until the incoming producer is ready. The engine
applies picture geometry, border and softness using the same frame-local shader
parameters. Audio crossfades linearly with progress. A completed timed transition
hands over to the incoming producer.

Confirmed Sony numbers, deliberately separate from SMPTE numbering:

| Sony | Shape |
| --- | --- |
| 1 | Horizontal travel / vertical edge |
| 3 | Vertical travel / horizontal edge |
| 5 | Box from top left |
| 6 | Box from top right |
| 9 | Diagonal from top left |
| 17 | Center opening on X |
| 18 | Center opening on Y |
| 21 | Square iris |
| 23 | Diamond iris |
| 24 | Circle / ellipse iris |

Unknown numbers fail instead of silently selecting another pattern. This list is
not the complete Sony catalog. Additional verified patterns can be added later.

Parameters: `SOFT` and `BORDER` 0–100; `ASPECT` width/height multiplier 0.01–1000;
At ASPECT 1, iris proportions are 1:1 in displayed pixels, regardless of output
format. Hard edges include approximately one pixel of antialiasing.
`MULTI` 1, 2, 4, 9 or 16; `X`, `Y` center 0–1; `REVERSE` 0 or 1;
`BORDERCOLOR` an opaque CasparCG color. Defaults: no softness or border, aspect 1,
single pattern, centered, normal direction, white border.

`BORDERMODE DRAW` (default) draws a softened contour over the outgoing/incoming
composition in the engine. `BORDERMODE GAP` retains the alternative two masks with
a color background between them. Both share the same geometry and progress.
Border mode is chosen when starting the transition, not during `CALL`.

### Manual progress and live preview modifiers

```
PLAY 3-1 route://2 RENDERED WIPESONY 1 SONY 9 MANUAL 1 SOFT 25 BORDER 10
CALL 3-1 "PROGRESS 0.5"
CALL 3-1 "PROGRESS 0.7 SOFT 40 BORDER 20 ASPECT 1.5 BORDERCOLOR #ff8800"
```

`PROGRESS` is 0–1; adding it via `CALL` also changes a timed transition to manual
control. Modifier updates validate before changing state. Manual mode stays on the
layer at either endpoint: the mixer client decides whether to commit the incoming
source or restore the outgoing source, using a normal `PLAY`. At progress 0 the
outgoing image is complete; at 1 the incoming image is complete, with no border.

For clients needing a matte only, `PLAY 3-1 WIPE://SONY/23 PROGRESS 0.5` generates
packed incoming/outgoing keys, matching the existing split-key composition path.
It accepts the same geometry parameters, but no border color/mode. Optional
`DURATION` animates that matte; explicit progress switches it back to manual.

## Compatibility and current limits

The upstream command set and numeric version remain unchanged. `VERSION` also
contains the patch version. [kavtor](https://github.com/kavtor/kavtor) uses these
extensions directly; feature availability depends on the installed patch version.
Versioned sections below identify when each command family was introduced. See
the [current release](../README.md#current-release) and
[Sony catalogue](SONY-CATALOGUE.md) for the implemented effects and remaining gaps.

Native wipes and 3D DME are engine primitives. Source assignments, M/E scheduling,
keyer participation and operator controls belong to the mixer client. Unsupported
Sony patterns reject execution rather than falling back to another effect.

Validation uses progressive 720p50 RGB lossless captures and recorded audio.
Interlaced operation, video-mode changes, long-running live sources and every
consumer/module still need broader integration testing. The regressions do not
establish that every possible startup flash has been eliminated.


## Shared progressive channel clock (0.3.0)

Assign the same nonempty `sync-group` name to every channel participating in a
mixing graph, including inputs, M/E compositions, outputs and multiview:

```xml
<channel>
  <video-mode>1080p5000</video-mode>
  <sync-group>kavtor</sync-group>
  <consumers />
</channel>
```

All members must use the same rational progressive frame rate. Raster dimensions
may differ (for example a wider multiview). Cross-channel routes automatically
establish dependency order and receive the current group frame. `RENDERED` still
requests an isolated composition. A group destination cannot route from another
clock domain or request positive cross-channel `BUFFER`. Cycles and whole-channel
self-feedback are rejected. Local layer routes retain their previous-stage
snapshot behavior, including explicit `BUFFER 1` used by DSK hold layers.

NDI, FFmpeg and screen consumers work with the software clock. Consumers owning a
hardware clock (DeckLink, Bluefish, OpenAL) are rejected in this initial mode.
Changing a member's frame rate or switching to interlaced operation requires a
server restart with a matching group configuration. Other format changes at the
same rate retain the group clock. Under sustained overload, output cadence drops;
the group does not independently skip/repeat one route to catch up. External
source arrival timing is not disciplined by this feature.

Channels without `sync-group` keep standard independent operation. Monitor state
exposes `frame-sync/epoch` for group members. This does not claim hardware genlock,
PTP synchronization or real-time performance under every workload.


## Static standard color bars (0.3.1)

```text
PLAY 1-1 COLORBARS EBU75
PLAY 1-1 COLORBARS EBU100
PLAY 1-1 COLORBARS SMPTESD
PLAY 1-1 COLORBARS SMPTEHD
```

EBU75 is the default if the pattern is omitted. EBU75 and EBU100 use FFmpeg's
`pal75bars`/`pal100bars` definitions. SMPTESD uses `smptebars` (EG 1-1990), and
SMPTEHD uses `smptehdbars` (RP 219-2002). Unknown patterns are rejected. Patterns
are generated once at the destination channel raster and repeated indefinitely
with no audio. Regenerate after a format change to retain pixel-level sharpness.
Existing solid-color commands remain unchanged.

Generation uses planar 4:4:4 to avoid chroma boundary interpolation. SD/EBU patterns
use BT.601 and HD bars use BT.709; small-raster HD bars use explicit RGB conversion
to avoid the legacy mixer's SD color-matrix heuristic. These are the named SDR
reference patterns implemented by FFmpeg, not a claim to implement every SMPTE
revision or HDR pattern, nor a guarantee of calibrated signal levels through all
RGB composites and output codecs.

References:
* https://www.ffmpeg.org/ffmpeg-filters.html (section 18.13)
* https://pub.smpte.org/pub/rp219-1/rp0219-1-2014.pdf
* https://www.itu.int/rec/R-REC-BT.601-7-201103-I


## Native graphics scenes (0.4.0)

```
PLAY 11-80 GRAPHICS
CALL 11-80 SCENE <base64-encoded UTF-8 JSON>
CALL 11-80 VALUES <base64-encoded UTF-8 JSON object>
CALL 11-80 HEARTBEAT
```

Each producer owns its independent viewport, scene, animation state and watchdog.
`SCENE` atomically replaces the scene. Root keys: `width`, `height` (logical pixel
viewport, up to 4096×2160), `timeout` (heartbeat seconds, 0.1–3600), and `nodes`.
Viewport geometry scales to the destination raster. At most 2048 nodes and 512 KiB
of encoded scene data are accepted. Extra root metadata is ignored by rendering.
`VALUES` updates bar targets by ID (values 0–1), preserving scene geometry and
cached static graphics. Unknown IDs or invalid values reject the entire update.
Accepted scene/value updates also refresh the heartbeat. A rejected scene leaves
the previous scene intact.

Node types: `rect`, `text`, `clock`, `bar`. Common keys: `x`, `y`, `w`, `h`,
`color` (`#RRGGBB` or `#RRGGBBAA`), `blink` (half-period milliseconds), and
`lostOnly` (draw only after timeout). Text uses `text`, `size` (6–256 pixels),
`align` (`left`, `center`, `right`), `bold`, `font` (`sans` or `mono`),
`spacing` (0–16 pixels), optional `background` and `padding`.
From 0.19.2, `valign` accepts `top` (unchanged default) or `center`. Center
places the visible glyph ink inside node `h`, excluding transparent font padding.
A centered background follows the node box; existing top-aligned backgrounds
retain their previous geometry.
Long text is ellipsized to its width. `clock` displays local engine-host time.
Bars use `id`, `value`, `vertical`, `minimum`, `maximum` and optional `group`;
colour bands of one meter share a group, target and release envelope. Callers
update all bar IDs in a group with the same normalized target. `hideOnLost`
hides a bar during the watchdog condition.

Static nodes retain their array order and are baked to one immutable cached
sheet. Animated bars are composited over that sheet, in bar array order; use
separate Caspar layers if text must overlay an animated bar. The static sheet is
rebuilt only for visible changes (including wall-clock ticks and blinking).
Text/shape cache is bounded to 512 entries/32 MiB per producer; retained draw
frames own their resources. Bars have immediate attack and a 180 ms release.

Example scene before Base64 encoding:
```json
{"width":1920,"height":1080,"timeout":5,"nodes":[
  {"type":"text","x":20,"y":20,"w":400,"size":28,"text":"PROGRAM","color":"#ffffff","background":"#c01818","bold":true},
  {"type":"bar","id":"level","x":20,"y":80,"w":10,"h":200,"vertical":true,"value":0.75,"color":"#1f9d3a"},
  {"type":"text","x":400,"y":460,"w":1120,"size":100,"align":"center","text":"SERVER LOST","color":"#ff4545","lostOnly":true}
]}
```

This adds no full-screen CEF replacement for arbitrary HTML templates. It is a
small native graphics API, reusable by clients independently of kavtor.

## Native DME transitions (0.5.0)

Append `DMENATIVE <frames> <effect> MANUAL 0|1 REVERSE 0|1` to a PLAY/LOADBG
producer command. Effects: MOVE, CUBE, ZOOM, PUSH_LEFT/RIGHT/TOP/BOTTOM and
SLIDE_LEFT/RIGHT/TOP/BOTTOM. MOVE additionally requires `SCENE <hex-json>`.
The unchanged legacy PUSH/SLIDE commands remain available.

`CALL <channel>-<layer> "PROGRESS <0..1>"` switches to absolute manual progress.
Source/destination and track readiness hold the outgoing frame until all inputs
are ready. Timed progress advances on the channel's frame clock, including fields.
The endpoint returns the ordinary destination producer, without restarting it.
Manual producers retain both endpoints for reverse scrubbing until replaced.

MOVE SCENE is UTF-8 JSON encoded as hexadecimal, with 1–66 track objects:
`producer` is a producer specification; `from` and `to` contain `fill`, `clip`,
`crop` rectangles as [x,y,width,height], `opacity`, `volume` (0–1) and `order`.
Scene payloads are limited to 128 KiB decoded. Geometry/progress must be finite.
Parsing and route creation occur once at preparation, not once per rendered frame.
The mixer client owns matching policy and producer identity; the engine owns
frame-local interpolation and GPU composition. Original source channels are never
modified. `RENDERED` routes keep M/E and nested compositions flattened.

The minimal 3D primitive projects video-textured cube faces through a camera into
Caspar's existing GPU perspective pipeline. It introduces no game-engine runtime,
new graphics context, CPU video readback, encoder or network return path. Cube
supports both directions; ZOOM currently zooms through the outgoing frame.
This is the foundation for additional planar/mesh effects, not a page-curl or
arbitrary animation importer yet.

## Textured page surfaces and backgrounds (0.6.0)

`DMENATIVE <frames> PAGE_CURL|PAGE_ROLL MANUAL 0|1 REVERSE 0|1` uses a
procedural video-textured surface. PAGE_CURL turns the outgoing picture from a
corner; PAGE_ROLL unrolls the incoming picture over the old image. Both endpoints
and reverse progress are absolute. These are generic primitives, not yet exact
implementations of numbered Sony DME presets.

The backend-independent mesh lives in `core/frame/page_geometry.h`: corner pages
use a 24×24 grid, rolls 48 bands. Quads are depth sorted, clipped and triangulated
into one GPU draw. UVs sample the live picture, with a lit neutral-paper backside.
There is no HTML producer, CPU video readback or secondary graphics context.
The current renderer is OpenGL; mesh generation can be reused by future backends.
Curvature and paper-back material are neutral defaults in this first version.

Optional `BACKGROUND <hex-UTF8-producer-spec>` adds a separate underlying signal.
Examples: hex of `#000000`, `#ff0000`, or `route://4 RENDERED`. Omitting it preserves
normal transparent Caspar composition; the mixer client explicitly requests BLACK
by default. Background audio is immediately muted. This fill is independent of
page backside material and of the outgoing/incoming pictures.

`CALL <channel>-<layer> "BACKGROUND <hex-UTF8-producer-spec>"` changes the fill
without resetting the clock or progress. The previous fill remains until the new
producer is ready. The native destination handoff remains unchanged: fill applies
to the transition composition, not a permanent recolouring of its destination.
The mixer client validates routing cycles and decides whether live updates are
permitted; kavtor allows them in rehearsal and snapshots programme takes.

### Mosaic wipe size (0.9.3)

Sony 200–203 and 206–213 accept `TILESIZE 2..50` (integer percentage of
producer height), default 10. Both creation and live CALL accept it.
Example: `PLAY 10-1 route://2 RENDERED WIPESONY 25 SONY 206 TILESIZE 10 MANUAL 1`.
Cells are square; edge cells are clipped. SOFT/BORDER are bounded to half
a cell and follow the exposed union boundary, without painting internal seams.

### Reviewed Sony DME primitives (0.10.0)

`DMENATIVE <frames> SONY_<code>` accepts the 44 IDs in
`src/core/producer/wipe/sony_dme_catalogue.h`. `MANUAL 1` plus CALL PROGRESS
uses the same geometry as AUTO; REVERSE samples the reversed A/B trajectory.
Example: `PLAY 10-1 route://2 RENDERED DMENATIVE 25 SONY_1025 MANUAL 1`.
Background specification remains an independent muted producer. The renderer
requires both foreground textures ready before advancing a timed take.

One-channel Slide/Squeeze/Doors place B over stationary A; two-channel Slide
and Squeeze transform both pictures. Split separates A to reveal B.
Interleaved Split Slide uses 16 strips at neutral preparation. Linear progress,
camera distance and strip count are project defaults, not documented Sony
curves. Reserved effects with unresolved geometry/multiple stages fail explicitly.

### Broadcast MIX video operators (0.11.0)

```text
PLAY 3-1 route://2 RENDERED DMENATIVE 25 NAM MANUAL 1
PLAY 3-1 route://2 RENDERED DMENATIVE 25 SUPER_MIX MANUAL 1 A_GAIN 1 B_GAIN 1
CALL 3-1 "PROGRESS 0.5"
CALL 3-1 "A_GAIN 0.7 B_GAIN 0.8"
```

A/B gains are finite numbers in 0..1, setting midpoint video levels. At time 0
only A is visible; at time 1 only B. NAM uses full A/B gains at midpoint and
selects the complete pixel with greater Rec.709 luminance. SUPER MIX adds the
weighted signals and clamps to the output range. Before midpoint A goes from
100% to its configured peak while B rises from zero to its peak; afterwards
A falls to zero and B reaches 100%. Audio always crossfades normally.
The video operators assume full-frame background signals. Generic `MIXER
BLEND NAM` and `SUPER_MIX` use the same pixel operations. `REVERSE` applies
the producer's usual swap/time-reversal policy.

### Flip/tumble (0.12.0)

The original interpretation of 1045–1048 was corrected in 0.18.0 (see below).
`SONY_1101`/`1102` rotates the picture
around its vertical/horizontal centre axis through half a turn: A is visible
before midpoint and B afterwards. The edge-on face disappears over the prepared
background. `1103`/`1104` also vary scale; `1121`/`1122` rotates in the opposite
sense with scale variation. The catalogue total is now 54 reviewed presets.

```text
PLAY 3-1 route://2 RENDERED DMENATIVE 25 SONY_1101 MANUAL 1 BACKGROUND 23303066663030
CALL 3-1 "PROGRESS 0.25"
```

The hex background in this example is `#00ff00`. Background producers remain
muted. A/B audio crossfades independently of which face is visible, including
at the exact edge-on midpoint. AUTO and reversible manual progress use the
same geometry. Defaults inferred from pictograms: centre pivot, constant
angular speed, camera 3.5 frame heights away, 65% midpoint scale for scaled
flips. They are not claims of measured Sony timing or lens equivalence.

### Logical alpha/luminance key processing (0.13.0)

```text
MIXER 3-2 ALPHAKEY LUMA 0.25 0.75 0 1 0 0.2 0.1 0.8 0.6
MIXER 3-2 ALPHAKEY LINEAR 0 1 1 0 0 0.1 0.1 0.9 0.9
MIXER 3-2 ALPHAKEY OFF 0 1 0 0 0 0.1 0.1 0.9 0.9
MIXER 3-2 ALPHAKEY
```

Order: mode, low, high, key-invert, mask-enabled, mask-invert, left, top, right,
bottom. Modes are OFF, LINEAR and LUMA. Numbers must be finite in 0–1; low <
high, left < right, top < bottom; flags must be exactly 0 or 1. Validation is
atomic. Query returns numeric mode 0/1/2 followed by the remaining parameters.
Preparation is immediate; no duration/tween suffix is accepted. MIXER CLEAR
restores defaults. OFF bypasses this additional processing.

LUMA extracts Rec.709 luminance from unpremultiplied RGB and linearly maps the
low/high interval onto coverage. Source alpha limits coverage. LINEAR uses
existing alpha, including a preceding CHROMA operation. Key inversion flips
coverage, never colour; unlike the old INVERT command, it does not create an RGB
negative. Fully transparent premultiplied pixels have no recoverable fill.

The rectangle mask is applied afterwards in output-space normalized coordinates.
Mask inversion retains the outside rather than the inside. It does not invert
the key extraction, and is inactive when the mask is disabled. Processing affects
only its logical layer; do not attach it to shared input producers. Already
processed rendered routes should use neutral destination processing. Audio is
unchanged. No separate fill/key-source operation is implied by this command.

### Planar 2D entries (0.14.0)

`DMENATIVE <frames> SONY_<code>` additionally accepts 1051–1058, 1061–1064
and 1068. These use the ordinary MANUAL/PROGRESS/REVERSE and prepared-background
contract. B grows over stationary A while rotating/translating; video samples
are transformed, not revealed through a wipe mask. Rotation uses physical raster
units so a 16:9 source remains the same rectangular texture when turned.

Interpretation defaults, awaiting operator review:
- 1051–1054: corner pivots LL, UL, UR, LR, angle −90° → 0°, scale 0 → 1.
- 1055–1058: corner pivots LL, UL, UR, LR, angle +90° → 0°, scale 0 → 1.
- 1061–1064 (corrected in 0.14.1): the side-centre of B starts on a corner
  of A and moves to its final full-frame side-centre. Pairings are
  UL/left/CCW, UR/right/CW, LR/right/CCW, LL/left/CW.
- 1068: lower centre → screen centre, −360° → 0°, scale 0 → 1.

Scale, centre motion and angle are linear in progress. The manual/pictograms
do not specify these exact pivots/angles/time laws; the effects are not claims
of measured Sony equivalence. Alpha/audio follow existing native DME policy.

### GRAPHICS transport shapes and channel timing (0.15.0)

GRAPHICS scenes accept a `triangle` node with the existing x/y/w/h/color geometry
and `direction` equal to `left` or `right`. Shapes are antialiased and cached;
no font glyph coverage is required. Existing rect/text/bar/clock types retain
their behaviour. Bar lostOnly/hideOnLost/blink rules remain independent.

Channel monitor state adds performance/frame-ms, produce-ms, mix-ms and
consume-ms, in milliseconds with the underlying timer resolution. Idle reserved
channels report frame-sync/idle=true and a current epoch. These timings describe
local work; they are not remote reception or network bitrate measurements.

### Mirror entries (0.16.0)

`DMENATIVE <frames> SONY_1355` through `SONY_1358` use the existing
MANUAL/PROGRESS/REVERSE contract. A remains behind four copies of B: the
normal tile and horizontal, vertical and double reflections. The normal tile
grows from the upper-left, upper-right, lower-right or lower-left respectively.
At halfway the four tiles cover the frame; at completion the normal B covers
the frame and reflected neighbours are outside it. Scale is linear in progress.
This is a pictogram-based interpretation awaiting operator confirmation.
Only one B tile contributes audio, preserving the ordinary crossfade.

### Frame In (0.17.0)

`DMENATIVE <frames> SONY_1201` grows incoming B uniformly from the screen
centre over stationary A, preserving texture proportions. Size equals manual
progress; at zero no incoming pixels are visible, at one B is full-frame.
The ordinary manual, reverse and audio-crossfade contracts apply. This is
a pictogram-based project interpretation awaiting operator confirmation;
Sony's multi-stage Frame I/O/key preparation and dead bands are not simulated.

### SPLIT direction correction (0.17.1)

Sony 1011–1013 use operator-confirmed NORM entry and REV exit. Only those
presets invert the earlier default; A/B endpoints and ordinary linear audio
crossfade remain unchanged. Other Sony primitives retain their direction.

### Far/near edge-hinged entry correction (0.18.0)

`SONY_1041`–`SONY_1044` unfold incoming B from the far side towards its full-screen
position, with left, right, top and bottom edge pivots respectively.
`SONY_1045`–`SONY_1048` use the same pivots from the near side, retaining the former
1041–1044 trajectory. `REVERSE` retraces the selected geometry. This replaces the
incorrect centre-axis interpretation of 1045–1048. Sources, endpoints and audio
crossfade policy are unchanged.

### Sony edge page turns and rolls (0.20.0)

```text
PLAY 3-1 route://2 RENDERED DMENATIVE 25 SONY_1301 MANUAL 1 REVERSE 0
CALL 3-1 "PROGRESS .5"
```

1301–1304 are edge Page Turn; 1321–1324 are edge Roll. In each block the
directions are right-to-left, left-to-right, bottom-to-top and top-to-bottom.
REVERSE exchanges A/B and reverses the same trajectory; final output remains B.
The default radius is .16 of the bend-axis extent. Sony keyframe/multi-action
variants and parameter editors remain pending.

### Karaoke rows (0.21.0)

```text
PLAY 3-1 route://2 RENDERED WIPESONY 25 SONY 220 MANUAL 1 ROWNO 8 START -100 PHASE 0
CALL 3-1 "PROGRESS .5 ROWNO 4 PHASE -100"
```

Karaoke 220–223 use tiled lanes. ROWNO is integer 1–64; START and PHASE
accept -100…100. START selects the first lane, then wraps order. PHASE -100
advances lanes simultaneously; +100 advances them sequentially. Tile length
is set with existing TILESIZE; lane thickness follows ROWNO. Parameter updates
are atomic, and progress retraces without a timer. SOFT/BORDER share the same
frontier. Dedicated application/controller parameter menus are not yet included.

## Random mosaic and Diamond Dust (0.22.0)

Sony 273 switches seeded rectangular tiles. Sony 274 expands actual diamond
particles. Both are evaluated only from progress: a held T-bar holds the image,
and rewinding retraces it. They do not alias the existing Dust Mix transition.
The manual (printed pp.142–143) documents H Size, V Size and Volatility for 273,
and H Size, V Size and Flash Rate for 274. Neutral defaults are H_SIZE/V_SIZE
0.02 of picture height and generation rate 75 (0–100). Equal H/V dimensions
have equal physical size on every output. VOLATILITY controls the 273 threshold
curve; FLASH_RATE controls the spread of 274 particle start times. These time
laws are project interpretations, not measurements of Sony hardware. Dedicated
LCD/touch parameter editors and operator morphology approval remain pending.
SOFT and BORDER use the same native contour, bounded by particle dimensions.

```text
PLAY 3-1 route://2 RENDERED WIPESONY 25 SONY 273 MANUAL 1 H_SIZE .04 V_SIZE .04 VOLATILITY 75
CALL 3-1 "PROGRESS .5"
PLAY 3-1 route://2 RENDERED WIPESONY 25 SONY 274 MANUAL 1 H_SIZE .02 V_SIZE .02 FLASH_RATE 75
```

89 wipes execute; 27 remain reserved (224–247 and 270–272). The three old
random presets still require identified morphology; they are not aliases.
