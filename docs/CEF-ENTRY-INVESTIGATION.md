# CEF subprocess entry investigation

Tracked in issue #4. This candidate is not part of a distribution release.
Linux core traces show `__stack_chk_fail` in `html::intercept_command_line`,
with CEF subprocess arguments enabling stack-guard changes on fork. CEF
requires a no-stack-protector boundary on that call chain. The candidate keeps
application-wide protection and the existing dependency version, annotates
only the handoff and terminates completed child processes without returning
through protected pre-fork caller frames.

The candidate compiles. A subsequent native audio attempt still did not reach
AMCP readiness within its startup deadline, so this is not a validated startup
fix and must not be applied by packaging. No new core was reported during that
attempt, but that is not proof of correctness. Diagnose the remaining startup
block and validate parent/child clean shutdown before release.

References:
- https://github.com/chromiumembedded/cef/issues/3912
- https://github.com/chromiumembedded/cef/blob/master/tests/cefsimple/cefsimple_linux.cc

No raw cores, personal configuration or private endpoint logs are distributed.
