# Project Epoch: Schala playable-character design v0

Status: content proposal only  
Implementation status: not authorized by the current milestone  
Target identity: logical playable PC `$07`  

This document defines a bounded creative target for a playable Schala. It does
not claim that the ROM can yet store, load, render, save, or combine an eighth
PC. All names, mechanics, art direction, event beats, and balance values below
are proposals unless explicitly labeled otherwise.

## 1. Verified ROM and project facts

The following are implementation constraints, not character-design choices.

- **[verified-static]** Vanilla logical playable PC IDs are `$00-$06`.
- **[verified-static]** Logical PC `$07` is not a complete playable character
  in the vanilla ROM.
- **[verified-static]** Save slot-relative `$0430` is not an eighth PC record.
  Its opening bytes contain the seven vanilla PCs' tech progress and learned
  masks, so the entire region must be preserved.
- **[verified-static]** Save slot-relative `$0480` lies inside the vanilla
  serializer's first `$05B0`-byte region, and the checksum covers the whole
  `$A00` slot. It is not an approved Project Epoch backing record.
- **[hypothesis]** Schala state will use a versioned sidecar in deliberately
  expanded SRAM after mapper/header compatibility is proved.
- **[verified-static]** Low graphics-source indices above `$06` are already
  associated with engine actors or vehicles; they are not free character
  slots.
- **[verified-static]** File byte `$0D400E` is shared by logical PC `$07`
  normal-attack indexing and Crono critical-attack indexing. It cannot be used
  as a free eighth-PC entry.
- **[verified-static]** The current supported-slot Lucca-to-Magus clone is a
  diagnostic of known character-data surfaces, not an eighth-character
  implementation.
- **[verified-static]** Character ID `$07` already maps to bit 0 of the joined
  and item-equip flag table, but vanilla general-item mask `$FE` excludes it.
- **[hypothesis]** The remaining engine changes for an eighth portrait,
  runtime record, tech-learning state, combination-tech eligibility,
  save-select display, and party exchange remain to be implemented and
  runtime-tested.

## 2. Character thesis

### Proposal: "The Astral Regent"

Schala is a defensive arcane controller who turns dangerous situations into
stable ones. She contributes barriers, cleansing, selective control, and
moderate Shadow damage. She should feel powerful because she makes the party
reliable, not because she replaces Lucca's damage, Marle's healing, or Magus's
elemental breadth.

Her playable arc moves her from ceremonial obligation toward deliberate
leadership. The royal identity remains recognizable at a thematic level, but
her playable appearance, animation language, equipment, and combat posture are
newly designed for travel and battle.

Core play pattern:

1. Open with a ward or control effect.
2. Use positional Shadow attacks while the party is protected.
3. Spend substantial MP on a recovery tool when a fight turns bad.
4. Rely on allies for top-tier physical damage and sustained full-party healing.

Deliberate weaknesses:

- Lowest physical damage in the roster.
- Below-average HP and defense.
- Average speed; no permanent speed advantage.
- No cheap full-party heal.
- No broad elemental coverage.
- Her strongest protection and damage options are MP-expensive.

## 3. Original playable visual direction

### Proposal

The playable design must be drawn from scratch. It must not recolor Schala's
NPC tiles, reuse another PC's body, or splice Magus's cloak and animations.

**Silhouette**

- A short, asymmetric travel mantle ends above the knees, avoiding the NPC
  gown silhouette and preserving leg readability in field animation.
- A split over-tunic creates two narrow trailing shapes rather than one cape.
- One shoulder carries a crescent-shaped clasp; the opposite side remains
  visually light.
- A small floating focus appears only during casting. There is no permanent
  staff competing with Frog's or Magus's silhouette.
- Cool-toned hair is gathered into a high knot with one side braid. This keeps
  a high-level link to the royal NPC identity without copying its hair tiles.

**Palette**

- Primary: midnight teal.
- Secondary: warm ivory.
- Metal: muted old gold.
- Magic accent: rose-violet.
- Hair: deep indigo, separated in value from both mantle and background.

The palette intentionally avoids making royal purple the dominant garment
color. At SNES scale, each major material should use a dark, middle, and light
value group before hue variation is added.

