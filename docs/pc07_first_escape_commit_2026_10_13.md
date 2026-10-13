# Project Epoch: first native escape commit, October 13, 2026

**Logical PC07's battle state now reaches its own live character record through
the game's native copy routine.** One prepared diagnostic completes a real
ordinary Attack, regains actor readiness, accepts held L+R, and reaches the
first escape work-to-live commit. Independent offline review reproduces the
result exactly. The playable-eighth-character goal remains active and incomplete.

This is the next persistence boundary after the
[ordinary-Attack checkpoint](pc07_first_attack_checkpoint_2026_10_13.md).
The separate [Schala presentation run](pc07_schala_presentation_2026_10_13.md)
already shows retail Schala graphics and the full six-letter battle name.
**The escape experiment uses the unchanged Crono-donor Attack image.** The
Schala screenshot illustrates that separate appearance milestone; it must not
be presented as an image of this escape run or of a finished playable release.

The escape-enabled encounter is deliberately authored. The existing pure event
transform changes exactly offset `$0547` of the accepted 1,914-byte destination
packet from `$93` to `$13`. The validator checks the actual new flag and its
native consumers; it does not replace `$13` with `$93` in the evidence. This is
not a claim that the retail Lavos encounter permits escape. The ROM image is
unchanged; the event is staged through the existing explicit debugger
preparation route.

The full run includes 4,642 recorded debugger byte-write/readback pairs for
the independent record, roster, compatibility relocation and selected events.
There are no debugger CPU edits or fabricated queue entries, action results,
escape counters or commit results. Recruitment and event installation remain
diagnostic preparation. After the native Attack and readiness sequence,
controller input holds L+R. Actual hardware reads qualify 220 native counter
increments; 101 native escape-request publications are observed before the
main loop takes the selected escape path. These are observed counts for this
run, not a universal escape latency or exactly-120-tick result.

At `$C18215`, the game calls `$C1B442`. The unchanged routine reads 80 bytes
from each active battle work record and writes the live record selected by
the roster identity. All **240 source-read / native-write / immediate-snapshot-
readback triples** are checked independently and by the frozen validator:

| Active slot / logical PC | Work source | Live destination | Live HP before commit | Work HP at commit entry | Live HP after commit |
| --- | --- | --- | ---: | ---: | ---: |
| 0 / 00 | `$7E5E2D` | `$7E2600` | 969 | 739 | 739 |
| 1 / 01 | `$7E5EAD` | `$7E2650` | 898 | 603 | 603 |
| 2 / 07 | `$7E5F2D` | `$7E2830` | 968 | 608 | 608 |

PC07's 608 HP remains distinct from donor PC00's 739 HP. These are live-state
commit values, not an attribution of every HP loss to a particular attack.
The earlier live records remain unchanged until the witnessed copy writes.
PC00 and PC01 legitimately receive their own battle results; preserving the
original characters does not mean preventing their native HP updates.

The fresh precommit snapshot matters: native cleanup has already changed
work offset `$23` from `$FF` to zero for all three actors, and offset `$26`
from `$40` to zero for PC01. Actual stores at `$C1EABC/$C1EAC5` and later
snapshot readbacks confirm those values, including same-value zero stores for
the other actors. Status-region bytes `$1D..$26` are zero in all three live
records at the cut. Other copied changes at `$3D/$3F/$40` are recorded without
inventing semantic labels. An earlier readiness snapshot is not substituted
for the source state at commit entry.

The observed near return passes `$C1B487` and reaches **`$C18218`, before the
inventory commit**. The ledger ends there. All 26 full SRAM snapshots equal
the input, and all 26 WRAM snapshots preserve the five inactive original
records 02–06 and all 48 stored-name bytes, including Epoch's separate name.
The original active identities00/01 and candidate07 remain independent.
Compatibility and declared guards pass the inherited checks; the bootstrap
rear guard is `$2CF0..$2CFF`, not the earlier field-only extension from `$2D00`.
These checks do not establish vehicle boarding, travel, appearance or save/load.

