# FFmpeg 9 and modern CEF assessment

Reviewed 2026-10-07 against CasparCG v2.5.1-stable + casparMIX 0.13.0.
This is an assessment, not an implemented dependency migration. Production
packages, running sessions and dependency pins were not changed.

## Current package

The local PKGBUILD uses `ffmpeg8.1` and CEF
`142.0.17+g60aac24+chromium-142.0.7444.176`. FFmpeg 9.0.2 is already installed as
system FFmpeg: libavcodec/libavformat 63.1.102, libavutil 61.1.102. Upstream 2.5.1
ships FFmpeg 8.1.2; 8.1 is a maintained release branch, not proof of an unsupported
library simply because 9 is newer.

## FFmpeg 9: small migration, runtime validation required

A syntax-only compilation using the system FFmpeg 9 headers succeeded for all
eight affected translation units checked: av_producer, av_input, ffmpeg_producer,
ffmpeg_consumer, av_util, audio_resampler, ffmpeg module and html_producer.
Precompiled headers were disabled and the version macros were verified as
libavcodec 63, libavfilter 12, libavutil 61. This is not a linked build or a
successful media playback test.

The existing FFmpeg 8 adaptation already handles modern channel layouts,
AVFrame duration, codec capability queries and typed filter option arrays.
One concrete runtime incompatibility remains: the producer unconditionally sets
`abuffersink.all_channel_counts`. A minimal actual-library probe returned success
with local 8.1 but AVERROR_OPTION_NOT_FOUND (-1414549496) with 9.0.2. The option
must be omitted for the new API; compilation alone cannot detect this failure.

Upstream PR [1795](https://github.com/CasparCG/server/pull/1795) is open and handles
that call. Its author reports successful FFmpeg 9.0.1 playback after the fix.
The text describes removal in 8+, but our installed 8.1 still exposes the
option as deprecated: use actual headers/library behaviour rather than assuming
all builds labelled 8 have the same compatibility options. The proposed guard
removes the now-unnecessary call for both newer branches.

[FFmpeg 8 support PR 1715](https://github.com/CasparCG/server/pull/1715) was merged
2026-03-17. The inspected master is still based on that adaptation. Searches did
not find a dedicated FFmpeg 9 upgrade PR; 1795 is relevant compatibility work,
not a complete release migration. Searches are scoped evidence, not proof that
no contributor is working privately.

Migration work:

1. Backport the relevant upstream fix with attribution in its own engine commit.
2. Fully rebuild/link with system FFmpeg 9, without 8.1 include/library paths.
3. Test video+audio and audio-only playback, multi-channel layouts, loop/seek,
   HLS/SRT, alpha media and file/stream encoding. Check colour and A/V continuity.
4. Change the package dependency to system `ffmpeg`; remove private 8.1 pkg-config
   and loader paths. Ensure every optional module links the same major libraries.
5. Retain a validated older-version configuration where inexpensive; do not mix
   headers from one major and libraries from another.

Engineering estimate: low effort for code/packaging (roughly 1–2 focused days),
plus 1–3 days for media/output regression testing, depending on coverage and
failures. This is a planning range, not a measured completion promise.

## CEF: moderate integration and validation work

Official Linux64 builds include CEF
`154.0.34+g14c5a08+chromium-154.0.8037.98`. It is a plausible test candidate; do
not select an unpinned development build. CasparCG master still pins CEF 142 in
its Linux bootstrap. No dedicated later-major CEF migration PR was found in the
reviewed title searches.

The CEF 154 render/audio/lifespan handler headers were compared with the installed
142 headers. The callbacks used by CasparCG in those three interfaces have no
obvious signature break; the render/lifespan differences there are documentation
changes. This is not a full SDK compile, wrapper rebuild or runtime validation.
Other CEF interfaces and generated API/ABI machinery still need review.

CEF library, headers, API version, C++ wrapper, subprocess handling and resources
must be built/packaged together. Replacing libcef.so alone is not an upgrade.
Make the system CEF root configurable rather than adding another hard-coded
version path. Test off-screen transparent frames, CG play/update/stop/reload,
HTML audio, WebGL, remote/local templates, frame cadence, teardown and GPU modes.
Review API hash/version initialization and sandbox/cache/resource paths.

[PR 1773](https://github.com/CasparCG/server/pull/1773) was merged on 2026-09-30,
after the 2.5.1 release. It addresses Linux utility subprocess stack-guard
crashes and merits independent backport review even before a CEF version change.
Fresh GitHub API state was used because the cached web page still showed Draft.

[PR 1730](https://github.com/CasparCG/server/pull/1730) restored shared textures
and was merged 2026-03-24. The accelerated texture-import implementation in our
HTML producer remains WIN32/D3D-only. A newer Linux CEF does not automatically
turn the CPU OnPaint path into zero-copy GPU import. CEF
[issue 4237](https://github.com/chromiumembedded/cef/issues/4237) concerns NVIDIA
native-handle OSR images; importing those into Caspar's OpenGL context is a
separate future optimization, not a prerequisite for updating the SDK.

Engineering estimate: moderate, roughly 2–5 focused days for integration and
baseline Linux validation if no regressions surface; broader platform/template
validation may extend that. Download/build time is not the main uncertainty.
No performance gain is guaranteed: kavtor's MV/wipes/DME are now native, so CEF
primarily affects actual HTML inputs and CG templates.

## Decision — deferred to upstream

On 2026-10-07 the operator decided to keep current FFmpeg/CEF dependencies and
wait for upstream updates. Dependency modernization is outside the current
casparMIX patch scope. No migration, dependency pin or package change was made.
This assessment remains evidence for evaluating the next official stable base.

CEF's Chromium media implementation and Caspar's external FFmpeg libraries are
separate dependencies; upgrading one does not update the other.

## Sources and local evidence

- [FFmpeg releases](https://ffmpeg.org/download.html)
- [CasparCG releases](https://github.com/CasparCG/server/releases)
- [Upstream Linux bootstrap](https://github.com/CasparCG/server/blob/master/src/CMakeModules/Bootstrap_Linux.cmake)
- [Official CEF build index](https://cef-builds.spotifycdn.com/index.html)
- CEF 154 headers: upstream commit 14c5a08, include/cef_render_handler.h,
  include/cef_life_span_handler.h, include/cef_audio_handler.h.
- Local probes/results: /tmp/casparmix-dependency-review/ffmpeg9-compile.json,
  ffmpeg9-header-proof.txt and filter-option-8.1.txt / filter-option-9.txt.