**Pose and motion**

- Neutral stance: feet planted, forward shoulder lowered, one open hand ready
  to draw a sigil.
- Run: mantle tails separate on alternating frames; the focus is absent.
- Cast: two-step hand geometry, followed by a brief orbiting focus and a
  collapsing ring.
- Basic attack: a short-range geometric pulse, visually small and quick so it
  does not imply Lucca-level weapon power.
- Victory: the focus closes into the crescent clasp; Schala looks toward the
  party rather than bowing.
- Hurt/critical: posture becomes compact, emphasizing physical fragility.

**Portrait**

- Three-quarter view with an alert, resolved expression.
- Travel mantle and crescent clasp visible at the lower edge.
- Newly illustrated facial proportions and lighting; do not trace the NPC
  portrait or official promotional art.

**Readability acceptance criteria**

- Recognizable in silhouette beside all seven vanilla PCs at 1× scale.
- Hair, face, mantle, and legs remain separable on dark and snow backgrounds.
- Field, menu, and battle art use the same palette hierarchy.
- No frame contains copied PC or NPC tile clusters.

## 4. Combat kit: eight single techs

### Proposal

MP costs and power relationships are tuning targets, not encoded values.
Mechanics such as Barrier, Slow, status cleansing, revival, and target shapes
must be mapped to traced engine primitives before implementation. If a listed
compound effect cannot be represented safely, preserve the tech's role and
simplify the secondary effect.

| # | Tech | MP target | Target | Proposed effect and purpose |
|---|---|---:|---|---|
| 1 | Astral Pin | 2 | One enemy | Low Shadow magic damage. Cheap, fast baseline spell; roughly one tier below Lucca's efficient single-target magic. |
| 2 | Veil | 4 | One ally | Grants a short magic-damage barrier. No healing. Establishes Schala's protective identity early. |
| 3 | Crescent Wake | 6 | Line | Moderate Shadow damage along a narrow line. Rewards positioning; weaker per target than Lucca's comparable area damage. |
| 4 | Stillpoint | 7 | One enemy | Attempts Slow and deals very low Shadow damage. Boss immunity follows vanilla rules; damage prevents it from becoming a dead command. |
| 5 | Recall | 10 | One fallen ally | Revives with low HP and clears no additional status. It is an emergency reset, intentionally weaker than Marle's late revival specialty. |
| 6 | Sanctuary | 12 | All allies | Clears removable negative statuses and applies a brief magic barrier. No HP recovery. High cost prevents routine pre-casting. |
| 7 | Rift Bloom | 14 | Enemy circle | High Shadow damage centered on one enemy. Schala's best efficient damage tool, but below Flare and Dark Matter at equal Magic. |
| 8 | Astral Gate | 20 | All enemies | Very high Shadow damage plus a one-turn self Magic-defense penalty, if that penalty can be implemented safely. Without the penalty, reduce its power and retain the high MP cost. |

The complete seventeen-command launch set is now pinned as original
machine-readable authoring data at
`assets/source/schala/v0/content/schala_tech_content_v0.json`, canonical
normalized SHA-256
`90f43fb7602682911829a1077fb91b824a61e9071931eec1e0832c8a96590c2b`.
It includes the eight singles, six duals, two triples, and Focus Pulse. Native
effect, target, and animation bindings remain null until their engine paths
are approved.

### Learning cadence

Schala is recruited late enough that starting with only a two-MP spell would
feel unusable, but giving her the entire kit would erase progression.

- On recruitment: Astral Pin, Veil, and Crescent Wake learned.
- Early post-recruit: Stillpoint and Recall.
- Mid post-recruit: Sanctuary.
- Late post-recruit: Rift Bloom.
- Capstone sidequest or substantial TP investment: Astral Gate.

The authored cumulative thresholds are now 100, 250, 500, 900, and 1400 TP
after the three recruitment techs. Their engine-step form is 100, 150, 250,
400, and 500. Encoding remains deferred until the eighth-PC tech-progress
reader and save representation are adapted. The intended time from recruitment
to capstone is approximately the time a normally leveled party needs to learn
two late single techs, not an entire vanilla character's full progression.

