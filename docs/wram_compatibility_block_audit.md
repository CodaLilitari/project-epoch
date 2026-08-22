# Project Epoch relocated compatibility-block audit

Status: preferred candidate, partially runtime-tested; not production-approved  
Last updated: 2026-07-28  
Target live record: Schala at `$7E2830-$7E287F`  
Candidate relocated vanilla block: `$7E2CA0-$7E2CEF`

## Result

The preferred runtime architecture is to preserve the engine's natural
`$7E2600 + id*$50` formula for Schala and move the complete vanilla
compatibility block currently occupying ID `$07`'s range:

```text
$7E2830-$7E287F  Schala live character record
$7E2CA0-$7E2CEF  relocated vanilla compatibility block
```

This is safer than an external Schala record because menu, battle load,
battle commit, reload, growth, and equipment code already derive a record
from the character ID. It still requires explicit initialization,
serialization, and compatibility-state consumer changes.

The `$2CA0` destination is a strong candidate, not declared free space.

## Static bounds

`verified-static`

- Vanilla's serialized cursor/state block at `$7E2C7C`, length `$1E`, ends
  at `$7E2C99`.
- A battle-exit cursor formula uses `$2C7C + id*4`; ID7 can touch
  `$2C98-$2C9B`. Starting at `$2CA0` leaves the four-byte structural front
  guard `$2C9C-$2C9F`.
- Battle/menu scratch begins at `$7E2D00`. Ending at `$2CEF` leaves a
  `$10`-byte rear guard.
- No named or direct reference in the pinned reconstruction targets
  `$7E2CA0-$7E2CEF`.
- Thirty-six existing bsnes2014 states sampled across title, save-select,
  loaded field, and diagnostic menu probes contain all zero bytes in the
  candidate range. This is supporting negative evidence, not ownership
  proof; computed pointers and block moves remain possible.

The complete `$50`-byte source block must move:

| Range | Known meaning |
| --- | --- |
| `$2830-$2836` | seven single-tech progress counters |
| `$2837-$285B` | 37 learned single/dual/triple group masks |
| `$285C-$2861` | unmapped compatibility/template bytes |
| `$2862-$287F` | bulk-initialized and serialized bytes; preserve until mapped |

## Runtime canary

`tools/inject_bsv_wram_canary.py` derives the pinned bsnes2014 WRAM block from
the live Lucca/Magus record pair when present, or from the separately checked
cold-state layout, and changes only `$7E2CA0-$7E2CEF`. It refuses to inject if
the source candidate is not all zero.

The deterministic `$50`-byte canary has SHA-256:

`4e3df1af239b20cefae9d9a2219f384a4934b1916da11b001b9e501b84e06290`

### Negative control: pre-boot injection

`verified-runtime`

A canary inserted into the cold/title initial state is cleared to all zero
during ordinary WRAM initialization. This is expected and proves that a
pre-boot canary cannot answer the live-allocation question. All four cold
experiments—idle boot and Continue into slots 1, 2, and 3—ended with the
same all-zero target SHA-256:

`5b6fb58e61fa475939767d68a446f97f1bff02c0e5935a3ea8bb51e6515783d8`

Production initialization must populate the relocated block after the
ordinary clear/seed path.

### Loaded-field injection

`verified-runtime` for field idle and menu-entry calibration

The corrected experiment starts from the already loaded field state, replaces
only `$7E2CA0-$7E2CEF`, and replays deterministic input:

- field-idle BSV SHA-256:
  `d307d1d200541dd17ab4039af73125cafe062f2cec085a646eddeca46d1d92b0`;
- field-idle exit-state SHA-256:
  `961f86d1d10628972285d9c962a090c4362c8cc729ded29e93a95f6c4b6bf185`;
- calibrated menu-entry BSV input-slot 4 SHA-256:
  `2eeed5f60773cd8f06af202ce9d00e99eba03246036f5f251c403cace4f68629`;
- menu-entry exit-state SHA-256:
  `5e50f58b3f69711afc4883636c7903043e51a5191102083d824fdfa35ada6667`.

The canary survives exactly once at pinned state offset `30531` in:

- the 900-frame field-idle run;
- all twelve short raw-input-slot calibration runs;
- the run in which raw input slot 4 enters the menu overlay
  (`$7E0016=$D4F0`, `$7E0A00=$06`).

The four-byte structural front guard and `$10`-byte rear guard remain zero in these exit
states. These runs prove basic live-field and menu-entry stability only.

### Live-menu transition matrix

`verified-runtime` for calibrated short transitions

The menu-entry exit state was then used as the initial state for twelve
otherwise identical 900-frame legacy BSV edits. The old editor treated each
pair of callback bytes as one little-endian value. Exact source inspection now
shows that slots 0-5 targeted player-1 IDs B, Select, Up, Left, A, and L,
while slots 6-11 targeted the same six even IDs on player 2. This was not a
complete twelve-button player-1 calibration. The canary survived exactly once
at state offset `30531` in every result.

- player-2 slots 6-11 were identical no-effect controls, exit-state SHA-256
  `ab188f73b7e0f1d9f1bb5660f69db9235647f448fa1f7ecf2900893e9afecebb`;
- slot 0 exited the overlay, exit-state SHA-256
  `43269807f31013e23f8356d1c1e83d384c27aa2c1b88e4c42e9e1d52a65bfe28`;
- slot 2 changed the menu cursor, exit-state SHA-256
  `4e841a893f7330b3758c70a3e77dd906f10606bf901ce96bf8ffcebad7131305`;
- slot 4 entered another menu task/page state, exit-state SHA-256
  `0027d3675b652bb2c26955762a32ea8a11f76b9b557d42a3331d993ac84c53b3`.

Slots 1, 3, and 5 also produced distinct live-menu states with an intact
canary. This establishes cursor, confirm/cancel, page-entry, and overlay-exit
stability for short deterministic paths; it does not yet cover every menu
page or character switch.

A second twelve-slot matrix started from the entered submenu/page state. The
canary again survived every run. Raw slot 2 changed the submenu cursor
(exit-state SHA-256
`18b6a3c89ce7ff3e2d8ec8ea41e8afd5f8e4383f2bb2a383d2d642115326b05c`);
raw slot 4 returned to the parent menu
(`b7aee22449dec6b1ddb56372a4ef03e846b5e6e365ddfacf97479863d92c23dc`);
slots 6-11 were identical controls
(`867dd650abfc44a6c1d81f1be3791ac81936727b618f8245601ac9984856fa3a`).
This adds submenu cursor/return coverage without claiming that the specific
page's record readers have all executed.

### Native main menu, party exchange, and battle checkpoints

`verified-runtime` for the stated paths

Three additional checkpoints were constructed with temporary, one-purpose
diagnostic ROM edits, then exported as zero-input BSV states and replayed for
600 frames against the unchanged static ROM
`4c4ea60434e22c19df0278aeb89ab03f566cdf7323c6fd0a31d2f6739d80666e`.
The diagnostic ROMs are local-only and are not patch architecture.

- **Full main menu.** The native main-menu checkpoint BSV SHA-256 is
  `c2ccf3523fca23f7a0294527b6dad50081c00156d2a70b072faa47b19838c79b`.
  Its entry state is
  `db157736e0f81b53e92715e1d3829886deb14e5facf2d336802faa7cb8ed3773`;
  the unchanged-ROM 600-frame exit state is
  `0cba3bfc1778fbecc184b5219bdab7f4c1100b4c811dad31d02c40da93b1e9f0`.
- **Party exchange.** A native swap changed roster bytes at `$7E2980` from
  `00 01 02 82 80 04 03 06 05` to
  `04 01 02 82 80 00 03 06 05`, exchanging Crono and Frog while preserving
  the compact roster. The reusable checkpoint BSV SHA-256 is
  `9ac8f2eec7629e1a53ba8a45bb1c79520c866c836472bebbdcb68369acf73de8`;
  its unchanged-ROM 600-frame exit state is
  `865219ffd626492a0649b7079cf72080d622b5b0823e125bb4923b2ea05d0617`.
- **Battle entry and idle.** The native battle-engine checkpoint BSV SHA-256
  is
  `f11688de39206cde3a7655e945fa035b7f0b150ba6ee1160fbeb905dfc6fc689`;
  its entry state is
  `dfe273af97abf9af0ba597dbea3ba4d668086457e5822ddcda8e2c861bc91ad7`;
  the unchanged-ROM 600-frame exit state remains in battle and hashes to
  `557867ef9fa7a6b59bc10a613384bab1695b0eebbeb454e83acd3b293e21759c`.
  The encounter was synthetically initiated with an already loaded field
  object, so this proves traversal and battle allocation, not encounter
  semantics.

In all three entry states, independent inspection finds the canary exactly
once at state offset `30531`; its SHA-256 is exact and the four-byte
structural front and sixteen-byte rear guards remain zero. The zero-input unchanged-ROM replays
retain those properties. This materially strengthens the candidate, but it
does not cover all main-menu pages, an eighth roster identity, battle
commands, death/victory, or field return.

### Equipment-screen entry and idle

`verified-runtime` for entry, rendering, and 600-frame idle; equipment change
and character switching unproved

The native main-menu checkpoint begins with cursor `$7E0411=$00`.
Static dispatch maps option 0 through `$C2:9C29`; `$C2:9C31` advances the menu
state and enters `Menu_EquipScreenInit`. The calibrated raw input slot 4 is
Confirm.

The accepted movie contains one two-poll raw-slot-4 pulse at poll frame 100:

- BSV SHA-256:
  `d4bd046ff61c06629dbc2fac5c64e6c386d4c4462fba8ac22b612e5a78c8cda6`;
- unchanged diagnostic ROM SHA-256:
  `4c4ea60434e22c19df0278aeb89ab03f566cdf7323c6fd0a31d2f6739d80666e`;
- 600-frame video SHA-256:
  `d36f97f2bdeff471a8e38cf5c72e2510545a6416ab944729c28f41f1aa204fc2`;
