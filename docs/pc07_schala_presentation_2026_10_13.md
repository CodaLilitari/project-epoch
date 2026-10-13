# PC07 retail-Schala presentation, October 13

Status: Schala is visibly rendered as PC07 in a continuous field-to-battle
diagnostic, with the full six-letter battle name. One native v2 run is recorded
and independently reviewed. The original run receipt retains its failed
final-buffer assumption; an additive temporal validator qualifies the unchanged
trace without claiming persistent name tiles or a captured VRAM-upload ledger.

Andrei requested Schala's retail NPC graphics and the full name **Schala** for
logical PC07, using copies of her retail poses where player poses are missing.
The accepted Crono-appearance field/Attack diagnostic remains unchanged as the
comparison baseline. This is an additive PC07 presentation change, not a
replacement of Crono, Lucca, the NPC Schala, or the Epoch vehicle.

## Reused evidence and new provider

The existing canonical-ROM-derived provider and its accepted supported-Lucca
field replay are described in
[the original provider report](schala_vanilla_npc_source_compatibility_v0.md).
They already establish 79 raw graphics tiles, 23 assembly records, four retail
facing blocks, and a twelve-color palette. No new graphics download or artwork
generation is necessary. The original provider and its old diagnostic remain
unchanged; the new compiler imports their pinned sources.

`tools/build_pc07_schala_presentation_v1.py` currently derives the graphics and
assembly exactly, preserves the first nine animation cells by numeric position,
and fills selectors 9..255 with each facing's exact retail entry-zero cell and
matching timing. Numeric cell preservation is not a complete semantic mapping
of NPC animation names to playable-character poses. Missing battle poses will
therefore be visibly repeated retail poses, as requested, rather than new art.

Each facing and the timing block has an extra copied guard cell. The resulting
stride is `$0404`, covering the battle initializer's eight-byte reads even for
selector255. All 1,024 facing/selector combinations have bounded frame and
timing termination. Four focused tests check exact retail payloads, all copied
fallback cells, disjoint bank-contained spans, and canonical-source refusal.

The proposed private provider spans are:

| Component | CPU start | Bytes |
| --- | --- | ---: |
| Raw graphics | `$420000` | 2,528 |
| Assembly | `$421000` | 920 |
| Four guarded primary facing blocks | `$424000` | 4,112 |
| Guarded timing block | `$425100` | 1,028 |

These are named private diagnostic placements. No production allocation or
global graphics-source index has been approved. Every extracted payload remains
local and ignored; source-controlled reports contain metadata only.

## Name and integration boundaries

The vanilla battle name path has five-byte buffers and five-cell draw loops.
The separate original name component stores all six authored letters in ROM,
uses the existing five-byte candidate buffer for the prefix, and appends the
sixth glyph through a PC07-specific status-panel helper. It leaves the seven
original stored names and Epoch's `$7E2C4D..$7E2C52` unchanged. Display type2 is
the selected diagnostic premise; type1 puts its gauge in the sixth cell and is
not silently admitted. This is not yet an editable name, menu/dialogue name
resolver, or serialized name implementation.

The new graphics helpers retain the existing logical identity and donor action
adapters. They qualify the actual PC07 object/slot before changing that object's
graphics, assembly, palette key, animation bases or stride. Separate fixed-bank
animation readers need adaptation; changing only the NPC descriptor or only
one battle frame reader would be insufficient. Actual native pointer/asset
reads, the inherited field-to-battle palette, sampled stack/register
preservation, original-character controls, and the visible six-letter display
are checked by the bounded native observation described below.

The new private write contract is sealed to its reviewed precise
source/section recipe. It reconstructs the unchanged accepted
first-Attack image, pins every new preimage and payload, requires full boot-bank
mirror/checksum consistency, reverses the new sections back to the accepted
image, and audits the complete inert-source-to-target difference. Both shared
guard APIs passed before the new private image was emitted, and fresh assembly
reproduced both original components. The recipe declares 23 new sections; the
full result differs from the inert scaffold in 8,892 bytes. Six adversarial
contract tests passed, including undeclared mutation, source drift, typed
metadata, output boundaries, and original sprite-table preservation checks.

The private output is
`private/test_runs/pc07_schala_presentation_diagnostic_v1/diagnostic.sfc`, SHA256
`96f2121be7c94d2acdf80bc3e22a3c06493e00345575802354725b71f43a2106`.
Its build receipt SHA256 is
`8cd1c9f67285bcc65896fbe5ae4f471755ed58946f36ee768fc8529a4d85373a`.
The metadata-only source recipe is
`references/pc07_schala_presentation_private_contract_v1.json`.
Static construction does not yet establish the native visual result.

The later consumer review found that the non-flipped field tile decoder at
`$C0:E687` dispatches only banks `$7F/$D2/$D3/$D4`; bank `$42` falls through to
hardcoded `$D5` reads at `$C0:E6BD`. The flipped path uses the full indirect
pointer and can read `$42`. Therefore publishing correct 24-bit pointers is
insufficient, and merely seeing some `$42` reads would not prove correct tiles.
This is a concrete defect in v1, not an emulator result. The original source
annotation calling pointer publication bank-agnostic must not be extended to
the downstream decoder. No v1 native launch was made.

## Additive v2 field tile repair

