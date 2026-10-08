# Audio/video synchronization investigation

Tracking issue: [#10](https://github.com/kavtor/casparMIX/issues/10). The operator
reports growing lip-sync error after transitions in an NDI receiver. **This report
remains open.** The controlled tests below do not reproduce that cumulative error
and do not certify the receiver's rendering, display or audio-device latency.

## Content-based measurement

`validate_av_sync.py` generates an uncompressed flash/beep source, routes it through
two equivalent paths, and performs alternating MIX, native Sony WIPE and DME takes.
It compares actual visual and audio onsets, not just transport frame counters.
The source itself is measured so input-frame quantization is not blamed on the
engine. Media timestamps, including gaps, are used rather than assuming a decoded
frame index is an elapsed-time clock.

The optional `ndi_content_probe.cpp` receiver measures the same cue content against
NDI timecodes. It receives only and changes no mixer state. The test harness creates
an isolated server and temporary output; it does not connect to the user's server.
The NDI SDK is needed only to build this diagnostic, not as a new engine dependency.

```sh
c++ -std=c++17 -O2 tools/ndi_content_probe.cpp -lndi -o /tmp/ndi-content-probe
python3 tools/validate_av_sync.py --binary /path/to/casparcg \
  --output /tmp/casparmix-av-sync --seconds 30 \
  --input-fps 24000/1001 --input-sample-rate 44100 --size 1920x1080 \
  --ndi-probe /tmp/ndi-content-probe
```

Omit `--ndi-probe` for a FILE-only measurement. `--stalls` deliberately stops and
resumes only the isolated test process for 150 ms every eighth take. Never use this
as a production test while competing workloads need the GPU.

The FILE diagnostic is scaled to 320×180 before lossless encoding to prevent its
own encoder from overwhelming the measurement. Native composition and NDI retain
the selected raster. The original full-raster lossless recording experiment had
652 timestamp gaps and an incomplete tail; it was discarded as a qualification
result. Counting its surviving frames as contiguous time falsely implied drift.

## Recorded observations (0.18.0)

- 50 fps / 48 kHz, 50 repeated takes: native cue offsets remain approximately
  0.04–0.06 ms; the NDI cue timecodes remain aligned.
- The same test with repeated 150 ms process stalls: no cumulative NDI cue offset.
- 1080p with a 23.976 fps / 44.1 kHz input converted to 50 fps / 48 kHz:
  50 takes, zero recording timestamp gaps. Input cue offsets span about 39.3 ms;
  native offsets span 40 ms, and NDI offsets span 40 ms. The observed slope follows
  the input's frame-quantization phase, rather than an accumulating engine delay.
- The final test ran alongside the user's existing mixer session and another
  substantial GPU workload. It is a functional observation, not an uncontended
  capacity or broadcast lip-sync certification.

See `validation/av-sync-*.json` for all marker pairs and the measured slopes.
The harness rejects timestamp-gapped recordings, too few paired markers, a drift
increase above 1 ms/s or an offset span above 80 ms. These are diagnostic screening
limits, not a recommended production lip-sync tolerance.

## Next checks

Capture the exact affected source and receiver combination, including whether the
audio leads or lags. Compare source content, native FILE output, NDI packet content
and actual receiver playback separately. Include mixed source rates, live inputs,
loop/seek controls, SuperSource/reentry paths, and longer runs. Avoid speculative
buffer or timestamp changes until the reported behavior is reproduced.

NDI's [send documentation](https://docs.ndi.video/all/developing-with-ndi/sdk/ndi-send)
explains synthesized timecodes; a timecode-only throughput test is insufficient
proof of content lip sync. Client rendering can add latency beyond packet reception.
