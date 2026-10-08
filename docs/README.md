# casparMIX

An additive engine patch set for CasparCG Server. The original numeric version,
commands and modules remain available. The version banner additionally identifies
casparMIX. kavtor is a separate mixer application; panel logic, delegations, server
profiles and UI belong there, not in this engine.

## Development and distribution

The `upstream` remote tracks the official repository. Each engine change is a
separate commit based on the exact stable tag and commit in `upstream.json`.
No public fork has been created yet.

Run `python3 casparmix/tools/export_release.py` from a clean committed checkout.
The ignored `casparmix/dist/` directory contains a combined patch, an ordered
individual patch series, a manifest and SHA-256 checksums. The exporter verifies
both forms against the exact upstream Git tree and requires identical results.
Apply the combined patch to the official source with `patch -p1 < FILE.patch`
before configuring CMake. Distribution-specific Boost, CEF and FFmpeg adjustments
remain in the package recipe and are excluded from this patch set.

For a new upstream stable release, review changes and replay each engine commit,
then update the pinned base and regenerate and validate the release. Do not update
only the tag while retaining an old commit. Regenerate after every validated release.

## Scope of 0.4.2

* Add reusable native graphics scenes with cached text/shapes, animated bars and a heartbeat watchdog.
* Add static standard color-bar patterns and correct the BT.601 green matrix.
* Preserve the 0.1.0 route readiness and consumer-free audio metering changes.
* Avoid division by zero and invalid picture transforms in one-frame transitions.
* Add opt-in GPU-rendered whole-channel routes for isolated compositions.
* Add native Sony wipe geometry, manual progress, live modifiers and drawn borders.
* Add opt-in shared progressive frame clocks and current-frame cross-channel routing.
* Discard stale pipeline frames when rendering resumes after an idle interval.
* Preserve the upstream numeric version and expose the additional patch version.

See `COMMANDS.md` for syntax and limits, `CHANGELOG.md` for validation and
`DEPENDENCIES.md` for packaging. The engine owns reusable picture/audio operations;
kavtor continues to own M/E scheduling, bus selection, panel behavior and UI.

Run `python3 casparmix/tools/regression.py --binary /path/to/casparcg --rendered --sony`
for isolated lossless capture regressions. This starts its own temporary server;
it does not connect to an existing production instance. It requires a usable GPU
session and FFmpeg tools. Artifacts include AMCP transcripts, server logs, captured
videos and `results.json`. Patch round-trip checks do not replace these tests.

See `TIMING.md` for shared-clock configuration, measured route latency and limitations,
and `TRANSPORTS.md` for deferred OMT/ST 2110 integrations and upstream references.

Sony catalogue 0.7.0: see [implemented masks and validation](SONY-CATALOGUE.md).

DME producer specifications in 0.7.1 preserve quoted image filenames (including spaces)
and options for backgrounds and MOVE tracks. Legacy registry parsing is unchanged.