The separately authored `$413000..$4130E1` helper uses a four-byte JML hook
at `$C0:E699` plus its exact boot mirror. It replays the displaced load/compare
and retains the original dispatch for other sources. Only the PC07 object with
the published `$420000` graphics source and a complete aligned retail tile
offset takes the new copy path. Sixteen word reads copy that tile into the
existing field cache, then `$C0:E72D` performs the original pointer update and
near return. Native destination bounds and register/stack behavior remain part
of the pending observer; this is not general relocation or interrupt proof.

The v2 recipe preserves every v1 graphics, assembly, animation and name payload.
Its 26 named sections produce 9,126 changed bytes relative to the inert
scaffold. Six fail-closed contract tests pass, both shared guard APIs pass, and
fresh assembly reproduces all three original helper components before emission.
The corrected private image is
`private/test_runs/pc07_schala_presentation_diagnostic_v2/diagnostic.sfc`, SHA256
`111d903b760d90b4fc8232fd0786baf0924f63d7f7d201facd6858a4c8065429`;
its build receipt SHA256 is
`38c4a0662a7dc42a6cb2878f0b658bb4bea0954dd1225caf6ed955dc17efdd4c`.
The exact source bundle is
`a2d5d1f5ca296f025946152e03a1732b7e05b996637e71cd46a8fc549b6bee04`.
No native result is implied by these construction checks.

## Observed field and battle result

The headless Mesen run at
`private/test_runs/pc07_schala_presentation_v2_run1` reached its declared
battle-ready cut with exit63 and 270,641 trace rows. Root inspected
`poll_400.png` and `presentation_ready.png`: Schala is the additional field
actor and the rightmost battle actor, and the battle HUD visibly reads
**Schala** alongside Crono and Marle. The latter screenshot SHA256 is
`0d5b4418402f9ce5fe570c1847f4bf402c4b89f12aeb85fd6828d1472ecf1d5a`.
This is actual emulator output, not a generated mockup.

The observed trace SHA256 is
`beae63bd64af6dc6073cdf13880c74adadb382e18ce7fd1953381a976cd0b31e`.
Its exact collector/source bundle is
`126f8b2a39cfb21e8b81496b24a0fa033460593ddaf6f83c328ddf358c4105d5`.
The same prepared independent-PC07 fixture and continuous controller route are
retained. Its 4,642 explicit debugger preparation write/readback pairs are
separate from native execution; no CPU edit or fabricated action result is used.

Ninety-six sampled presentation windows pass their fixed CPU/stack/publication
replay. Four candidate non-flipped tile copies, two in each field scene, each
show all 32 original-source bytes, 32 native cache writes, stack readbacks and
the canonical return. Four original-character fallback samples also pass.
Actual graphics, assembly, primary-animation and timing reads occur in field
and battle; the candidate's body palette equals the retail source. Original
Crono/Marle palette checks pass. All 18 snapshots preserve the original seven
character records, the 48 stored name bytes including Epoch, and input SRAM.
These are selected runtime checks, not all-character rendering or vehicle-use
proof. No new source mapping is claimed merely because an old annotation was
checked again.

The first full validator incorrectly required the final shared drawing buffer
to retain the six name cells. Native execution had already reached the correct
cut, but the validator rejected that final-buffer requirement. The original
receipt and failed predicate remain preserved. Windows77 and94 actually write
and immediately read back the sixth glyph and attributes; the later window's
entry and final snapshot show that those temporary cells are reused. The final
buffer contains command-menu text, while the screenshot still displays Schala.

The additive temporal validator retains all other checks and proves the native
five-byte `Schal` source plus the sixth-cell writes/readbacks at their proper
times. The full name's visible result is separately inspected in the screenshot.
The first five HUD-tile writes and VRAM upload are not captured, so neither a
six-contiguous-byte HUD ledger nor a VRAM-transfer ledger is claimed. The
separate independent review rehashes 112 source rows and 74 recorded artifacts;
its receipt SHA256 is
`adf5e69982f542dc7bdbca4fd65ea71c5ff309b68a1333b61ea56dbd3cdef8ca`.

This run stops before an ordinary player Attack. It does not replace the earlier
accepted Crono-appearance Attack proof, establish all four rendered facings or
all fallback poses, or make PC07 recruitable/saveable throughout the campaign.
The name is currently a fixed battle-HUD name, not a menu/dialogue/save-name
implementation. The guarded image and all extracted data remain private.

The reproducible temporal requalification receipt SHA256 is
`650b9c9682e6d94ead85d12c86acfe6a9ec0d1a7766d6cd95d120a501e25e9aa`.
Root independently reran both the full corrected validator and its receipt
reproducer against the unchanged trace; both passed. The original failed receipt
remains SHA256
`bb204e3a94ae275f17f9bfe9d01a1227985fb0790c2fdc5e5d50f0f0121f293b`.
The metadata-only observation index is
[`references/pc07_schala_presentation_observation_2026_10_13.json`](../references/pc07_schala_presentation_observation_2026_10_13.json).

Read-only reproduction:

```powershell
python -B private/research/pc07_schala_presentation_temporal_review_20261013/reproduce_receipt.py
python -B private/research/pc07_schala_presentation_review_20261013/review_v1.py --check
```

The shared guard gained separate v1 and v2 private-presentation forwarders. The
exact earlier guards were archived, and a separately numbered source-resolution receipt
rechecks all 98 accepted Attack source entries without changing the frozen
bundle or receipts. Future revalidation must use that explicit resolver rather
than silently accepting the changed live guard.

Normal saving/cold-loading, recruitment, menus, overworld presentation, Techs,
complete battle return, and actual Epoch vehicle operations remain part of the
unfinished playable-eighth-character goal. No publication is implied.