There are 402,532 trace rows in one successful run, not a repeated pair.
The review rehashes 124 source rows, 95 recorded run artifacts, 11 original inputs
and six staged runtime files, and reconstructs all 13 staged inputs. Both
archived intent and complete-diff audits pass for the existing image's 481-byte
difference from its inert scaffold. The earlier guard is explicitly resolved
from its preserved archive; changed live guard sources are not silently
accepted. Three focused synthetic review tests pass, separately from native
execution. Two early PNG files are empty; every required WRAM/SRAM snapshot
exists. No screenshot or raw game payload is included in this repository
checkpoint.

Principal SHA-256 identities are:

| Evidence | SHA-256 |
| --- | --- |
| Frozen launch source bundle | `9cd03aa10f60f8f912c2852861d4d2c7dc6a23bd7d6d5e2b67c6d0772c866ca3` |
| Unchanged private Attack image | `6d420e3daa6761a6ca2b0dd6bfc9119aa15967124f92c5d731a431f76726eefa` |
| Authored destination event | `13879385d478acbdab1c92c1289414fcfb4761e50b4d913928a34964686341c4` |
| Original run receipt | `0d4bf2fa68ee9af3136c85644267dd864338242728e2493b37d715ff69e1b468` |
| Raw trace | `51ae3ffb9be98d6eac1ab8c225e71b689dd4bc1048b1b7a6f122b22767e34942` |
| Independent review receipt | `3ff22606f13a1919e32d227c9c22af9eadac30931685c59ed6a619129b288556` |
| Independent review reproducer | `7a5bed1ad7cd0e08f2ecf07190eacf415d1fa1bd9aea5270b7365af1ed427f32` |

The original run is `private/test_runs/pc07_escape_commit_v2_run1`; the additive
review is `private/research/pc07_escape_commit_independent_review_20261013`.
Its 19,794-byte receipt reproduces byte-for-byte. The main task independently
executed the reproducer again and saved its stdout as `root_reproduction.json`,
SHA-256 `6452dd26aacc9de970c6677ebcefcc6654ae1f47fe7b2ed6e2d2da5ea2c015ef`.
That JSON agrees with the accepted receipt. Windows stdout uses CRLF plus one
extra print newline; normalizing CRLF yields the exact receipt plus one LF.
The reproducer internally verifies exact receipt-byte equality.
The historical run receipt
retains `collected-awaiting-independent-route-review`; qualification is recorded
additively. Private paths identify evidence, not distributed assets.

The public [machine record](../references/pc07_first_escape_commit_2026_10_13.json)
is curated by a read-only source auditor. For a holder of the exact private
fixtures, reproduce it without launching an emulator or emitting an image:

```powershell
python -B tools/audit_pc07_first_escape_commit_2026_10_13.py
```

The public source and metadata support inspection; native evidence cannot be
reproduced from the public repository alone without the private inputs. The
auditor emits metadata only. ROMs, extracted event bytes, saves, states,
screenshots and raw traces remain excluded from Git.

This work reuses the community's event/party mappings, the existing native
serializer and record research, and the accepted parser/transform and Attack
adapters. See the [historical mapping audit](historical_eighth_character_forum_mapping_audit_2026-08-23.md)
and [event parser audit](location_event_item_reference_audit.md) for attributed
sources and corrections. No novelty or first-discovery claim is made.

The next gate is the later inventory merge, second live-record commit and
actual field restoration. `$C18218` is not final field-return state: a later
path performs another copy after HP/status changes. Deferred emulator shutdown
is outside the authoritative ledger, and its battery file is not a save result.
Normal saving/cold-loading, recruitment, broader menus/Techs, Schala-appearance
integration with this return route, and Epoch vehicle behavior remain open.
This checkpoint does not mark the goal complete or provide a playable release.