### Progression data

The original machine-readable progression source is
`assets/source/schala/v0/content/schala_progression_v0.json`, canonical
normalized SHA-256
`17e25577bfb80998e33c5ac0890147231a5e1d3674de8af97e6fdf242f51aab5`.
It freezes the median-party recruitment-level policy, level-one stats, HP/MP
and seven-stat growth, high-bit-first starting learned mask `$E0`, TP cadence,
and the Glass Focus/Regent Mantle starting loadout. Its deterministic `$48`
Project Epoch overlay is not a vanilla character record or a runtime binding.
See `docs/schala_progression_foundation_v0.md`.

## 5. Combination-tech integration

### Proposal: bounded launch set

The initial content target is six dual techs and two triple techs. A
Schala–Magus dual is deliberately deferred: vanilla Magus's lack of combination
techs makes that path a separate engine and UI investigation.

Each combination below should be implemented only after tracing its eligibility
check, command-list construction, animation participants, MP consumption, and
learned-state persistence.

#### Dual techs

| Partners | Tech | Concept and balance target |
|---|---|---|
| Crono + Schala | Horizon Arc | Lightning strike collapses Schala's ring into a circle of mixed Lightning/Shadow damage. Strong group damage, below Luminaire's peak per target. |
| Marle + Schala | Quiet Heaven | Modest party heal plus status cleanse. Less raw healing than the best dedicated recovery combinations; its value is reliability. |
| Lucca + Schala | Eventide | Fire is compressed into a target circle, dealing heavy magic damage. High combined MP cost; below the strongest triple-tech burst. |
| Frog + Schala | Oathguard | Party magic barrier plus a modest heal. No physical-defense buff, preserving Frog's hybrid role. |
| Robo + Schala | Phase Engine | Moderate all-enemy Shadow damage and a brief party speed increase, if a safe temporary speed primitive exists. Otherwise use damage plus status cleanse. |
| Ayla + Schala | Star Pounce | Ayla delivers a physical leap through a spatial ring onto one enemy. High single-target damage, with no status or area utility. |

#### Triple techs

| Partners | Tech | Concept and balance target |
|---|---|---|
| Crono + Marle + Schala | New Dawn | Strong party heal, revive of at most one fallen ally, and moderate all-enemy magic damage. Extremely high total MP cost; weaker offensively than the premier damage triples. |
| Lucca + Robo + Schala | Little Star | A contained artificial star deals very high circle damage. No healing, control, or guaranteed status; intended as the kit's pure magic burst. |

#### Deferred relationship payoff

**Magus + Schala: Black Crown** is a narrative and mechanical stretch goal, not
part of the launch set. Its proposed role is concentrated single-target Shadow
damage that becomes stronger when an ally is at critical HP. It should proceed
only if tracing proves a clean way to give Magus a combination-tech command and
to represent its learned state without special-case corruption.

## 6. Equipment and item identity

### Proposal

Schala uses **Foci**, small magical instruments that alter the shape of her
basic pulse. They are a unique weapon family in content terms. The underlying
weapon-table expansion, damage formula, animation selector, inventory bit, and
equip permission are all unverified.

#### Weapon progression

| Weapon | Acquisition | Tuning identity |
|---|---|---|
| Glass Focus | Recruitment equipment | Low attack, Magic +1. Establishes that the weapon is secondary to spell power. |
| Tide Lens | Ocean-era side chest | Modest attack, improved magic critical/effect chance only if a traced primitive supports it; otherwise Magic +2. |
| Night Prism | Late sealed chest | Moderate attack, Magic +3. No status proc. |
| Star of Zeal | Capstone reward | Highest Focus attack, Magic +4, and 25% MP reduction only if it does not stack abusively; otherwise Magic +5 with no MP reduction. |

Basic-attack output should remain below Marle's at equivalent level and gear.
The top Focus must not approach Wondershot, Crisis Arm, or Masamune peak damage.

#### Restricted armor and accessories

- **Regent Mantle**: Schala-only armor; high Magic Defense, ordinary Defense,
  and status protection only if its total budget remains below Prism Dress.