- equipment-screen frame SHA-256:
  `e3190735fb43100e4dec3f094067bcf999c772f49ea77e802556b64b5f8b1b2c`.

The recording visibly reaches the equipment page and renders Crono's
equipment and derived stats. A separate auto-state replay of the same movie
produced state SHA-256
`2fd8b7194b5e7a9220ff0b8a5d47e92f3a0666a12a0f96f963e8e31f8cd173af`.
The canary appears exactly once at state offset `30531`, matches SHA-256
`4e3df1af239b20cefae9d9a2219f384a4934b1916da11b001b9e501b84e06290`,
and retains its four-byte structural zero front guard and sixteen-byte zero
rear guard.
The log confirms content CRC-32 `9CA72581`, disabled SRAM saving, and a
successful auto-state save.

This proves menu initialization, equipment/stat rendering, and idle
preservation only. It does not prove item selection, equipping, recalculation
after a change, shop paths, or switching among characters.

### Raw battle-menu input calibration

`verified-runtime` for the legacy native menu-state calibration itself; attack
execution was unproved by this subsection and is superseded by the bounded
current-core cycle below

Twelve legacy two-byte editor positions were pulsed independently from the
native battle checkpoint. They covered the six even-numbered joypad IDs on
each controller port, not all twelve player-1 buttons. Player-1 slots 0-5
produced distinct states; player-2 slots 6-11 matched the idle baseline state
SHA-256
`557867ef9fa7a6b59bc10a613384bab1695b0eebbeb454e83acd3b293e21759c`.
Static/runtime correlation supports:

- raw slot 2 latched `$EF=$08`, matching the Up handler at `$C1:11B1`;
- raw slot 3 latched `$EF=$02`, matching previous-PC/Left at `$C1:11A8`;
- raw slot 4 latched `$EE=$80`, matching Confirm at `$C1:11D2`;
- raw slots 0, 1, and 5 latched `$EE=$0A`, `$04`, and `$20`, corresponding
  to player-1 B, Select, and L in the pinned core's proved query order.

Confirm changed the native menu state at `$7E06E2/$7E06E6/$7E06E7` from
`11 00 55` to `12 02 54`. It did not produce a proved ordinary attack,
action-queue entry, damage event, victory, or field return. Slots 6-11 are
player-2 inputs and therefore do not test the missing player-1 Y, Start, Down,
Right, X, or R paths.

All twelve output states retain the exact canary once, with zero front/rear
guards. The six distinct state SHA-256 values for slots 0-5 are:

```text
00  1d1d38fcee62232518a7ae248c7681f7f85b467a7899ddf5770259f1ae47946d
01  e3d5bb09cbaa283eb10e959e5d43b6b0a71af9ec74015840682193b5958fb4a9
02  7b9f1cc1a66ad9a3ec56e3dfd5b4b9a9335baaadd4869554af3a29ab35a09b03
03  6e7e4849b5b46cdf3766ad90cc969aff5ec027b4d669569d3cd9e2e9d544ae9e
04  8717d7673edbbecc7a3f6c2afc46b7fece48550b9dce37d924faaa4be434cca2
05  a823553ea7cdd9aaa39189837f4882c93aa731155f312e39d6d9634367549069
```

### Inert ExHiROM checkpoint replays

`verified-runtime` for continued execution from three established states

The full-menu, post-swap party-exchange, and native-battle checkpoint movies
were rebound to an inert 8 MiB expansion of the same static diagnostic base.
The rebind updates only replay/ROM identity metadata; it preserves the
serialized core payload and all controller inputs. Each rebound movie then
ran for 3,600 frames with SRAM loading and saving disabled.

At every checkpoint:

- the canary remains exact once at state offset `30531`;
- the four-byte structural front and sixteen-byte rear guards remain zero;
- the complete serialized payload, including all 128 KiB WRAM, is identical
  to a repeated 4 MiB control after excluding the ROM identity field;
- the state comparator reports zero unexplained differences.

The ExHiROM output state SHA-256 values are:

- full menu:
  `aa434a4a9b3cd0e6a8a80c26f75a0c3ba387fe64e49a7eda211ec6262f9c8efa`;
- party exchange:
  `2d1c3e3a96e468f43a8e9156e843d97738164b8fe5f9144cfb498161a7e61da7`;
- battle:
  `e7a7254c2ac0cf4b0df85a7342b61ebcc16cbaa1eaa76b23ddf200aa2d98523e`.

Because the movies begin inside those engine states, this does not replace
end-to-end input, normal encounter, save/load, or battle-exit gates.

### Inert ExHiROM Continue/full-load controls

`verified-runtime` for the inert mapping, negative control for this WRAM block

Recorded title-screen inputs loaded save slots 1, 2, and 3 on both the
supported-slot 4 MiB base and its inert 8 MiB expansion. Every ExHiROM result
matches its repeated 4 MiB control across the complete serialized payload and
all WRAM after excluding ROM identity.

In all six outputs, `$7E2CA0-$7E2CEF` is all zero and both guards are zero.
This agrees with the cold-initialization finding: a canary planted before boot
is cleared before the full load completes. Therefore these runs verify the
ExHiROM title/Continue/full-load path, but do not establish survival of live
relocated compatibility data or a future Schala sidecar.

### Soft-reset calibration and emulator transition

`verified-runtime` for the vanilla reset effect; rejected as an isolated
player-1 replay and not a Project Epoch initialization test

Exact RetroArch 1.7.1 and bsnes2014 source inspection corrected the legacy
movie model: the frontend records one byte per input callback, while one
normal bsnes2014 auto-joypad latch contains 12 player-1 bytes followed by 12
player-2 bytes. The corrected legacy editor now models all 24 callback slots.

An intermediate calibration movie, SHA-256
`b63d0e45aea8c552c41b9e438c48cc17c35d1ef3220ac7b4c745f7e9d0cb7e25`,
held Select+Start+L+R on both ports because it was generated during the
12-byte half-latch diagnosis. It did fire the vanilla soft reset:

- exit-state SHA-256:
  `dfea98d95ed034cb10b67744dc4e2667e6cb54dbf02a78f1ecf2b4b22c4d53b8`;
- `$7E2CA0-$7E2CEF` is all zero, with target SHA-256
  `5b6fb58e61fa475939767d68a446f97f1bff02c0e5935a3ea8bb51e6515783d8`;
- the complete `$2000`-byte SRAM image remains byte-identical to the embedded
  initial state, SHA-256
  `450c392bb29ac198cef7061e31512c69231c46eedf50d2e923d2e75e72018930`;
- the sidecar-gap canary remains exact once at state offset `8280`, SHA-256
  `219051da0bd17ea7e24c9d260ed4d84ee8215ebdb71545fb25bb49b859eb7348`.

This proves that the vanilla reset clears the candidate WRAM block without
clearing SRAM in that calibrated run. It does not prove a player-1-only input
path, relocated compatibility initialization, Schala initialization, or
Project Epoch post-reset behavior, so the approval-matrix reset gate remains
open. The legacy harness is now retained only as reproducible historical
evidence.

The active emulator baseline has moved to RetroArch 1.22.2 plus the current
bsnes core. Both the canonical clean ROM and the supported-slot diagnostic
complete a 120-frame headless smoke test on that baseline. Existing
bsnes2014 savestates are not treated as transferable evidence.

### Current-core field, menu, and Player-1 reset controls

`verified-runtime` for the listed vanilla paths; Project Epoch initialization
still unimplemented

The current BSV2 harness regenerated a slot-1 field checkpoint from the
canonical ROM and an isolated disposable copy of the recovered SRAM. Tagged
input records prove that only Player-1 Left at frames 1800-1801 and Player-1 A
at frames 1950-1959 were used for title entry and load. The resulting raw
current-core state independently anchors live WRAM at state offset `$2284`,
placing `$7E2CA0-$7E2CEF` at state offset `$4F24`.

An exact canary then passed:

- 600-frame loaded-field idle;
- native main-menu entry from Player-1 X and 600-frame menu idle;
- Equipment entry from tagged Confirm;
- a tagged Down transition from Crono to Marle on the Equipment page.

In both exit states the canary appears exactly once and the four-byte
structural front guard plus sixteen-byte rear observation guard remain zero.

An isolated Player-1 Select+Start+L+R chord at frame 60 visibly returned to
the pendulum intro. Its exit state has an all-zero candidate block and zero
guards. This confirms the legacy calibration's vanilla clear effect using
tagged current-core Player-1 events. It does not satisfy the Project Epoch
gate: the future reset handler must initialize the relocated compatibility
record and Schala state before subsequent consumers run.

All hashes, tool behavior, disposable-SRAM rules, and reproduction commands
are in `docs/current_emulator_replay_harness_2026-07-26.md`.

The same raw checkpoint was rebound to the canonical inert 8 MiB ExHiROM by
changing only the BSV2 content CRC. Matched current-core outputs for field
idle, native menu, Equipment with Marle selected, and the full 3,599-frame
field replay have byte-identical raw core states and pixel-identical
screenshots between 4 MiB and 8 MiB. The canary and guards remain exact.

### Current-core party exchange, recruitment, and narrative battle

`verified-runtime` for the bounded vanilla paths below; no PC `$07` installed

The clean-ROM current harness now supplies three stronger transition families:

- a normal Y-button party exchange changes the seven-PC roster from
  `00 01 02 82 80 04 03 06 05` to
  `04 01 02 82 80 00 03 06 05`, exchanging Crono and Frog;
- the full-party North Cape recruit branch changes
  `04 01 03 83 81 84 02 05 80` to
  `04 01 03 06 81 84 02 05 80` before Magus name acceptance, then native
  party exchange produces `06 01 03 04 81 84 02 05 80`;
- the alternate North Cape choice enters the real Frog-versus-Magus
  location-event battle and remains in that battle through a 600-frame
  zero-input replay while enemy AI advances;
