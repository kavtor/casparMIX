# casparMIX

An additive, versioned GPL patch set for CasparCG Server. Apply it to the pinned
upstream stable source: keep CasparCG commands/modules and gain native mixer
primitives. [kavtor](https://github.com/kavtor/kavtor) is a separate mixer brain;
M/E scheduling, source assignments, panel behavior and UI belong there.

## Current release

**CasparCG 2.5.1 + casparMIX 0.18.0**, pinned to upstream `v2.5.1-stable`.
The combined distribution patch and ordered individual patches live in
[releases/casparMIX-0.18.0-casparcg-2.5.1](releases/casparMIX-0.18.0-casparcg-2.5.1).
The patch is a distribution format; internal changes remain individually
reviewable and can be proposed to upstream. No full engine fork is duplicated here.

```sh
# In a clean CasparCG 2.5.1 stable source checkout:
patch -p1 < /path/to/casparMIX-0.18.0-casparcg-2.5.1.patch
# Then configure/build/package CasparCG using your normal platform recipe.
```

Preserve the manifest, checksum file and upstream pin when packaging. Added
dependencies relative to upstream: FreeType and a readable TrueType font for
native graphics (for example DejaVu Sans). FFmpeg/CEF pins follow the currently
validated upstream-compatible recipe; independent dependency upgrades are deferred.

## Native operations

Rendered whole-channel routes, shared progressive clocks, Sony-numbered wipes
with live softness/borders, native DME planes/page meshes, source-aware MOVE,
alpha/LUMA processing, standard color bars, cached multiview graphics and
consumer-free audio metering. Existing upstream commands remain available.
The banner preserves the upstream version and appends the patch version.

Current catalogues: 83 wipes and 72 DME presets. Pending IDs reject execution
rather than silently substituting an effect. Operator review and performance
limits are documented. SPLIT 1011–1013 use operator-confirmed NORM entry and REV exit (issue #2).
Edge-hinged 1041–1048 now distinguish far/near entry (issue #9).

## Development and validation

```sh
python3 tools/verify_release.py --release releases/casparMIX-0.18.0-casparcg-2.5.1
```

This checks SHA-256 and applies combined/ordered forms to the exact upstream
commit, requiring identical resulting Git trees. Native pixel/audio tests in
`tools/` require a built engine and a usable GPU session; their recorded results
are in `validation/`. CI patch checks do not replace those runtime tests.

Published release patches are immutable historical source artifacts: old project names in their comments are retained to
preserve their checksums and reproducibility. Current documentation and tools use
kavtor.

- [Commands](docs/COMMANDS.md), [changelog](docs/CHANGELOG.md)
- [Timing](docs/TIMING.md), [capacity/performance](docs/PERFORMANCE.md)
- [Dependencies](docs/DEPENDENCIES.md), [roadmap](docs/ROADMAP.md)
- [Sony catalogue](docs/SONY-CATALOGUE.md), [deferred transports](docs/TRANSPORTS.md)

GNU GPLv3, preserving CasparCG upstream notices. This is an experimental
additive patch set, not an official CasparCG release or a guarantee of arbitrary
hardware/output capacity. Use issue → PR → reviewed merge for changes.
