# Canonical-donor package preflight planner v1

Date: 2026-09-08. Status: `verified-static`, independently reviewed source-only
implementation with a byte-reproducible metadata reference.
The report below describes host decisions; no game hook, image, native
preflight, cleanup or action completion is installed or approved.

The planner now distinguishes three situations using two accepted canonical
battle observations. The observed Luminaire action can preserve its original
primary package, or supply an exact donor for a deliberately associated
synthetic package. The naturally refused Cure stops at its earlier
target-validation boundary and supplies no package eligibility evidence.

The reviewed [design](schala_package_preflight_planner_design_v1.md) is kept
unchanged as the architecture receipt. Its source SHA-256 is
`8d569df20932b81d59a6f7f072de729cf046d179cdbd099fee6d0c944d9def05`.
Both root and a separate implementation agent independently reviewed that
design before implementation began.

| Request and context | Host decision | Meaning |
| --- | --- | --- |
| Original canonical action/config `$08`, exact observed pre-effect context | `canonical-path-preserved` | No replacement is requested; the authored-stream policy makes no new assertion about vanilla command data |
| Same context, only config byte `+0` replaced by `$80`, explicit immutable synthetic association | `transport-valid-source-only` | Both descriptor masks and every declared direct stream pass the existing command policy |
| Observed queued Cure `$0C` after its selected target died | `native-target-refusal-observed` | The accepted early refusal is retained; donor and package eligibility are not evaluated |
| Diagnostic replacement with no explicit association | `unbound-diagnostic-package` | The default high-selector registry remains empty |

The [pure context planner](../tools/schala_package_preflight_planner_v1.py)
checks exact immutable schemas, the declared snapshot profile, queue and
participant consistency, donor equality and explicit association. It performs
no file access. Its positive candidate result is only
`requires-package-policy-validation`, bound to source/layout hashes.

The [read-only auditor](../tools/audit_schala_package_preflight_planner_v1.py)
revalidates the previous successful/refused native pairs and their private
source archives, verifies the canonical ROM identity, and reconstructs the
donor in memory. It separately invokes the existing pinned package policy on
the immutable source. It accepts no supplied certificate or skip-validation
option. The existing policy's own file reads stay outside the pure context
function.

## Donor and evidence limits

The new donor is physical action-config row `$08`, file `$0D45DE-$0D45E5`,
half-open. Its seven-byte SHA-256 is
`044dfdb673f9506789daf42470a7d5173f70354169f6ecc5006235783a46b334`.
Only byte `+0` changes; the preserved `+1..+6` SHA-256 is
`642eb9302b2906890aceb5baf58a28e11dfdaff1ed15d1233db7c401bb5f1a96`.
The candidate row SHA-256 is
`9c747786b110ff2b63c293e3cacefa0fb84e436f48257cd139742e0a339dbf3e`.
Neither row's byte payload is emitted or tracked. The earlier symbolic
donor-`$01` proof remains unchanged.

Preserving the six suffix bytes includes auxiliary fields `+3/+4/+5`, whose
native readers still depend on fixed banks. This is source-derived equality;
the accepted observation did not independently capture every live auxiliary
field or CPU row read. It does not establish compatibility of new primary
commands with those auxiliary assets.

The successful context is the exact `$C1BBD4` pre-effect snapshot from the
[Luminaire transaction](schala_package_transaction_observation_v1.md). The
refused context is the distinct `$C1BB8B` snapshot from the
[natural Cure refusal](schala_package_natural_refusal_observation_v1.md).
At the latter boundary the animation identity still contains earlier work.
The planner retains those stale fields rather than inventing a Cure pre-effect
state. Both accepted observations use a prepared checkpoint and controller
input after its exact state load; this source audit launches no emulator.

The current zero `$B3C8` value is an exact-profile requirement, not proof that
MP/status validation has run. Native validation occurs later inside preparation.
Likewise, a terminal `$00` stream's transport validity does not prove that the
caller receives its required completion signals. Every decision keeps
production, cleanup, completion and native-integration approval false.

## Verification and reproducibility

The frozen implementation passed 33 focused host tests, independently repeated
by root during code review. Their donor bytes
are original synthetic test data under scoped, test-only hash substitutions;
they do not claim to be canonical data or a captured native state. A separate
read-only audit uses the real pinned ROM and revalidated accepted traces.

The adversarial tests cover every donor/queue byte mutation, preserved suffix
changes, missing/duplicate associations, logical PC `$07`, high action IDs,
bad or duplicate participant mappings, changed CPU/stack/decimal context,
relabeled refusal snapshots, mutable inputs and boolean integers. Policy
controls reject a broken alternate descriptor and decoded alternate `$1E`,
while accepting an original valid raw operand `$1E` vector in the planner's
synthetic bank namespace. Completion claims are explicitly rejected.

During initial unit verification, two assertions needed correction: the policy
also validates its own dependency conformance vector, so the test now counts
calls on the actual candidate envelope; and the reusable raw-operand vector
uses a different synthetic bank, so its test identity is explicitly relocated
to this planner's bank `$42`. Neither change altered the accepted game
observations or the policy implementation.

```powershell
python -B -m unittest discover -s tests -p test_schala_package_preflight_planner_v1.py -v
python -B tools/audit_schala_package_preflight_planner_v1.py
```

The closed
[metadata reference](../references/schala_package_preflight_planner_v1.json)
is 14,779 bytes, SHA-256
`cd14a36b8d4e725349b1c3256fd2fb36e65a5be9597029998a4bf8273d58f0a9`.
Root independently reproduced the initial in-memory result before clearing
reference generation. A final review requested explicit UTF-8/LF stdout in
place of platform-dependent text output. Only the auditor's output write was
changed; planner, tests and design remained frozen. The auditor-bound reference
was regenerated, and two normal CLI runs now match that reference byte-for-byte
with empty stderr. No JSON or newline normalization is needed.

The earlier metadata SHA-256
`91bcb8f75623a6eb397d2c0e858f511ac67227611be6e690036dbe44469b7df8`
belongs to the pre-serialization-correction auditor and is historical. Its
decisions were unchanged; its different auditor source identity prevents it
from certifying the final revision.

| Frozen implementation | Bytes | SHA-256 |
| --- | ---: | --- |
| Pure context planner | 15,049 | `5b5848d0e47d5c068d61e3728d3044137ac26bcad1da3ba301c28f6b6ebf9640` |
| Read-only auditor | 16,567 | `68aff1f41f379f10deb1a293e57b5bb780486079c5c4ef459dc99f3946ebc4a4` |
| Host tests | 15,742 | `2180e966ca1005c1a40248411a2b84f091d7f9f747c414bbe28935ed37966b1c` |

The native trace, checkpoint and source-archive evidence is reused and
revalidated, not newly executed. Only this source-only metadata reference was
generated. The auditor has no output-file option and verifies its computed
result against that reference before printing it. Reconstructed canonical
donor bytes and raw trace payloads remain private/in memory.

## Next boundary

This result supports planning a future native preflight. It does not authorize
a rejection jump to `$C1BC5A`: the successful pre-effect path has performed
additional animation and target-mask work that the natural early refusal
never performed. The accepted observers cover declared watched ranges, not
full WRAM ownership or the equivalence of those earlier writes.

Native placement, instruction preimages, interrupt/stack behavior, cleanup
from the proposed boundary and a compatible action-completion protocol remain
separate requirements. Late helper refusal remains a failed experiment until
a separately reviewed recovery design exists. All production package and
allocation catalogs remain unchanged.