- independent four-frame pulses cover all twelve Player-1 joypad IDs at the
  native Frog-versus-Magus command menu: Y moves the command window, Start
  pauses, Up/Down select Item/Tech, and A begins the normal-attack flow; B,
  Select, Left, Right, X, L, and R match the zero-input endpoint only in this
  bounded top-level context;
- Down followed by A opens Frog's native Tech submenu with Heal, Leap Slash,
  and Water 2 visible; no tech is selected or cast;
- two further A presses separated by four released frames select Heal and
  confirm Frog; against a matched Tech-open control, Frog reaches `999/999`
  from `837/999`, MP changes `99->97`, Magus remains `6666/6666`, and the
  command menu becomes stable again;
- a matched 1,200-frame A-only probe leaves Magus at `6666/6666`, proving the
  first A stops at target choice rather than resolving the attack;
- after four released frames, a second A completes the native normal-attack
  cycle: the matched 1,500-frame control remains `6666/6666`, the attack route
  reaches `6137/6666` (529 damage), and the command menu is stable again;
- an isolated native slot-1 save increments Save #62 to #63, preserves
  `$0430-$047F`, and fresh-process reload restores that exact region to live
  `$7E2830-$287F`; the proposed relocation block is all zero after reload,
  proving vanilla does not serialize it;
- the recovered final save walks normally from Lavos Tunnel `$01DA` into
  Lavos Core `$01DB`, advances bounded party dialogue, and reaches the native
  Lavos battle menu.

Magus registration changes the vanilla joined mask from `$FC` to `$FE`.
Across the decision, registration, name-entry, party-swap, North Cape battle,
Lavos location transition, dialogue, and final-battle entry checkpoints, the
candidate canary appears exactly once, both guards are zero, and live Epoch
name bytes at `$7E2C4D-$7E2C52` remain
`a4 c9 c8 bc c1 00`. The selected source SRAM and all disposable copies retain
SHA-256
`a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9`.

A prior survey of the North Cape outputs found 49 current-core RASTATEs: 39
post-injection states contained the exact canary and 10 pre-injection controls
retained an all-zero target. The twelve independent Player-1 calibration
states add twelve exact-canary results, again with zero guards and unchanged
Epoch/SRAM bytes. The accepted route and exact hashes are in
`docs/vanilla_magus_recruitment_runtime_trace_2026-07-26.md`.

This closes current-core seven-PC reserve registration, native party exchange,
normal story-battle entry, battle idle, top-level command navigation, pause,
window movement, one complete normal-attack target/damage cycle, Tech-submenu
entry, one native Heal selection/self-target/effect cycle, and the native
slot-1 save/full-load boundary. It does not prove PC `$07`, an eight-character
roster, actual relocated compatibility data, other Tech target/effect classes,
Item/target flows, victory/death/exit, Project Epoch sidecar persistence, the
other save slots, or New Game+.

### Current-core menu, equipment-mutation, and Item tranche

`verified-runtime` for the bounded vanilla paths below; no PC `$07` installed

Six independent replays open the native main menu and advance its cursor to
Item, Tech, Config, Party, Save, and Equip. The resulting core-state SHA-256
values are:

```text
Item    f7598b7ad9ee771c26d1abf84b303e9962957ef7206d217cb6d1ef39dfda0dca
Tech    9359a5a733f01674654f6d5157ef3c97555e2e3d0a0e636193ff824550380026
Config  ce43d7d75d513992833e27fc426be350b4c308372ccea5047df0bc924be912ec
Party   124af09e3cc5b8c7f0673e40ae8e16013616417a1730bfd883da770ae9a9fed1
Save    514860bb40fb560974cc3d60a9e086598abd9264c8760e382a00121bca1c6613
Equip   1c2891f36b775081682c2d7d2c92c8e5cc55ab03d2d7a8d000338dacc03cde48
```

A seventh replay enters Tech and switches the visible owner from Crono to
Marle. Its core-state SHA-256 is
`afacd3778eee18a0553e71cb47151a15601c6115740d7d4dbfec85954f154e2c`.
This proves one native character-switch path and rendering of Marle's
single-tech list; it does not prove PC `$07` owner resolution.

The Equipment route opens Crono's weapon list and selects the highlighted
Kali Blade. The before/after core-state SHA-256 values are
`f47754cbd7614434c10f0bb243ac0fbef9fe5ab23acc7606d34af0dbe1ff478d`
and
`160f542cb946ee35cd357a67cbdc153f62b037d7089599df3faadd79a2d7d5c0`.
Within Crono's `$50`-byte field record, the four equipment bytes change only
from `8f 6b 55 9f` to `8f 6b 0d 9f`; current Attack changes from `$EC` to
`$C6`. The screen renders the Kali Blade as equipped and returns the Rainbow
to inventory. The disposable SRAM remains byte-exact, so this is a live
equipment/recalculation path rather than a save-write proof.

The North Cape battle route wraps from Attack to Item, opens the native item
list, selects MegaElixir, confirms Frog, consumes one unit, and returns to a
stable command menu. A matched no-use control retains battle-inventory row 8
as `c5 81 02 21 00`; the use route changes only its quantity byte, producing
`c5 81 02 20 00`. Their core-state SHA-256 values are respectively
`52abd534b64e65334599d061ebe99f7a6c59303a675b660154b9ec2d0902130f`
and
`86653ad80befd6ac44a77f45392df4ac7f9862da0b39fce20d3f03a1d702ffac`.
All other populated battle-inventory rows match.

Every one of the thirteen output states contains the exact relocation canary
once, with a zero four-byte front guard and zero sixteen-byte rear guard. The
field-menu/equipment SRAMs retain SHA-256
`cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203`;
the North Cape battle SRAMs retain
`a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9`.
The 51 accepted movies, logs, states, and screenshots are selected by
`references/current_compatibility_canary_tranche_accepted_artifacts_v1.json`;
the local-only curated manifest is reproduced as documented in
`docs/current_emulator_replay_harness_2026-07-26.md`.

This closes the remaining top-level main-menu pages, one Tech owner switch,
one equipment mutation with derived-stat recomputation, and one complete
Item/list/target/consumption cycle for the compatibility-block canary. It
does not close shop menus, offensive or multi-target Tech classes,
death/victory/battle exit, actual relocated data, or any PC `$07` adapter.

### Natural encounter, victory, and field return

`verified-runtime` for one bounded vanilla battle lifecycle; no PC `$07`
installed and no balance claim

A high-level Crono-only test fixture walks normally from the 1000 A.D.
overworld into location `$0013`, Guardia Forest (Present), then reaches the
three-Roly encounter by field movement. The encounter boundary is
deterministic: Right beginning at replay frame 60 for 139 frames leaves
`$7E011F=1` and `$7E0117=0` (field/explore); the otherwise identical
140-frame input changes them to `0/1` and enters the battle. The two boundary
movies hash to:

```text
139 frames  b523a6a4a20e82fbd3ea7c5d07e4e4e2254bd0562aed950e93e30d09ecf18d83
140 frames  e1052485dfe1d5d13481f970d8480b4ea2451e7ee2ead75529371c20e93c1f6c
```

At the command-ready endpoint, the generalized `$80`-stride combatant
inspector reports Crono in slot 0 at `996/999` and enemy slots 3, 4, and 5
with identity `$5E`, each at `14/14`. This independently confirms the visible
three-Roly encounter.

The accepted command-ready battle checkpoint BSV SHA-256 is
`6681a81b7a44942ac838b167e7222e47929402004d06eb9e390071602f7f0a79`.
From it, three pairs of released A pulses select Attack and confirm one target
at frames `60/68`, `620/628`, and `1180/1188`. The victory movie SHA-256 is
`33d2ba256d929667081d3a3197762d283a1f00160e43e713bf02bf61dfd3626a`.
At frame 1,800 the rendered reward line is `Found 480G`; by frame 2,600 the
same replay has returned to free field movement in location `$0013`.

The final RASTATE container hashes to
`efcfd98405f247d158dbbd248e287a4e1a570f62d9d4d52dd2cf7132886b9918`;
its extracted core hashes to
`3f63df9b8d30a0b3d09cc95761a683e9627c869ae74aa8d14e3638c6025a3f5c`.
All eight accepted route/boundary/reward/return states pass the exact-canary
and guard checks, preserve slot `$0430-$047F` against live
`$7E2830-$287F`, and retain the single disposable SRAM SHA-256
`a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9`.
The 37 accepted checkpoints, movies, logs, states, and screenshots are
selected by
`references/current_guardia_victory_canary_accepted_artifacts_v1.json`;
failed and exploratory navigation probes remain excluded.

This closes one natural battle's entry, three native attack/target cycles,
victory reward, battle teardown, and return to field for the relocation
candidate. It does not cover character death, status effects, criticals,
multi-PC victory poses, an eighth identity, or the future translated battle
commit for actual relocated compatibility data.

### Offensive two-target Tech cycle

`verified-runtime` for native Cyclone against three enemies; no PC `$07`
installed

The command-ready three-Roly checkpoint begins with enemy slots 3, 4, and 5
at `[14,14,14]` HP and Crono at 99 MP. The accepted route applies:

```text
Down 60:4     select Tech
A 68:4        open Tech list
A 140:4       select Cyclone
Down 220:4    choose the lower Roly cluster
A 300:4       confirm the cast
```

The matched no-cast control is byte-identical through the Down pulse and
omits only the final A. The effect frame visibly renders simultaneous damage
values `357` and `364`. At the resolved endpoint, enemy HP is `[0,14,0]` and
Crono has 97 MP; the control remains `[14,14,14]` and 99 MP. This proves that
the native target pattern selected and resolved two nonadjacent battle slots,
not merely that an animation played.

The cast and control core-state SHA-256 values are:

```text
control     118aa3337bcb10101cc8f507502129089fb646f8b5d5e1c5f91b9512fb4ffd2e
resolution  954507019a46e157e39b7dcbd0087dfd1efd7df7c98e8357e5ccd285fd0649a7
```

