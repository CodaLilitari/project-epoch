# Battle exploration history, 2026-09-08

This is the preserved discovery history behind the accepted alternate-resolver
observation and the unsuccessful Life2 route. It records 17 private runs and
keeps their evidence distinct from the later focused, repeated experiments.
The [metadata census](../references/battle_exploration_history_20260908.json)
pins every historical manifest and trace, verifies the retained staged Lua,
and records source availability. No trace, ROM, SRAM, state, screenshot or
extracted game data is included in source control.

The discovery observations remain `hypothesis` for integration purposes.
The census verifies historical file identities and event counts; it does not
retroactively apply a stronger validator or accept the old broad observer's
completion claims. The later [accepted alternate report](schala_package_resolver_alternate_v1.md)
is the authority for the actual Black Hole/Spekkio result.

| Discovery group | Runs | What the bounded routes established |
| --- | ---: | --- |
| Initial menu and hit/evade inspection | 2 | Baseline/menu context, with no player resolver entry |
| Crono Spincut and left/right variants, then accuracy instrumentation | 4 | One observed primary-branch entry per route; no alternate branch |
| Marle menu timing | 3 | Menu/setup refinement with no player resolver entry |
| Marle Provoke | 2 | One observed primary-branch entry per route |
| Lucca Hypnowave | 1 | One observed primary-branch entry |
| Spekkio conversation setup | 1 | Battle setup with no player resolver entry |
| Spekkio/Robo Rocket variants | 2 | One observed primary-branch entry per route |
| Spekkio/Magus Black Hole | 1 | The alternate `$0040` branch was discovered; later replaced by the accepted focused pair |
| Marle Life2 against a living party | 1 | Seven records: baseline, five menu observations and terminal; no queued action or natural refusal |

The final broad Black Hole discovery has 3,793 records and 42 publication
bytes. Its ordinary branch input is `$0040`. These discovery counts differ
from the accepted focused observer's 3,783 records because they are separate
collectors. They are not inconsistent repetitions of one frozen experiment.
The Life2 route's absence of a queued action is limited to its fixed inputs;
it does not establish a universal targeting or cancellation rule.

The exact current alternate launcher and Lua match the final Black Hole
discovery. Fifteen earlier runs retain their historical source hashes and
staged Lua, but their launcher revisions are not present in this packet as
matching current files. The original broad runner also did not retain a
prelaunch receipt. This is a history gap, which the census states explicitly.
Do not substitute the final launcher for an earlier revision and describe
the result as an exact historical reproduction. The new accepted observers
archive their guarded sources before launch and check those copies afterward.

Life2 has a prelaunch receipt and all five original archived sources. The
historical launcher imports the accepted transaction validation module only
for its exception type; its own exploratory summary does not accept a
transaction. Its recorded reproduction directory is still named
`package_transaction_NEW`. That is an output label in a retained command,
not a claim that a transaction was observed. The source remains unchanged.

Preserved original source endpoints:

- [Alternate discovery launcher](../tools/run_package_alternate_branch_probe_v1.py)
  and [Lua collector](../tools/mesen_package_alternate_branch_probe_v1.lua).
- [Life2 discovery launcher](../tools/run_package_refusal_probe_v1.py)
  and [Lua collector](../tools/mesen_package_refusal_probe_v1.lua).

Reproduce the metadata without launching or mutating a game:

```powershell
python -B tools/collect_battle_exploration_history_20260908.py
```

The read-only collector validates the fixed 17-manifest allowlist, every
recorded trace hash and count, every staged collector identity, and the
available Life2 source archive against its recorded five-source set. It emits
UTF-8 JSON with LF and one trailing newline. Its source hash is included in
the resulting reference. Reproduction requires the preserved private packet;
the public repository deliberately supplies original tools and metadata only.

The next useful work follows the accepted focused proofs. Repeating these
discovery routes adds no acceptance evidence unless a changed boundary,
source drift or new failure makes a fresh experiment necessary.