- **Crescent Clasp**: Schala-only accessory; Magic +4 and Magic Defense +4. No
  Speed bonus.
- **Pendant Shard**: key item used during recruitment; never equippable and
  never consumes the vanilla Pendant's story role.

The seven-item authoring pack is pinned at
`assets/source/schala/v0/content/schala_item_content_v0.json`, canonical
normalized SHA-256
`dfa3f66d079a8921ff088b99f2ba507cf205525ab47fb11da609704e90c2fd85`.
Candidate byte IDs `$E8-$EE` are `verified-static` as unclaimed by canonical
location events after the complete pointer/script audit, but they are not
globally free or installable until the remaining item adapters and runtime
tests pass.
See `docs/schala_item_namespace_architecture.md`.

#### General equipment permissions

- May equip general robes, helms, and defensive accessories appropriate to
  magic users.
- Cannot equip swords, guns, bows, fists, scythes, arms, or Masamune-family
  weapons.
- Cannot equip PrismSpecs if Star of Zeal retains any MP reduction.
- No exclusive item may grant Haste, automatic revival, and status immunity in
  the same loadout.

Equip-mask width and an eighth permission bit are **[hypothesis]** until traced.
If a safe eighth bit does not exist, the content design must not be implemented
by borrowing another PC's equip identity.

## 7. Recruitment arc

### Proposal: "The Silent Palace"

Recruitment is an optional late-game quest unlocked after the Ocean Palace
collapse and after Crono returns. This placement avoids displacing the
Crono-recovery arc and gives Schala agency in the final act without rewriting
her earlier NPC scenes.

1. **Resonance at the End of Time.** The repaired Pendant emits a second,
   unstable note. Gaspar identifies a sealed temporal pocket formed during the
   Ocean Palace collapse.
2. **Open the pocket.** The party visits three existing eras to stabilize an
   anchor: a sunlit ruin, a future power conduit, and a living natural site.
   Each stop is one encounter or environmental puzzle, not a new dungeon.
3. **Enter the Silent Palace.** A compact original map shows a fragment of Zeal
   held outside ordinary time by Schala's failing ward.
4. **Resolve the ward.** The party defeats a magic-draining guardian while
   protecting three anchor points. Schala appears as a guest caster for one
   scripted Veil, demonstrating her role without becoming controllable yet.
5. **Choice and recruitment.** Schala releases the pocket's trapped survivors
   to the timeline and chooses to join the party against the Black Omen. The
   choice belongs to her; she is not collected as a rescue reward.
6. **Capstone.** Returning after confronting the Queen's legacy unlocks a short
   scene, Star of Zeal, and Astral Gate.

Narrative guardrails:

- Do not claim the quest erases or replaces Schala's established fate; the
  temporal mechanism must be presented as Project Epoch's explicit branch.
- Do not make Magus's approval the condition for her recruitment.
- Include optional Magus dialogue, but the quest remains complete without him
  in the active party.
- Do not reuse the Ocean Palace NPC sprite as the controllable sprite.
- Keep mandatory new locations to one compact map and reuse existing eras for
  the three anchors.

Event flags, guest-party behavior, an eighth roster bit, and alternate dialogue
branches are all **[hypothesis]** pending trace evidence.

## 8. Balance constraints against the vanilla roster

### Proposal

These constraints are acceptance tests for later tuning.

- **Crono:** Schala must not exceed Crono's general-purpose speed, physical
  damage, or efficient all-target capstone damage.
- **Marle:** Recall revives with less HP than Marle's premier revival. Schala
  cannot combine strong party healing and Haste in a single cheap action.
- **Lucca:** Rift Bloom and Astral Gate remain below Lucca's best fire damage at
  equal Magic and comparable MP unless Schala is paying a clear defensive cost.
- **Robo:** Schala offers no efficient all-party HP sustain and has materially
  worse durability.
- **Frog:** Schala cannot match Frog's physical output or low-cost hybrid
  healing; Oathguard requires both characters.
- **Ayla:** Schala has no steal/charm replacement and never approaches Ayla's
  physical critical ceiling.