Every command/list/target/effect/control/resolution endpoint contains the
canary exactly once at state offset `20260`, with both guards zero. Live
`$7E2830-$287F` and saved slot `$0430-$047F` both hash to
`6007023eefa73f3f9c70da546f921dce866d3131e8c98ba978785f7ac28f82c1`,
and every disposable SRAM retains SHA-256
`a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9`.

The 25 accepted checkpoint, command/list/target/effect/control/resolution
artifacts are selected by
`references/current_cyclone_multitarget_canary_accepted_artifacts_v1.json`.
Unselected target-direction and timing probes remain excluded. This closes
one native offensive multi-target Tech class for the relocation canary; it
does not prove other targeting/effect classes or any Schala command adapter.

## Current-core attract/demo canary

`verified-runtime`, unmodified vanilla behavior

A zero-input 30,000-frame current-bsnes movie was rebound to a raw title
checkpoint captured at cold-boot frame 1,800. The paired checkpoint differs
only by the exact 80-byte Project Epoch canary at state offset `$4F24`,
corresponding to candidate `$7E2CA0-$2CEF`. From that checkpoint:

- party seeding first appears at replay frame 360; frame 359 is still zero;
- the pending request becomes `$80` at frame 415; frame 414 is zero;
- location leaves title `$01B1` for `$01F5` at frame 431; frame 430 remains
  `$01B1`;
- accepted canary endpoints cover the entry boundary, Flea battle at frame
  2,400, a Zeal field scene at 4,800, Zombor battle at 8,000, and the stable
  returned title logo at 10,800.

Every accepted endpoint retains exactly one canary with SHA-256
`4e3df1af239b20cefae9d9a2219f384a4934b1916da11b001b9e501b84e06290`,
the four-byte front and sixteen-byte rear guards remain zero, and the
disposable SRAM remains byte-exact at
`cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203`.
The external slot-1 `$0430-$047F` bytes remain at SHA-256
`b70a2e5d291811c9f58689d7d0dbbfe89b913a3c0b1ef846de4607f0af6d9c73`.
This title/attract fixture has zero name bytes at `$7E2C4D-$2C52`; they remain
zero throughout.

Matched zero/canary runs at frames 431, 4,800, and 10,800 have identical core
state lengths. Each pair differs at exactly state offsets
`20260..20339`, the canary span and nothing else. Replacing that span with the
zero control yields byte-identical complete core states, and each screenshot
pair is byte-identical. The three PNG SHA-256 values are respectively:

```text
entry         0ed7b26b91b35f00cac8a9909698a5aeec7f2b425d7f4726a7fb21d0427b3bf4
Zeal field    b110e03ffed45b74f3e5be0e37d226c60f86352002c093dfdf43b702450152a7
return title  765e763b6d12fcf0894969ebf373104f67cedf81fdd599ff2d116b1197bb0260
```

The natural PC `$07` span is independently overwritten by vanilla during the
same replay. It stays all-zero with SHA-256
`5b6fb58e61fa475939767d68a446f97f1bff02c0e5935a3ea8bb51e6515783d8`
through frame 2,130, then changes at frame 2,131 to
`53f64b10614539a07fe883a88170ae6e044bc2f79f2d7cfaf8fc980c2b0038a0`.
The candidate canary and guards remain exact across that one-frame boundary.
This runtime result confirms the statically reconstructed eight-destination
attract initializer writes natural record `$07`; it does not write the
candidate relocated block.

The 37 accepted source/checkpoint/control/end-point artifacts are selected by
`references/current_attract_canary_accepted_artifacts_v1.json`. The matched
run proves that the unmodified vanilla attract cycle does not touch the
candidate block and confirms the natural-PC07 overwrite hazard. It does not
initialize relocated compatibility data, initialize Schala, approve the
candidate allocation, or prove a general menu path; the autonomous demo
showed battle HUDs but no general pause/menu screen.

## Static lifecycle reconstruction

`verified-static`, except where a narrower label is stated

The reconstruction now accounts for every identified initialization,
serialization, reset, and erase route that directly determines ownership of
natural PC `$07` or the compatibility block. It defines the required
translation; it does not install any hook or approve `$7E2CA0-$2CEF`.

### Normal new game

`$C2:956E` copies exactly `$280` bytes from `$CC:0000` to `$7E2600`.
Those bytes are seven `$50`-byte records followed by the existing `$50`-byte
compatibility template:

```text
$CC:0000-$022F -> $7E2600-$282F  seven vanilla records
$CC:0230-$027F -> $7E2830-$287F  vanilla compatibility state
```

The required Project Epoch split is:

```text
$CC:0000-$022F       -> $7E2600-$282F  seven vanilla records
$CC:0230-$027F       -> $7E2CA0-$2CEF  relocated compatibility template
independent $50-byte -> $7E2830-$287F  Schala PC $07 record
```

`tools/schala_save_layout.py::split_new_game_seed` is the source-only
contract for that split. It requires one exact `$280`-byte vanilla seed, one
exact independently supplied `$50`-byte PC `$07` record, and a sufficiently
large bank `$7E`; wrong sizes and missing or short destinations fail closed.
It does not author Schala's still-incomplete record.

### Attract/demo

`$FD:B33F` copies exactly `$230` bytes and therefore initializes only the
seven vanilla records. The surrounding initializer at `$FD:B2DE-$FD:B33E`
nevertheless loops over eight `$50`-byte destinations. Its selected HP/MP
source block contains only seven eight-byte rows, so iteration 8 reads beyond
the selected block and writes natural PC `$07` fields at
`$2833/$2835/$2837/$2839/$283B/$283C/$283E`.

Extending `$FD:B33F` beyond source `$CC:022F` is not a solution: the following
bytes are compatibility state, not an eighth record. A production adapter
must keep the seven-record copy bounded, remove or replace the eighth
out-of-bounds row use, then provide the relocated compatibility template and
the independent PC `$07` record before any consumer runs.

`tools/schala_save_layout.py::finalize_attract_pc07_layout` models only that
last namespace split. It preserves the seven records already initialized and
requires exact caller-supplied `$50`-byte compatibility and PC `$07`
templates. It neither invents either template nor proves an installed
attract hook.

### Normal save and full load

The proposed normal-save descriptor translation replaces vanilla's first
`$5B0` region with:

```text
$7E2400 len $0430 -> slot +$0000..$042F
$7E2CA0 len $0050 -> slot +$0430..$047F
$7E2880 len $0130 -> slot +$0480..$05AF
```

The other seven descriptors remain unchanged. The resulting ten-entry table
is 50 bytes; the established `$7E9890` staging buffer has at least `$40`
bytes. The table-copy counts at `$FF:FA20/$FF:FAB8` would change from
`#$0027` to `#$0031`, and the loop stops at `$FF:FA4F/$FF:FAE6` from
`#$0028` to `#$0032`. The serialized layout remains `$834` bytes and the
vanilla checksum still covers the complete `$A00` slot.

`tools/schala_save_layout.py` models both directions. Its save model proves
that live PC `$07` cannot leak into the vanilla slot and that relocated
compatibility bytes still occupy slot `+$0430-$047F`. Its inverse
`restore_regions_from_slot` contract:

- requires one immutable, exact `$A00` slot;
- consumes exactly the native `$0834` serialized prefix through the exact
  descriptor table;
- restores slot `+$0430-$047F` only to `$7E2CA0-$2CEF`;
- leaves precleared `$7E2830-$287F` unchanged; and
- preserves the checksum-bound `+$0834-$09FF` tail.

Malformed slot shapes, missing or short destination banks, overlapping
destinations, invalid descriptor fields, and tables that do not consume
exactly `$0834` fail closed. The synthetic translated save/load round trip
reproduces the full serialized prefix. This is source proof, not an installed
writer/loader or runtime proof of the candidate allocation.

The low-level full loader performs no validation and restores roster bytes
after any earlier preclear. A future wrapper must clear PC `$07`, validate
vanilla, run the translated copy, then either validate and atomically publish
a party-consistent v2 record or sanitize exact roster `$07->$87` and clear
joined bit `$01` before `$C2:E6AB` reaches party/menu loading.

### New Game+

Vanilla `$FF:FAED-$FF:FBD2`, called at `$C2:E6D8`, copies:

```text
slot +$0000-$057F -> $7E2400-$297F
slot +$05B0-$05E2 -> $7E2C23-$2C55
```

The first move necessarily restores serialized compatibility bytes
`+$0430-$047F` over natural PC `$07`. It does not copy roster/joined state at
`$7E2980-$29AF`.

The exact Project Epoch source contract is four non-overlapping moves:

```text
slot +$0000-$042F -> $7E2400-$282F  main through PC $06
slot +$0430-$047F -> $7E2CA0-$2CEF  relocated compatibility state
slot +$0480-$057F -> $7E2880-$297F  remaining partial main state
slot +$05B0-$05E2 -> $7E2C23-$2C55  names
```

`tools/schala_save_layout.py::restore_new_game_plus_regions_from_slot`
requires an exact `$A00` source slot and exact pinned region set, rejects
source or destination overlap, and proves that the translated partial copy
leaves both `$7E2830-$287F` and `$7E2980-$29AF` untouched. This is a
source-only contract; the four moves are not installed.

`verified-runtime`, vanilla negative control only

A current-bsnes New Game+ replay from a checksum-valid unlocked slot brackets
the native partial loader. At frame 61 natural PC `$07` has SHA-256
`ca33129e383fea5c0ad8e176d7847f5118ccbbf77ea1098da9ec1f24c0451123`.
At frame 62 it changes to
`714d4e95e48bc696bdd1ba7d12471fe1487b8c2df50e1e38385d48b28a36e3f3`,
byte-exactly matching selected slot `+$0430-$047F`. Roster remains all `$80`
at that boundary, while a paired candidate canary remains exact with zero
guards. Matched zero/canary states at frames 61, 62, 90, and 300 differ only
in the 80-byte candidate span and render pixel-identical screenshots.

