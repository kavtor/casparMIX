# Frame timing and ST 2110 roadmap

## Measured baseline, 2026-10-04

`tools/route_timing.py` runs an isolated three-channel 720p50 server and generates
an FFV1 clip with a sixteen-bit frame counter encoded in vertical bars. A simultaneous
capture compares a direct source route with that same source routed through a
GPU-rendered channel. It then captures repeated CUTs between those routes.

On the 0.2.1 candidate, all 184 settled simultaneous samples showed the rendered
path **two source frames behind** the direct path (40 ms at 50 fps). Alternating
CUTs also produced discontinuities. This reproduces the temporal problem which
static-color regressions cannot detect. Some CUT anomalies are larger than the
steady two-frame offset; producer replacement/last-frame handling needs separate
investigation rather than attributing all discontinuities to steady latency.

The script exits successfully when measurement succeeds, even when synchronization
fails. `frame_locked` and `continuous` in its report express the actual result.
The recorded baseline is `validation/route-timing-0.2.1.json`.

## Engine findings

* Each `video_channel` advances its own counter and thread.
* `output` maintains a per-channel software clock unless a consumer owns timing.
* The mixer retains one progressive frame (two fields for interlaced operation).
* Rendered routes publish the completed, buffered mix; raw routes publish stage frames.
* Route queues consume whichever frame is available, repeat the last frame when
  late, and have no common presentation epoch.

A shared clock alone will not compensate different processing depths. A fixed
route buffer alone will not establish a shared clock or preserve alignment across
changing topologies. These findings describe the independent-channel baseline. See the opt-in group
implementation below for the new path.

## Proposed implementation order

1. Introduce opt-in synchronization groups with a common rational frame timeline,
   frame identifiers and matching audio sample ranges. Retain existing independent
   channel operation for standard CasparCG workflows.
2. Schedule channel dependencies without cycles and compensate path latency at
   joins. Define startup, format changes, consumer clock ownership, late frames and
   bounded latency before making frame-accurate claims. Preserve GPU texture routing.
3. Verify moving-picture identity during CUT, MIX, frozen compositions and nested
   routes, together with audio alignment and overload behavior.
4. Add an external clock provider (PTP/ST 2059) and ST 2110 producer/consumer modules.
   External timing must discipline the same internal timeline, not create a second
   independent scheduling system.

## ST 2110 assessment

ST 2110 belongs in the engine as optional transport and clock integration. kavtor
owns endpoint configuration, routing and operator UI. The transport suite provides
separate synchronized media essences; it does not by itself align unequal internal
rendering pipelines.

Evaluate a tagged release of OpenVisualCloud Media Transport Library rather than
writing packetization, receive timing and pacing from scratch. Begin with ST 2110-20
video, ST 2110-30 audio, ST 2110-10 timing and ST 2110-21 sender pacing. SDP/session
handling is required; NMOS discovery/control, ANC and redundant transport can follow
as separately scoped features. NIC/backend compatibility and actual timing compliance
must be measured. No transport dependency has been added yet.

Uncompressed 1920x1080p50, YCbCr 4:2:2 10-bit active video requires
1920 * 1080 * 50 * 20 = 2,073,600,000 bit/s before packet overhead. Network capacity,
multicast, PTP infrastructure and hardware timestamp/pacing support must therefore
be part of deployment planning, rather than assuming ordinary gigabit Ethernet.

Sources reviewed:
* https://www.smpte.org/standards/st2110
* https://github.com/OpenVisualCloud/Media-Transport-Library

## Idle-resumption fix in 0.2.2

Discarding pending mixer work during consumer-free/rendered-route-free periods
eliminates the large stale-image excursions seen when recreating a route. The
post-fix capture has eight backward steps of one frame and eight forward steps of
three frames, consistent with the remaining two-frame path offset; it no longer
shows the baseline jumps of roughly 15–44 frames. One additional repeat/skip pair
was recorded. This is a bounded improvement, not a frame-lock solution.
See `validation/route-timing-0.2.2.json`.


## Shared-clock implementation in 0.3.0

An explicit `sync-group` schedules matching progressive channels on one rational
software timeline. Each cross-channel route registers a dependency for its
lifetime; a topological pass evaluates sources before destinations. Rendered
routes publish the completed current mix, bypassing the independent-channel
pipeline queue. Routes inside the group only accept the current epoch. Source
startup readiness still delays producer replacement until actual picture content
exists. Same-channel layer snapshots retain their original behavior.

Moving-frame verification includes two nested rendered hops and a dependency from
channel 4 into channel 3, so numeric channel ordering cannot accidentally pass the
test. CUT and MIX between direct and nested paths must preserve frame identity and
one-frame increments. The shared-clock test exits nonzero on failure. Cycle and
explicit cross-channel buffering rejection are checked without terminating the
server. Lossless captures and audio windows are recorded by the regression suite.

```sh
python3 casparmix/tools/route_timing.py --binary /path/to/casparcg --synchronized
python3 casparmix/tools/regression.py --binary /path/to/casparcg --rendered --sony --synchronized
```

This initial implementation serializes channel evaluation within each group and
waits for completed GPU work where required. It prioritizes frame identity over
pipeline parallelism. Sustained overload lowers cadence; it is not proof of
frame-rate performance with a full production graph. Independently paced live
sources can still arrive late. Hardware-clock consumers, interlaced groups and
cross-domain inputs are explicitly unsupported. PTP and ST 2110 remain deferred.


Validated captures: at 50 fps, 185 simultaneous comparisons had zero frame offset,
340 CUT samples and 210 MIX samples advanced by exactly one frame. At 60000/1001
fps, all 225 simultaneous comparisons had zero offset; 411 CUT samples and 255 MIX
samples likewise advanced by one frame. Neither capture had discontinuities.
The shared-clock video/audio suite passed all sixteen cases. Reports are in
`validation/route-timing-0.3.0-50.json`, `route-timing-0.3.0-5994.json` and
`0.3.0-synchronized.json`. These are isolated test graphs, not full-load validation
of the live kavtor installation.

The independent-channel suite also passed all sixteen cases; see
`validation/0.3.0-independent.json`. No build or runtime dependency was added.

## Cadence regression and reserved-channel work (0.15.0)

Operator reported normal clips appearing slow. On the real setup, channel 1
advanced approximately 39.6 sync epochs/second at a nominal 50 fps, and its
media time advanced 0.792 seconds per wall second. This was a genuine global
cadence issue, not an inferred source FPS or a persistent Speed Editor rate.

Reserved empty channels still queued stage calls and silent audio mixing. They
now fast-path only when no layers, consumers or live route readers exist.
Loading uses the autonomous stage executor and atomic empty-state notification;
a route to an empty channel continues rendering black in the shared epoch.

Single-frame rebase tolerance also accumulated media drift on otherwise
recoverable stalls. A bounded 200 ms window now allows short backlog recovery.
Native graphics static-definition serialization moved from every receive to
SCENE changes; clock/blink/watchdog phases still invalidate visible sheets, and
VALUES updates do not invalidate static composition.

After changes, the same configured load with program/preview active measured
50.00 fps and approximately 1.000 media seconds per wall second over 30 seconds.
See validation/live-cadence-0.15.0.json. This does not measure lip-sync content
or solve sustained resource exhaustion: recovery remains bounded, and extended
overload can still reduce cadence. Treat output-rate loss as a separate future
overload-policy/telemetry requirement, not intentional clip slow motion.
