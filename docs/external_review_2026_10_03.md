# External review receipt and independent disposition

These were bounded source/text reviews on existing subscription routes.
Model labels are client observations, not independent backend attestations.
No reviewer received a ROM, SRAM, checkpoint, raw game trace or unrelated
project material. Only explicit source packets were supplied. Review output
is advice; the coordinator checked consequential claims independently.

## Returned Antigravity packets

The installed Antigravity 1.2.8 client exposed the previously selected
`gemini-3.1-pro-high` / `high`. Its official readiness check showed both
included-usage windows available and `use_g1_credits=false`. Two packets
returned through the tool-denied isolated route:

| Packet | Hub job | Provider session | Result |
|---|---|---|---|
| Conditional HDMA timing | `4ac378e9918c449988d2f03c7998dcbd` | `de7e61a7-f233-4f89-aba4-bfd9d5b41a2a` | Returned; arithmetic/source advice checked |
| Phase-v3 source review | `9181e5480b9845c3926a81c3dd9725a4` | `92c0c381-0d74-47f0-9132-dac38296a05e` | Returned; five objections dispositioned below |

The first review's support for the finite-prefix inequality, 216-clock
initialization and 472-clock transfer bounds agrees with the already accepted
source calculation. Its explicit omitted-source limitations are retained.
Its additional wrap example gives `(261+65275) & 65535 == 0`; that is another
conditional cache-overflow illustration, not a new native experiment or a
configuration admitted by our zero-extra launcher. Nothing promotes the
HDMA calculation to game admission.

The second review is deliberately preserved as disagreement rather than
summarized as a clean approval:

1. **Savestate replacing the zero-extra guard:** the reviewer correctly notes
   that hidden cached PPU values load from a state and are not directly observed.
   That is already an explicit premise of v3. It conflates cached values with
   the separate CLI configuration, which `UpdateNmiScanline()` later reads.
   A crafted replacement state fails the launcher's exact state hash. The
   bootstrap premise remains open; the claim that this invalidates the narrow
   crossing observation is not accepted.
2. **Counter values must use alleged physical limits instead of uint16:** the
   new fields are typed snapshots of Mesen's serialized uint16 members. V3
   intentionally validates that domain and claims no transition/deadline proof.
   Accepting a synthetic 60000 test value demonstrates that limit of the
   structural validator, not native observation of such a value. A future
   counter-transition theorem must prove its reachable domain separately.
3. **An instruction can skip line-zero H=1364 and lose overshoot:** rejected
   for the pinned runtime. `SnesMemoryManager::IncMasterClock*` expands into
   two-clock `Exec()` steps. `Exec()` checks the next scheduled event, and the
   end-of-line event retries at 1360, 1362 and 1364. An instruction is not an
   atomic jump over these events. See the exact
   [memory-manager source](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesMemoryManager.cpp#L131)
   and [PPU boundary](https://github.com/SourMesen/Mesen2/blob/137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1/Core/SNES/SnesPpu.cpp#L395).
4. **Renamed copied run directories can fool an offline pair auditor:** accepted
   as an evidence-authentication limitation. Hashes, inventories and process
   receipt checks do not authenticate execution against fabricated unsigned
   receipts. The auditor now explicitly reports
   `execution_authenticated_against_fabricated_receipts=false`. The two actual
   process invocations remain separate recorded coordinator/tool evidence.
   This limitation is not represented as a cryptographic guarantee.
5. **Cache-event CPU/stack/game fields are absent from v2 equality:** correct
   that these are new observations, since v2 has no corresponding events.
   They are not unvalidated: v3 calls the frozen common record validator,
   validates the event/execution address, requires exact crossing timing and
   historical NMI bracketing. Equality is asserted only for the retained v2
   projection. This does not authenticate invented JSON or prove all new game
   values through a second historical source; no such claim is made.

The first review was thanked in the next packet, explicitly labeled a new
isolated review. The hub exposes no native continuation for these sessions;
no same-session follow-up or acknowledgment delivery is claimed. Raw responses,
request/attachment hashes and helper receipts remain private in the shared
review hub and `private/reviews/20261003b/`.

## Other routes and unresolved state

Claude Code's fresh usage UI showed included Pro capacity with usage credits
off. Job `8cf82ea83be948d89d7af51a80e106fe` attempted the design review at
the saved Opus/max choice. The helper reached its 1,800-second deadline:
`status=timeout`, `submission_attempted=true`, `model_review_completed=false`.
The hub labels delivery unknown. No answer or independent approval is claimed,
and no automatic resend was performed. This is separate from the historical
earlier timed-out job.

Grok Build initially refused unrelated user-skill discovery. A non-generating
probe established that a per-child empty `USERPROFILE`, preserving normal
`HOME` and the dedicated `GROK_HOME`, passes the unchanged startup guard and
retains subscription login. Its current catalog still exposes the saved
Grok 4.7 / xhigh choice. The official background `/usage` UI showed SuperGrok,
17% weekly use and no model calls in that session. The paid-extra setting was
not established by that UI, so dispatch initially remained pending. Andrei
then explicitly confirmed that paid extra usage is disabled. One bounded
Grok 4.7/xhigh review of the next IRQ-request model was started through the
unchanged official helper under the verified per-child isolation. The exact
19,400-byte packet hashes to
`46b93615f46f66176ae87b7678f183db05fbfde926e44f39828062a7396bcaf9`.
It contains only two Mesen source files and our scoped question. Results are
pending at this checkpoint; do not equate dispatch with review completion.
The temporary usage process was closed; normal configuration and billing were
not changed. Helper receipts are in
private/reviews/20261003b/grok_irq_review_live/.

Native subagent dispatch hit this old chat's thread limit. A new authorized
project chat can continue from the committed handoff with fresh agent capacity.
Do not relabel any failed/blocked route as completed review or shared consensus.