- **Magus:** Schala is limited to Shadow damage and support. She does not gain
  Magus's four-element coverage or equal Dark Matter's uncomplicated burst.

Quantitative targets at equal level and ordinary late-game gear:

- HP: lowest or tied-lowest in the roster.
- Speed: roster median, with no more than one point of natural variance from
  Lucca's comparable progression.
- Magic: high, but below Magus at recruitment before equipment.
- Stamina: lowest tier.
- Basic attack: at most 60% of Marle's expected ordinary attack damage.
- Efficient area spell: 75-85% of Lucca's comparable area damage.
- Capstone: 85-90% of Dark Matter's expected damage before Astral Gate's
  proposed self-penalty.
- Sanctuary: costed so repeated use cannot maintain permanent party protection
  without external MP recovery.

No balance target is **verified-runtime** until tested against recorded vanilla
comparisons using identical level, stats, enemy defense, equipment assumptions,
and RNG controls.

## 9. Scope boundary and implementation gates

This design does not authorize production PC `$07` changes. Before any content
is encoded, tracing must identify:

1. PC-ID input and table bounds for field, battle, portrait, menu, and
   save-select graphics.
2. Runtime character-record allocation and every initialization path.
3. Save/load storage for stats, equipment, learned techs, TP progress, roster,
   and active-party membership.
4. Inventory and equipment permission representation for an eighth PC.
5. Single-tech command construction, descriptions, targeting, animation, and
   effect dispatch.
6. Dual/triple eligibility, learned state, MP consumption, and menu layout.
7. Event/recruitment flags and party-exchange behavior.
8. A provenance-backed location for any injected code or expanded data.

If a proposed content feature requires an untraced new mechanic, either defer
that feature or substitute a verified vanilla primitive while preserving its
combat role. No alias to Magus, borrowed graphics index, borrowed equip bit, or
save-region overwrite is an acceptable shortcut.

### Recruitment authoring source

The Silent Palace recruitment direction is pinned as an original executable
authoring graph in
`assets/source/schala/v0/content/schala_recruitment_content_v0.json`,
canonical normalized SHA-256
`fbffbc7bd9bed555ed7966ed62f6b9b247b4403986fef358711e9e00e13520eb`.
Its seven acceptance scenarios cover Magus present/absent, decline, open/full
party, already recruited, and retained/reset New Game+ behavior. All 29 engine
dependencies and every graph node remain explicitly unmapped with null
bindings. No dialogue or event bytes were copied from the game.

## 10. Content acceptance checklist

- [x] A partial clean-room gameplay foundation compiles deterministically:
      four cardinal field idles, a three-key downward walk, battle ready, cast
      gather, and cast release.
- [x] The current partial field/battle foundation passes exact and
      palette-renaming-invariant tile comparison against all seven canonical
      playable-character graphics windows.
- [x] The current partial gameplay and Glass Focus sources have zero exact or
      palette-renaming-invariant H/V/HV matches against the 78 nontrivial
      tiles in the one documented Schala-family NPC packet.
- [ ] The completed field and battle sprite sheets pass the corresponding
      full 241-packet compressed-corpus and near-match review.
- [x] Original 48×48 full portrait and 32×32 save preview pass visual and
      tile-copy review.
- [x] Original stats, HP/MP growth, stat growth, TP cadence, and starting
      loadout compile into the Project Epoch progression overlay.
- [ ] Progression overlay is bound to the live record, growth readers, TP
      reader, save path, and equal-level balance replays.
- [ ] All eight single techs have a traced target rule, effect primitive,
      animation route, MP value, and learned-state representation.
- [ ] Six launch duals and two launch triples have traced combination behavior.
- [ ] Equipment has a genuine eighth-PC permission model.
- [ ] Recruitment neither alters the original save nor depends on an unsafe
      record alias.
- [x] Original recruitment dialogue/branch authoring covers the required
      Magus, party-capacity, repeat, and New Game+ scenarios without runtime
      bindings.
- [ ] Recorded emulator tests cover save-select, menu, roster, party exchange,
      field, battle, tech learning, combination techs, saving, reloading, and
      New Game+.
- [ ] Balance comparisons satisfy Section 8 or document an intentional revision.