This proves the vanilla overwrite hazard and candidate non-access for the
bounded New Game+ route. It does not prove the translated four-move adapter,
Schala retain/reset policy, eight-PC roster reconstruction, or sidecar
persistence.

`$FF:FB3B` follows the partial copy and precedes party processing. After the
translated copy it may stage the selected retain/reset PC `$07` policy, but
it creates no new serialized slot. It must not bind or write a v2 sidecar;
rebinding waits for the first later finalized normal save.

### Reset and erase

The field cold-entry path at `$C0:000E` zero-fills
`$7E:0700-$7E:EFFF`, which includes both natural PC `$07` and the candidate
relocation. The current-core Player-1 soft-reset result independently confirms
the vanilla clear effect. A future Project Epoch reset route must repopulate
both namespaced structures after the clear and before any consumer. No such
post-reset initializer is installed.

Erase calls `$C2:E729 -> $C2:E8B7`. At `$C2:E8C6`, vanilla writes the doubled
selected slot index (`$00/$02/$04`) into that slot's magic low byte at
`$30:7FF8 + slot*2`, invalidating the native slot without clearing a full
word. A future wrapper must first invalidate exactly the corresponding
sidecar, then allow the native erase. It must not touch another slot's
sidecar.

### Required lifecycle boundaries

`proposal`, using the verified-static routes above

- full save wrapper: `$C2:CF51`, unique preimage `22 FB F9 FF`;
- full load wrapper: `$C2:E657`, unique preimage `22 A3 FA FF`;
- save-preview ID resolver: `$C2:D1C1`, preimage
  `BF 80 05 30 8F 02 42 00`;
- New Game+ translated partial-load/staging route:
  `$FF:FAED-$FF:FB3B`;
- erase caller: `$C2:E729`, preimage `20 B7 E8`;
- battle reload/template resolver: `$C1:CF15`;
- normal new-game seed: `$C2:956E`;
- attract/demo initializer and template helper:
  `$FD:B2DE-$FD:B33F`; and
- location event `$11C`, object `$09`, absolute tech-state commands for
  location `$1D1`; and
- post-clear initialization reached from field cold entry `$C0:000E`.

The normal save wrapper must invalidate the selected sidecar first, call the
vanilla writer, then hash the finalized complete `$A00` and write/validate v2
with sidecar magic committed last. Vanilla copies only `$834` bytes but its
checksum covers the full `$A00`; the untouched `+$0834-$09FF` tail is part of
the v2 binding.

`tools/schala_sidecar_v2_lifecycle.py` executes these persistence boundaries
on immutable host SRAM images. It preserves caller-finalized
compatibility/Epoch bytes, distinguishes invalid-vanilla no-copy from
post-copy party handling, stages New Game+ without a destination bind, and
breaks sidecar magic before partial erase-body clears and native invalidation.
Its all-three-slot failure matrix is source proof only; it neither validates
this WRAM relocation nor installs any listed hook.

## Direct compatibility-state consumers

`verified-static` for the listed instructions; coverage is incomplete

Relocation must adapt every path below to the new `$2CA0` base while
preserving the original byte meaning:

| Instruction(s) | Existing effective range | Use |
| --- | --- | --- |
| `$FF:F86D` | `$2837-$285B` | learned single/double/triple mask sweep |
| `$FF:F9A2` | indexed from `$2837` | rock-triple requirement checks |
| `$C1:C9A9` | `$2837-$283D` | single-tech learned masks |
| `$C1:CA56`, `$C1:CB26` | `$283E-$284C` | double-tech learned masks |
| `$C1:CD08`, `$C1:CDEE` | `$284D-$285B` | triple-tech learned masks |
| `$C1:F29C` with `$C1:F5C1/$C1:F5C7` | `$283E-$2856` | combo-learning read/modify/write pointer |
| `$C1:F3B5` with `$C1:F46F/$C1:F508/$C1:F547` | `$2830-$2836` | per-PC next-tech counters |
| `$C2:82E1` | `$2857-$285B` | equipped-rock flags |
| `$C2:B9AF` | `$2857-$285B` | five-byte rock-flag copy |
| location event `$11C`, object `$09` | `$2830-$2832`, `$2834`, `$2837-$2839`, `$283B` | magic-grant writes to four tech counts plus read/OR/write of four learned masks |

The bounded direct-reference pass found no named direct reader of
`$285C-$287F`. That is negative evidence, not proof that those bytes are
unused.

The `$C1:F29C` computed path is now bounded independently by the canonical
ROM and pinned disassembly. `$C1:F265` resets `$B2D2`; the scan advances one
five-byte `$CC:2778` record and increments that counter for every rejected
participant mask. The 26th and final record is the first and only
first-byte-`$FF` sentinel, and the sentinel exits before the pointer is built.
Thus only 25 live records can reach `$283E + index`: indices `$00-$18`, with
maximum effective address `$2856`. The read/modify/write at
`$C1:F5C1/$C1:F5C7` cannot reach the rock flags beginning at `$2857`.
None of the 25 live participant masks contains bit `$01`; vanilla has no
logical-PC07 combo group. A naively appended 26th live row would use index
`$19` and collide with the first rock flag, so Schala combo state must be
expanded separately.
`tools/audit_pc_init_record_schema.py` pins the table, scan-code, access-code,
and disassembly hashes, checks the 15 dual plus 10 triple live-group shape,
and emits semantic bounds without raw table bytes.

The complete canonical location-event corpus adds one mandatory non-assembly
adapter. `tools/audit_location_event_items.py` examines all 513 event-pointer
entries, 489 valid event IDs, and 462 unique valid packets. Among 1,511
absolute-memory commands `$48-$4E`, exactly 12 overlap the compatibility
range, all in event `$11C` object `$09`, referenced only by location `$1D1`.
They write counts at `$2830/$2831/$2832/$2834`, then read and write learned
masks at `$2837/$2838/$2839/$283B` around the script's `$E0` OR operation.
After relocation those exact fields are
`$2CA0/$2CA1/$2CA2/$2CA4` and
`$2CA7/$2CA8/$2CA9/$2CAB`. Leaving the compressed event unchanged would
silently write Schala record bytes. A future implementation must either
recompile this one packet with pinned translated operands or add an
exact-address resolver; a global remap of arbitrary event memory is not
approved.

The audit now proves the recompiled-packet operand plan without producing
installable data. It pins event `$11C`'s decompressed preimage, requires all
12 exact sites, translates only their 24 low/high operand bytes by `$0470`,
reparses the result, and rejects any remaining reference to the old block.
The `$0C6B`-byte packet length and every non-address byte remain exact.
Source and transformed SHA-256 values are recorded in
`docs/location_event_item_reference_audit.md`. This is a source-only,
decompressed-packet proof: compression, named expanded allocation, pointer
installation, and installed runtime behavior remain open. The later volatile
WRAM trace below closes only the already-decompressed event-consumer step.

The same static decode identifies the runtime gate. Spekkio object `$0A`
calls grant object `$09`, function `$03`, after storyline `$4C` and lap byte
`$7F021C=03`. A deterministic diagnostic can prepare those two bytes and
clear only the active-PC bits in `$7F01E0` from a talkable location-`$1D1`
checkpoint. Two party compositions are required to exercise all 12 accesses.
No checksum-valid ordinary-New-Game pre-grant fixture is currently present
locally, so a late End-of-Time save is navigation or explicitly prepared
diagnostic evidence only.

A controlled current-bsnes vanilla baseline now completes that diagnostic in
two profiles: the source save's Magus/Robo/Frog party and a synthetic
Crono/Marle/Lucca active party. Both reach storyline `$4D` with the predicted
tech counts, learned masks, magic flags, and TP values. Each matched
zero/canary endpoint pair differs only at the exact 80-byte candidate span;
both guards, Epoch, paired screenshots, and disposable SRAM remain exact.
This is `verified-runtime` endpoint evidence for the unmodified event branches,
not for a recompressed or installed translation, and it does not observe each
transient memory access.

A native Mesen 2.1.1 instruction trace now closes that transient-access gap
for the canonical event handler. Each zero/canary pair repeats the same
sequence; collapsing each pair, the Crono/Marle/Lucca and Magus/Robo/Frog
profiles contain exactly nine plus three unique operations at
`$C0:6797/$C0:6822`: writes of `$03` to
`$7E2830/$2831/$2832/$2834`, reads of `$1F` from
`$7E2837/$2838/$2839/$283B`, and writes of `$FF` back to those four masks.
Order, PCs, targets, values, and relative frames match between each pair.
The candidate, both guards, and Epoch name remain exact. This is
`verified-runtime` for the unmodified old-block operands only; it does not
install or prove the `$2CA0` translation. The accepted hash contract is
`references/mesen_event11c_trace_accepted_artifacts_v1.json`, with all runtime
artifacts kept private.

### Volatile relocated event `$11C` trace

`verified-runtime` for the already-decompressed packet in volatile WRAM only

The follow-up Mesen 2.1.1 diagnostic starts from the same private
location-`$1D1` checkpoint. Before any event input, it requires the complete
`$0C6B`-byte source packet at live buffer `$7F2000-$7F2C6A`, verifies the exact
12-site/24-byte source-to-transformed relation, changes those 24 operands, and
requires a complete transformed-packet match both after preparation and at
termination. The collector's explicit `write8` and `write16` calls target
`snesWorkRam` only. It then copies the complete `$7E2830-$287F` compatibility
block to `$7E2CA0-$2CEF` before applying the selected grant profile.

The initial calibration deliberately filled the entire old `$50`-byte block
with a canary. That run exposed legitimate recalculation of equipped-rock
flags at `$2857-$285B`; treating those changes as event corruption would have
been a false gate. The accepted control therefore limits zero/canary
preparation to the event-target span `$2830-$283B` and does not overwrite the
existing learned-mask/rock-flag tail. The complete prepared old block must
still be byte-exact at termination.

