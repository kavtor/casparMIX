# 60 fps qualification and capacity margin

The minimum progressive target is 60 fps. Qualify a declared workload at 75 fps
to demonstrate 25% higher frame throughput (20% shorter processing intervals).
This is a capacity test on a specific system, not a guarantee for arbitrary
source counts, hardware, codecs, outputs or sustained thermal conditions.

The isolated benchmark uses 110 reserved channels, six moving 1080p60 inputs,
two static inputs, four M/E pairs, nested native iris/border and Mirror effects,
and a twelve-tile native multiview with labels/clock. Optional NDI mode adds
program and multiview consumers and receives both locally. It coexists with
the normal development server, rather than claiming an otherwise idle GPU.

Example fixture (generated locally, no third-party footage):

```sh
ffmpeg -f lavfi -i testsrc2=size=1920x1080:rate=60 \
  -f lavfi -i sine=frequency=440:sample_rate=48000 -t 6 \
  -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -c:a aac bench.mp4
python3 casparmix/tools/benchmark_mixer.py --binary /path/to/casparcg \
  --clip bench.mp4 --fps 60 --seconds 120 --output /tmp/mixer-60 \
  --ndi-probe /path/to/kavtor-ndi-timing
```

Repeat at `--fps 75`. kavtor builds the updated optional receive probe with
`-DKAVTOR_BUILD_NDI_DIAGNOSTICS=ON`; the NDI SDK is required only for that tool.
The renderer keeps its existing dependencies.

Pass criteria: mean producer cadence at least 99.5% of target, media-clock
advance within 0.5% of native real time, and (with NDI) delivered mean cadence
at least 99.5%, one-second delivery windows at least 97%, and zero receiver SDK
video/audio drops after connection startup. Producer-clock one-second windows
are reported separately: bounded catch-up behind consumer buffers can cause
a short epoch window without losing delivered frames. Composition-only mode
also requires that clock-window threshold, since no delivery is measured.

Synthesized NDI timecode discontinuities are reported, not interpreted as
frame loss or lip-sync evidence. SDK drops are independent counters. Neither
proves frame-by-frame content identity, encoder quality or physical-network
behavior; qualify required output consumers and receivers separately.

Current 30-second NDI captures: approximately 60.01 producer / 60.02 PGM /
59.99 MV fps at 60, and 75.04 producer / 74.98 PGM / 74.96 MV fps at 75.
Both maintained native media speed and recorded zero SDK audio/video drops.
One synthesized timecode discontinuity occurred per receiver at 75 fps.
See validation/headroom-ndi-60-0.16.0.json and headroom-ndi-75-0.16.0.json.
Longer soak testing and hardware outputs/encoding remain separate requirements.

## Frame In 1201 qualification (0.17.0)

The first 30-second run maintained 75 fps and zero SDK drops but failed the
strict 97% one-second delivery-window threshold (MV minimum 71.73 fps).
A 60-second repeat passed without threshold changes: PGM and MV averaged
75.00 fps, minimum windows 73.38/72.99 fps, native media speed 1.00046x,
and zero SDK audio/video drops. Both results are retained in validation.
This variability remains a reason for longer soak testing and controlled
system-load qualification, not a universal real-time guarantee.
Use `--sony 1201` to include this effect instead of the default Mirror.

## Capacity exploration above 75 fps

100 fps: producer 100.10, PGM 100.01 and MV 100.00 fps, no SDK drops,
1.001x native media speed. Strict window qualification failed (MV 96.89).
120 fps with native effects advancing every frame: producer 120.12, PGM
120.02 and MV 120.00 fps, no SDK drops, 1.001x media speed. Strict window
qualification failed (MV 115.99).
150 fps: producer 136.59, PGM/MV approximately 136.3 fps and media speed
0.911x. This is sustained overload, despite zero receiver SDK drops.
These results bracket throughput below 150 fps for this declared graph;
they do not qualify 100/120 as clean production formats or compare systems.
The previous live renderer was no longer reachable and its concurrency was
not verified, so these runs must not claim a coexisting production graph.
A subsequent 130 fps attempt crashed during startup and is not a valid
capacity measurement. Crash diagnosis is tracked separately.

## Live GPU observation (2026-10-08)

Short per-process `nvidia-smi pmon` samples of the user's 1080p50 mixer showed
CasparCG at roughly 19–46% GPU activity and the desktop compositor at roughly
5–17%. A later ten-second sample included another application at 68–96%; it
cannot establish a CasparCG regression relative to the previously observed 30%.
Per-process activity is an estimate, may overlap, and must not simply be summed.

No capacity claim or rendering change is based on these samples. Compare an
identical source/M/E/output graph, consumers and receiver connections, with the
GPU otherwise idle. NDI readback/encoding, live HTML and desktop composition must
be distinguished from native effect cost. See [A/V investigation](AV-SYNC.md) for
the separate content-timing tests and their limitations.
