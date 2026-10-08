# Open engine work — casparMIX

Reviewed against 0.17.0 on 2026-10-07. kavtor owns mixer semantics, configuration
and operator UI; casparMIX owns reusable producers, composition and timing.

## Current

- Remaining key composition primitives for separate fill/key, pattern keys and
  DVE key processing. Native LUMA, alpha inversion and rectangular mask/inversion
  are implemented; preserve shared-input isolation and upstream commands.
- Complete the individually reviewed Sony DME catalogue and unresolved wipes.
  Current native catalogues: 72 DME and 83 wipes. Unknown presets remain explicit
  pending errors, not aliases. Inferred motion requires operator review.
- Page/roll backside materials and optional projected shadows, with independent
  live preview preparation and no HTML/video readback path.
- Stinger/track-matte readiness, synchronized fill/matte sampling and frame cut
  primitives as required by kavtor's complete stinger implementation.

## Reliability and performance

- Measure progressive A/V content drift before adding compensation or changing
  queues; packet timestamps alone do not establish lip sync.
- Expose measured consumer delivery/loss and NDI receiver counters where available.
  Do not label whole-interface traffic as an individual output's bitrate.
- Continue measured optimization without removing existing upstream functionality.
  Minimum progressive target: 60 fps; qualify defined workloads at 75 fps for
  headroom. Native composition and local PGM/MV NDI passed the initial test;
  longer soak tests and additional output/encoding consumers remain.
- Evaluate GPU allocation only with a concrete resource/timing benefit; preserve
  texture lifetime and coherent frame epochs across any new boundary.

## Later engine extensions

- Restricted external AMCP endpoint for owned CG/playout channels, including
  route-reference validation and rejection of global destructive commands.
- Same-epoch regional backdrop blur with an independent coverage mask.
- Evaluate OMT upstream module/backport; ST 2110 remains deferred.
- FFmpeg/CEF version upgrades are deferred to upstream; retain current dependency
  pins and evaluate official stable updates rather than implementing our own migration.
- Native capture/replay and additional producers/consumers when their contracts
  have been agreed. No yt-dlp/streaming transport is implied by existing modules.
- Broader mesh/3D primitives as effects require them; a game runtime is unnecessary
  for the projected planes and page meshes already implemented.

## Distribution and upstream

- Maintain tested combined patch and ordered commit series against pinned stable.
- Rebase/review on the next upstream stable, eliminating patches superseded there.
- Select upstreamable fixes and propose them as separate issues/PRs.
- Review licenses/attribution and publish the fork/patch repository.

Rendered whole-M/E routes, frame-clock synchronization, native wipe/border
compositing and native generic multiview graphics are implemented and are not
listed as future work. See CHANGELOG and validation captures for their evidence.