At each routed `$C0:6797/$C0:6822` access, the collector requires CPU Y to equal
the exact decompressed event-data command offset, direct page to equal `$0100`,
and the M flag to be set. It resolves the opcode and 24-bit operand from
`$7F2000 + Y`, requires that operand to equal the live `$CD/$D0` pointer, and
for writes requires low A before `STA [$D0]` to equal the deferred post-store
byte. The four accepted cases update only the planned candidate count/mask
targets. Candidate non-target bytes, the full prepared old block, both
candidate guards, and Epoch remain exact.

| Profile / variant | Trace bytes / SHA-256 | PNG bytes / SHA-256 |
| --- | --- | --- |
| Magus/Robo/Frog zero | `5884` / `645f6f4c1ce5ffac18a3a3cb8caf8b5115303fa4a3a5f2b32a089f55e70306fe` | `9503` / `0882eb8e58d053a0e5b2222c9615ab5a1e4530d8849ddd7388e491803417b7fb` |
| Magus/Robo/Frog canary | `5886` / `27d1330a474391220b47a4a154d06e1ee6d416771456e94110d2332c82d1e7fe` | `9503` / `0882eb8e58d053a0e5b2222c9615ab5a1e4530d8849ddd7388e491803417b7fb` |
| Crono/Marle/Lucca zero | `7715` / `70006be6c842a940de366a9102c7ee80db1f8829f9078d3bf5369368a69f090b` | `10421` / `312a56671d05c8f4a47ca0cbb65aa6dbefda0eb81068736d1dde5eb2aeea8e96` |
| Crono/Marle/Lucca canary | `7717` / `579fa7aaace23cbb1fdd1b0a040a00073552eafef2f8337ce4a616b3d644f595` | `10421` / `312a56671d05c8f4a47ca0cbb65aa6dbefda0eb81068736d1dde5eb2aeea8e96` |

The exact PNG gate now samples only when the field frame is zero modulo 16 and
Spekkio's sprite frame is 22 for Magus/Robo/Frog or 4 for
Crono/Marle/Lucca. This removes the adjacent idle-frame nondeterminism exposed
by exact image comparison.

The strict four-trace set validator requires one source compatibility image
across all cases, identical candidate endpoints and callbacks across each
zero/canary pair, exact packet/edit metadata, and the complete preservation
contract above. The current accepted private root is
`private/test_runs/mesen2/event11c_relocated_accepted_hardened_v4`; a fresh
replay through the production-safe launcher reproduced all eight hashes under
`private/test_runs/mesen2/event11c_relocated_launcher_replay_hardened_v4`.
Both four-trace sets pass the schema-v2/version-2 validator and are
byte-identical across all eight artifacts.
Acceptance v1 and v2 and their private roots remain retained as historical
evidence rather than the current acceptance set. V2 mislabeled the
incompatible hardened shape as trace-v1/collector version 1. The current
validator requires trace schema v2 and collector version 2 because that shape
removed synthesized `absolute_frame`, added phase fields, and narrowed the
explicit-write scope.

| Source-controlled contract | Bytes | SHA-256 |
| --- | ---: | --- |
| `tools/mesen_event11c_relocated_trace.lua` | `35700` | `4413876f258c091a728a8d6d53e2aea824206c5e7f9852ca476b5ee5c974070c` |
| `tools/validate_mesen_event11c_relocated_trace.py` | `24820` | `2025a749fc3081ff7a6dfeb49b7b1c9aa6ae31241c4744be14c23d63e06de186` |
| `tools/run_mesen_event11c_relocated_trace.py` | `43512` | `78371ecb3974046d170d6613239d08c3b7a56252681af0bb352dac12e4676b4c` |
| `references/mesen_event11c_relocated_trace_accepted_artifacts_v3.json` | `8934` | `839b86310dbe33273cf14ffec01386aa4ee6b88426b100be2cdc65d17a0790cc` |

The launcher derives both raw packets ephemerally from the pinned private ROM,
exact-byte compiles and executes its pinned Python modules, and only reads and
hashes the legacy launcher source for provenance; that legacy source is not
executed. It stages a unique disposable ROM/SRAM pair, isolated Mesen app, and
verified collector/checkpoint bytes. Collector output is staged first, then
the trace/PNG pair is published with exclusive `xb` creation and
identity-limited rollback if pair publication cannot complete. Packet files
and the staging tree are deleted after validation. Source ROM, checkpoint,
SRAM, shared Mesen saves, and staged inputs all pass post-run identity checks.
Loading the checkpoint and executing the game may still alter other transient
emulator state; only the collector's explicit writes and the host-visible
source-file/shared-save preservation claim are bounded here.
This does **not** prove recompression, a ROM allocation or pointer, an installed
hook, global ownership of `$2CA0-$2CEF`, natural PC `$07`, or any save/load,
erase, reset, or New Game+ adapter.

The scan finds no absolute-command
overlap with `$285C-$287F`, but that negative result is not ownership proof.

Reconstructed files still retain hidden `incbin` spans plus possible other
computed pointers and block moves. Therefore the consumer list and candidate
ownership are not globally complete; the remaining static bounds and runtime
watchpoint matrix stay mandatory.

## Remaining approval matrix

- [x] Static front/rear structural bounds.
- [x] No direct pinned-source reference to the candidate span.
- [x] Loaded-field idle canary.
- [x] Menu-overlay entry canary.
- [x] Short menu cursor, page-entry, cancel, and overlay-exit matrix.
- [x] Short submenu cursor and return matrix.
- [x] Native full-menu entry and 600-frame idle.
- [x] Current-core field idle and native main-menu entry with exact canary.
- [x] Current-core Equipment entry and Crono-to-Marle selection.
- [x] One native seven-character party exchange with an actual roster swap.
- [x] Native battle entry and 600-frame idle.
- [x] Current-core seven-PC party exchange with an actual roster swap.
- [x] Current-core vanilla full-party reserve registration, naming, and
      newly recruited Magus active-party insertion.
- [x] Current-core normal narrative battle entry and 600-frame battle idle.
- [x] Current-core final-save route through Lavos Core transition, dialogue,
      and native Lavos battle entry.
- [x] Legacy even-ID battle-menu calibration for player 1 plus player-2
      controls, with native Confirm transition and canary preservation.
- [x] Complete current-core Player-1 twelve-button top-level battle-menu
      calibration with isolated four-frame pulses.
- [x] Inert ExHiROM full-menu, post-swap party-exchange, and battle-engine
      checkpoint replays with payload-exact repeated controls.
- [x] Current-core inert ExHiROM field, menu, and Equipment/Marle controls
      with byte-exact raw states and pixel-exact screenshots.
- [x] Inert ExHiROM title/Continue/full-load replay for all three vanilla
      slots, with the expected cleared-block negative control.
- [x] Remaining main-menu pages and one native Tech owner switch.
- [ ] Party exchange with all eight distinct roster identities and PC `$07`.
- [x] Equipment page entry, rendering, and 600-frame idle.
- [x] One native equipment change with derived Attack recomputation.
- [ ] Shop menus.
- [x] Normal-attack command confirmation reaches the native attack flow.
- [x] Complete one native normal-attack target/damage cycle with a matched HP
      control.
- [x] Native Tech submenu entry and rendering; no tech selected or cast.
- [x] One native Heal selection/self-target/effect cycle with matched HP/MP
      control.
- [x] One native Item list/target/consumption cycle with a matched no-use
      control.
- [x] One natural three-enemy victory, reward, battle exit, and field return.
- [x] One native offensive two-target Tech cycle with matched no-cast
      control.
- [ ] Remaining Tech target/effect classes, character death, status, and
      criticals.
- [x] Isolated native slot-1 save and fresh-process full reload, including
      exact `$0430-$047F` to `$7E2830-$287F` restoration.
- [x] Source-only normal new-game split and attract finalizer contracts reject
      malformed inputs and keep PC `$07` separate from compatibility state.
- [x] Source-only inverse normal-load contract consumes exactly `$0834`,
      restores `+$0430-$047F` to the candidate, and preserves precleared PC
      `$07`.
- [ ] Project Epoch sidecar write/load, all three slots, erase, and
      power-cycle persistence.
- [x] Host-only all-three-slot sidecar save/load/NG+/preview/erase ordering and
      partial-write refusal model.
- [x] Unmodified current-core New Game+ negative control proves the native
      partial loader overwrites PC `$07` from slot `+$0430-$047F` while the
      candidate canary survives.
- [x] Source-only exact four-region New Game+ translation preserves PC `$07`
      and roster/joined state.
- [x] Canonical post-battle combo-learning index is bounded to
      `$7E283E-$7E2856`; it cannot reach rock flags `$2857-$285B`.
- [x] All canonical location-event absolute-memory commands are scanned;
      event `$11C`/location `$1D1` contains the only 12 compatibility hits.
- [x] Source-only event `$11C` transform rejects preimage drift and changes
      exactly the 12 address operands to `$2CA0-$2CAB` in memory.
- [x] Controlled unmodified event `$11C` magic-grant baseline completes the
      two prepared party profiles with matched zero/canary terminal states.
- [x] Native Mesen instruction trace observes all 12 unmodified event `$11C`
      compatibility accesses with exact PC, target, value, and order.
- [x] Volatile already-decompressed event `$11C` magic-grant path updates
      `$2CA0-$2CAB` while the prepared old `$2830-$287F` block remains exact.
      This is not a recompressed or installed ROM path and does not activate
      Schala's natural record.
- [ ] Installed Project Epoch New Game+ translated copy, retain/reset staging,
      eight-PC roster reconstruction, and later normal-save rebinding.
- [x] Unmodified current-core attract cycle preserves the candidate and
      independently overwrites natural PC `$07`.
- [ ] Project Epoch attract/demo compatibility and Schala initialization.
- [x] Current-core Player-1 vanilla soft reset clears the candidate block.
- [ ] Soft reset followed by Project Epoch initialization.
- [x] First generic native-Mesen callback/access-counter ownership tranche:
      calibration, field idle, main menu, and event `$11C`, each with matched
      zero/canary candidate preparation.
