# Optional IP transport integrations

Research checked on 2026-10-04. These are deferred features; current development
priority is internal route timing, frame alignment and CUT continuity.

## Open Media Transport

CasparCG upstream already has an implementation proposal:
https://github.com/CasparCG/server/pull/1790

At review time it is open, draft, unmerged, with no submitted reviews or issue
comments. Last update: 2026-09-27. Reviewed head:
`16b10e6af97467b31faca88bffeaa23cf350a3b2` (based on upstream master).

The change adds a producer, consumer, `OMT LIST`, source names and `omt://host:port`
addresses. Output supports multiple pixel formats and alpha conventions. libomt
is loaded dynamically, so a server can operate without that runtime installed.
Prefer evaluating/backporting this work, with attribution, instead of building a
second transport module. Compatibility with the pinned 2.5.1 engine and local
FFmpeg must be checked before claiming it works here. No OMT patch was applied.

Dependencies and packaging:
* libomt exports a C API and uses .NET Native AOT to produce a native library.
  The .NET SDK is needed to build it, not as a managed runtime for the application.
* libvmx provides the codec runtime. The libomt, libomtnet and libvmx repositories
  declare MIT licenses.
* The PR's optional Linux source build requests .NET 8 SDK and clang. Its external
  projects currently follow `master`; our package must pin reproducible releases
  or commits instead. Prefer separate runtime packages with optional dependency
  relationships rather than making all casparMIX builds fetch unpinned projects.
* No dependency has been added to the current casparMIX package.

Timing review:
* OMT exposes timestamps in 100 ns units, including an automatic timestamp/pacing
  mode (`-1`). The PR uses that automatic mode for video and audio output.
* Its input assembles audio from a FIFO against channel cadence; the inspected
  producer does not use incoming timestamps to align picture and audio.
* It is therefore a transport starting point, not a solution to internal M/E
  frame synchronization. Test A/V continuity, source loss/reconnect, queue bounds,
  frame-rate mismatches, alpha handling and multiple-source discovery before use.

Primary sources:
https://github.com/openmediatransport/libomt
https://github.com/openmediatransport/libomtnet
https://github.com/openmediatransport/libvmx

## ST 2110 upstream status

GitHub searches across issues and PR (open and closed) for `2110`, `2059`, `PTP`
and `Media Transport Library` found no native software transport proposal in the
CasparCG organization. This is a scoped search result, not proof that no private
or unindexed work exists.

There is relevant hardware-backed work:
https://github.com/CasparCG/server/pull/1652
Merged 2025-09-24, this enables opting into YUV/v210 output for otherwise 8-bit
channels. The discussion explicitly references Blackmagic 2110 receivers which
need 10-bit YUV. This is DeckLink output compatibility, not a general ST 2110
network producer/consumer or a common internal M/E clock.

Forum discussions:
https://casparcgforum.org/t/casparcg-smpte-st-2110/4587/14
A maintainer described Deltacast prototyping and considered Media Transport Library
in March 2023; proprietary SDK distribution was a stated obstacle. This historical
post is not evidence of an active current implementation.
https://casparcgforum.org/t/blackmagic-decklink-ip-support/6156/1
A maintainer tested DeckLink IP output in November 2023 and described same-card
hardware sync groups for fill/key output after the 2.4 implementation changes.
That guarantees a specific hardware output pairing, not all channels in the engine.

ST 2110 remains on the roadmap in TIMING.md. Neither it nor OMT is a prerequisite
for fixing unequal internal path latency on a single machine.