- [x] Second menu-only native-Mesen ownership tranche: Equipment and Tech
      owner switching, Item Use/Move, and Party Exchange, each with matched
      zero/canary preparation and a fixed 600-frame endpoint.
- [x] Bounded native-Mesen Lavos command-ready tranche: frame-zero
      calibration plus 60-frame idle, Down/Up command round trip, and
      Down-to-Tech routes, each with matched zero/canary preparation.
- [x] Bounded native-Mesen Lavos battle-action tranche: no-input action
      control, Attack target hold, and one Crono critical Attack through
      command recovery, each with matched zero/canary preparation and exact
      replay.
- [ ] Watchpoints for computed/block-move access across the full matrix.

Until these pass, `$7E2CA0-$7E2CEF` remains a preferred candidate rather than
an approved allocation.

## Accepted native-Mesen WRAM ownership census

The first generic ownership tranche is now `verified-runtime`. It is separate
from the event `$11C` relocated-packet experiment: this collector does not
rewrite an event packet or install a ROM change. It watches all 196 bytes in
these seven ranges:

| Range | Role |
| --- | --- |
| `$7E2830-$287F` | active vanilla compatibility block / positive control |
| `$7E2980-$2988` | serialized active-party roster sentinel |
| `$7E29AF` | joined-mask sentinel |
| `$7E2C4D-$2C52` | protected Epoch name |
| `$7E2C9C-$2C9F` | structural front guard |
| `$7E2CA0-$2CEF` | unapproved relocated-block candidate |
| `$7E2CF0-$2CFF` | structural rear guard |

Each scenario runs twice from the exact Mesen 2.1.1 checkpoint. The zero
variant asserts that the candidate is already zero and writes nothing to it.
The canary variant writes exactly 80 deterministic bytes before callbacks and
access counters arm. Preparation is therefore excluded from the observation
window by construction, and the collector requires every watched counter to
be zero immediately before tracing.

| Scenario | Terminal frame | Callbacks | Reads | Writes | Measured activity |
| --- | ---: | ---: | ---: | ---: | --- |
| calibration | `0` | `0` | `0` | `0` | observer/control must remain empty |
| field idle | `600` | `450` | `450` | `0` | 150 reads each at `$2980-$2982` |
| main menu | `600` | `124` | `124` | `0` | 52 old-block reads, 72 roster reads |
| event `$11C` / Frog | `1500` | `1224` | `1197` | `27` | 118 old-block callbacks, 1,106 roster reads |

The Frog event positive control is exact:

1. frame 985: write `$7E2834=$03`, callback PC `$C0:6824`;
2. frame 989: read `$7E283B=$1F`, callback PC `$C0:6799`;
3. frame 989: write `$7E283B=$FF`, callback PC `$C0:6824`.

The same trace also records 25 legitimate same-value writes to
`$7E2857-$285B` at `$C2:82E7/$C2:82F3`. Those writes are not hidden or
misclassified as Project Epoch activity: the validator permits them only in
the event scenario, proves each one writes the already-simulated value, and
requires the complete zero/canary callback streams to be identical.

Across all eight accepted traces:

- the candidate and both guards receive zero read or write callbacks;
- Epoch, roster, and joined state receive no writes;
- every per-byte Mesen access counter equals the independently recorded
  callback count;
- zero/canary callbacks, counters, termination, and all non-candidate endpoint
  bytes match exactly;
- the accepted root and a fresh launcher replay are byte-identical across all
  16 JSON/PNG artifacts.

Mesen 2.1.1 required two version-specific adaptations. Its
[Lua API documentation](https://github.com/SourMesen/Mesen2/blob/2.1.1/UI/Debugger/Documentation/LuaDocumentation.json)
lists the access-counter arguments in the opposite presentation order from
the order consumed by the tagged binding, so the working call is
`emu.getAccessCounters(memoryType, counterType)`. Raw `snesWorkRam`
callbacks also report CPU-relative addresses; the collector normalizes them
with `emu.convertAddress(..., snesMemory, snes)` before range classification.
Read callbacks expose the post-read PC while writes expose the advanced store
PC, hence `$C0:6799/$C0:6824` above. The exact implementation references are
the tagged
[Lua binding](https://github.com/SourMesen/Mesen2/blob/2.1.1/Core/Debugger/LuaApi.cpp),
[call helper](https://github.com/SourMesen/Mesen2/blob/2.1.1/Core/Debugger/LuaCallHelper.cpp),
[scripting context](https://github.com/SourMesen/Mesen2/blob/2.1.1/Core/Debugger/ScriptingContext.cpp),
and
[access-counter implementation](https://github.com/SourMesen/Mesen2/blob/2.1.1/Core/Debugger/MemoryAccessCounter.h).

The renderer can expose either adjacent Spekkio presentation buffer even when
the route fields and trace endpoint are identical. The collector therefore
freezes and disarms the trace at the first valid end-of-frame route endpoint,
then waits without recording further accesses for the exact canonical
9,503-byte PNG. This does not extend or edit the measured callback stream.

Current source and evidence roots:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `tools/mesen_wram_ownership_trace.lua` | `40088` | `d5dd2b2d7085237844d95ab04f7007b6b2d17b2e1160f23857018319380b7569` |
| `tools/validate_mesen_wram_ownership_trace.py` | `29388` | `89a7dc86c6b5b10dc984b778451152e4734b5c553a669b7ee033e465ca87f2ba` |
| `tools/run_mesen_wram_ownership_trace.py` | `40447` | `80f25f577da219d383829dfc977564d8295d1e0691ae4a2823da3e41079fa203` |
| `references/mesen_wram_ownership_scenarios_v1.json` | `14145` | `e9ea3ec765d3c14511f11815f1155c66c63f4cda1b23d445a2274ade0d8831d9` |
| `references/mesen_wram_ownership_accepted_artifacts_v1.json` | `10813` | `b8f863ab2db7ed5f17222c59044a026305a05db86a7a0303fc3db84bfa197142` |

- accepted private root:
  `private/test_runs/mesen2/wram_ownership_accepted_v2`;
- independent replay root:
  `private/test_runs/mesen2/wram_ownership_replay_v2`.

This tranche is evidence against ownership in four specific routes, not proof
of global freedom. Battle, save, load, New Game+, erase, reset, attract,
shops, equipment, naming, and additional field/menu routes remain mandatory.
No allocation, hook, compatibility relocation, PC `$07` record, or Schala
installation is approved.

## Accepted menu-only native-Mesen ownership extension

The second generic tranche derives a private collector from the exact accepted
v1 collector rather than changing the v1 source. The builder rejects any v1
preimage drift, changes only the scenario/input/schema regions, and stages the
41,089-byte Lua source below the disposable private run. That generated source
is deleted after every launch.

The same seven ranges and all 196 per-byte counters remain in force. Four
fixed 600-frame routes now exercise menu paths that were outside the first
tranche:

| Scenario | Endpoint | Callbacks | Reads | Writes | Measured activity |
| --- | --- | ---: | ---: | ---: | --- |
| Equipment owner switch | Frog Equipment page | `124` | `124` | `0` | 52 old-block reads, 72 roster reads |
| Tech owner switch | Frog Tech page | `137` | `132` | `5` | 65 old-block callbacks, 72 roster reads |
| Item list/cancel | Item Use/Move page | `124` | `124` | `0` | 52 old-block reads, 72 roster reads |
| Party page/cancel | Party Exchange page | `2117` | `2117` | `0` | 52 old-block reads, 2,065 roster reads |

Entering Tech exposes one exact native sorting sequence at frame 221:

1. sequence 124/125 writes `$00` to `$7E2857/$7E2858` from `$C2:82E7`;
2. sequence 127/129/131 writes `$00` to `$7E2859-$7E285B` from
   `$C2:82F3`.

The validator accepts that sequence only in `tech-owner-switch`, with exact
sequence number, frame, address, value, and PC. Reconciliation proves all five
writes are same-value and the pre/post bytes remain `0000000000`. Any extra,
reordered, moved, or changing old-block write fails. Old-block writes remain
forbidden in the other three scenarios.

Across the final eight-trace set:

- the candidate and both structural guards receive zero callbacks;
- Epoch, roster, and joined state receive no writes;
- every access counter reconciles with the independent callback log;
- each zero/canary pair has identical callbacks, counters, and termination,
  with equivalent endpoints after candidate normalization;
- the accepted and independent replay roots are byte-identical across all 16
  JSON/PNG artifacts.

Current source and evidence roots:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `tools/build_mesen_wram_ownership_menu_collector_v2.py` | `8526` | `bb68dbe03d2a92dac265dd5c0b378a56e942229f0d5cf1c209a11ac86b82823a` |
| generated private collector | `41089` | `7ec953af6e4899b4a91f8a5edf9f5e20236b9a32dbdff4ad1fbb3813efc71f05` |
| `tools/validate_mesen_wram_ownership_menu_trace_v2.py` | `9878` | `2dc71df20769644f6065f36311095ea7882142d066dbd717f36994521a94922b` |
| `tools/run_mesen_wram_ownership_menu_trace_v2.py` | `17517` | `6041d89b869215316292440e3bd53a68645b46594fbe08d111fd2704cfc23efe` |
| `references/mesen_wram_ownership_menu_scenarios_v2.json` | `12298` | `e0dbb86a513de2a45bf9c1a83af0b50b0bef08d5b20b5e21398de6da29222c99` |
| `references/mesen_wram_ownership_menu_accepted_artifacts_v2.json` | `11785` | `c6978ec88c573dd4181e42d4645cbbd76b85612574cacfe4f8e0ef3d59bd2e04` |

- accepted private root:
  `private/test_runs/mesen2/wram_ownership_menu_v2_accepted_v2`;
- independent replay root:
  `private/test_runs/mesen2/wram_ownership_menu_v2_replay_v2`.

The exact input schedules contain no final item-use, equipment-change,
party-swap, or save confirmation. Roster/joined writes are directly watched
and absent. Inventory and equipment arrays are not watched, however, so the
screenshots and schedules are route witnesses rather than byte-level proof
that those systems are unchanged. The endpoints also remain within their menu
pages; full leave-page flows remain untested.

This extension still does not prove global ownership, approve
`$7E2CA0-$2CEF`, install the relocation, create natural PC `$07`, or alter
Epoch. Battle, save/load, New Game+, erase, reset, attract, shops, naming, and
wider field/menu coverage remain required.

## Accepted native-Mesen Lavos battle ownership extension

The third, command-only ownership tranche adds a real command-ready battle
boundary without installing a ROM hook or executing an attack. Its source
state is the accepted native-Mesen Lavos checkpoint produced from the
recovered pre-Lavos SRAM:

- native state: `261614` bytes,
  `d5825ffff2f2a3b7edbe3c37e7118155d67727dc02ed672d13257f3824482b8b`;
- decoded core: `324388` bytes,
  `8369e220290e1afc27138df5a1f999dee83cb4fdb462bc13c152ef1c313ecf4c`;
- endpoint: location `$01DB`, storyline `$D6`, pending battle `$01`;
- active party `00 01 02`, roster `00 01 02 82 80 04 03 06 05`, joined
  `$FE`;
- combatant vector `00 01 02 CD FF FF CC FF FF FF CB 00`;
- current/max HP `969,898,909,8000,12000,20000`;
- battle UI `00 59 AC` and initial command state
  `0000000000ffff000100000000`.

The checkpoint acquisition and independent fresh-load proof are frozen by
`references/mesen_lavos_battle_checkpoint_accepted_artifacts_v1.json`. The
fresh control performs Down at frames `20-23` and Up at `32-35`, restoring
Attack. The second proof performs only Down and ends on Tech. Both stop at
frame 60 with the same complete non-command battle anchors and full HP. The
four deterministic checkpoint artifacts repeat exactly; PNG hashes do not and
are explicitly presentation-only.

The ownership collector is derived from the exact accepted v1 collector. It
never writes the ROM. Before observers arm, the zero variant asserts that
`$7E2CA0-$2CEF` is zero, while the canary variant writes the same deterministic
80-byte Project Epoch canary. Both guards and Epoch must already match their
pinned preimages. The first calibration correctly rejected the inherited
Spekkio direct-page assumption; the loaded Lavos state reports and now pins
`D=$0000`.

Four scenarios run as exact zero/canary pairs:

| Scenario | Input | Capture | Command endpoint | Callbacks |
| --- | --- | --- | --- | ---: |
| calibration | none | immediately after observer arm, frame `0` | Attack | `0` |
| battle idle | none | `endFrame` after input poll `60` | Attack | `0` |
| command round trip | Down `20-23`, Up `32-35` | `endFrame` after input poll `60` | Attack | `0` |
| command down | Down `20-23` | `endFrame` after input poll `60` | Tech | `0` |

Across both accepted and independent replay roots:

- all eight JSON trace bytes repeat exactly;
- every one of the 196 watched per-byte counters reconciles with the callback
  log;
- the old `$7E2830-$287F` compatibility block receives zero reads or writes;
- the candidate and both structural guards receive zero reads or writes;
- roster, joined, and Epoch receive no writes;
- all scenarios share one normalized checkpoint preimage;
- all non-command battle anchors, the complete 12-byte combatant vector, full
  HP, and battle UI `$0059AC` remain exact;
- the Down endpoint advances only the active command cursor from Attack to
  Tech; no action executes.

Screenshots remain private supporting evidence. Some independent acquisitions
produce a different rendered Lavos frame even while the state and JSON trace
are byte-identical, so PNG identity is never an acceptance gate.

Current source and evidence roots:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `tools/build_mesen_wram_ownership_battle_collector_v3.py` | `21160` | `443d521ffa435ffddaa2b9ebdd68bc66c22b144e125fe91e9bebef38817cdf91` |
| generated private collector | `41269` | `7491d1c6a8a3962884baeaf9997df4659c4a53d3f67b3c6ac69999d08f6ee68b` |
| `tools/validate_mesen_wram_ownership_battle_trace_v3.py` | `20095` | `b5ecc2c3cd81d34e5cc94428fcd45bbd39496c4ba1080a97db3c47380a6f5155` |
| `tools/run_mesen_wram_ownership_battle_trace_v3.py` | `23798` | `ed3bc349bc97705a434c2cef14e7f80c517a2a5ca143f40a4c77ccb84eb49095` |
| `tests/test_mesen_wram_ownership_battle_v3.py` | `34577` | `55aec26b3b129fb73940c8fb7bdeb890c7dedaaccd97a8023f8c9d1ec13e365f` |
| `references/mesen_wram_ownership_battle_scenarios_v3.json` | `7042` | `934e56f08585e315c37287f9351773473125874f6ca6296f10e0af746c20f83a` |
| `references/mesen_wram_ownership_battle_accepted_artifacts_v3.json` | `10855` | `203dd4409d4d662ac76f88c0b52b1f358fe829ddea7efacdf8f86bd1cc3900b3` |

- accepted private root:
  `private/test_runs/mesen2/wram_ownership_battle_v3_accepted_v2`;
- independent replay root:
  `private/test_runs/mesen2/wram_ownership_battle_v3_replay_v2`.

This battle-v3 tranche is `verified-runtime` evidence only for calibration,
idle, and command navigation during the first 60 frames of the accepted Lavos
command window. It does not itself cover attack/Tech/Item execution, enemy
action, damage, status, death, victory, teardown, persistence, reset, attract,
shops, equipment, or naming. It therefore removes one battle-command
uncertainty but does not approve the relocation or either WRAM range as
globally free.

## Accepted native-Mesen Lavos battle action/recovery extension

The fourth ownership tranche derives from the same exact command-ready state
and keeps the same seven ranges and 196 per-byte counters. It adds a compact
action timeline sampled at frame zero and whenever its complete signature
changes. The signature includes selected combatant HP/status, target state and
list, PC FIFO and command records, action request/targets/slots, menu-ready,
logic-busy and AI state, resolution flags, battle UI, and command state.

Three scenarios run as exact zero/canary pairs:

| Scenario | Input | Terminal / last signature | Rows | Current HP endpoint | Battle UI | Command-state endpoint |
| --- | --- | --- | ---: | --- | --- | --- |
| action control | none | `606 / 603` | 269 | `739,821,712,8000,12000,20000` | `03bf59` | `00000000000102000300000000` |
| Attack target hold | A `20-23` | `60 / 60` | 17 | `969,898,909,8000,12000,20000` | `0059ac` | `0000000000ffff000100000000` |
| Attack recovery | A `20-23`, A `32-35` | `606 / 606` | 206 | `739,821,712,7038,12000,20000` | `003a00` | `01000000ff01ff010100000000` |

The exact endpoint rows are stronger than the summary table: the validator
pins every field of the final action signature. It also requires these causal
milestones:

- the control's already-in-flight enemy action damages only the party at frame
  336, followed by an action-request transition at frame 363;
- the target-hold route enters Attack target selection at frame 20;
- the recovery route enqueues the player command at frame 32, receives the
  same enemy-only party damage at frame 337, dequeues the player command at
  frame 373, exposes the `$AE9B` bit-`$80` critical marker at frame 375,
  lowers enemy slot 3 at frame 557, and returns to a command-ready state at
  frame 606.

The control and recovery party endpoints match exactly at `739,821,712`.
Enemy HP remains `8000,12000,20000` in the control, while the recovery route
changes only slot 3 from `8000` to `7038`. The target-hold endpoint retains the
complete full-HP preimage.

Across the accepted and independent replay roots:

- every one of the 196 per-byte counters reconciles with the callback log;
- the old compatibility block, candidate, and both guards receive zero
  measured access;
- after observers arm, no watched byte is written;
- in each Attack-recovery variant, the only callbacks are the same two reads
  of roster byte `$7E2980=$00` at frame 377, with advanced callback PCs
  `$C1:4A43` then `$C1:438A`;
- the zero/canary timelines, callbacks, counters, battle snapshots, and
  termination records are identical; and
- all six accepted JSON traces are byte-identical to the independently
  acquired replay traces.

The two roster reads identify concrete Attack adapter consumers. The
read observed at advanced PC `$C1:4A43` follows `LDA $2980,Y`; the read at
advanced PC `$C1:438A` follows `LDA $2980,X` before the per-PC critical-Attack
selector lookup on this accepted route. They do not prove either consumer
accepts logical PC `$07`.

The acceptance contract is
`references/mesen_wram_ownership_battle_action_scenarios_v4.json` (`12552`
bytes, SHA-256
`ad6d686bdc01f93ce9abed3c21beb4a2bac5d5142883f94fc29c6e3f06c6f727`).
It pins all six trace hashes, sources, schedules, endpoint signatures, watched
ranges, and controls.

The complete source/private-evidence manifest is
`references/mesen_wram_ownership_battle_action_accepted_artifacts_v4.json`
(`11045` bytes, SHA-256
`0d0936cccb1640109eeab09b870281ff638e736bcd75b1b77fc2ce93a319c2d6`).

The private roots are:

- accepted:
  `private/test_runs/mesen2/wram_ownership_battle_action_v4_accepted_critical_v2`;
- independent replay:
  `private/test_runs/mesen2/wram_ownership_battle_action_v4_replay_critical_v2`.

Screenshots remain private supporting evidence and are not an acceptance gate;
some differ even when their JSON traces are byte-identical.

This tranche is `verified-runtime` only for one already-in-flight enemy action,
one Attack target-selection state, and one Crono critical Attack through
recovery. It does not approve `$7E2CA0-$2CEF`, the compatibility relocation,
or PC `$07`. Noncritical Attack, attacks by other PCs, Tech, Item, status,
death, victory, teardown, persistence, save/load, New Game+, erase, reset,
attract, shops, equipment, and naming remain outside this tranche.
