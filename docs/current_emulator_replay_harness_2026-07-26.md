# Project Epoch current-emulator replay harness

Status: active current-core test baseline  
Evidence: `verified-runtime` for the bounded runs listed below  
Production ROM integration: not performed  
Last updated: 2026-07-28

## Result

Project Epoch now has a deterministic test path on RetroArch 1.22.2 and the
current 64-bit bsnes core. The old RetroArch 1.7.1/bsnes2014 installation is
preserved only so existing evidence remains reproducible; it is not the
baseline for new approvals.

The current harness has completed all of these bounded checks:

- canonical clean-ROM and supported-slot 120-frame boot smokes;
- a 3,599-frame zero-input recording with a disposable recovered SRAM;
- recorded title entry, Continue, slot-1 load, and field initialization;
- extraction of the resulting current-core state from RetroArch's RASTATE
  container;
- construction and replay of a raw-state BSV2 field checkpoint;
- 600-frame field idle with the exact `$7E2CA0-$7E2CEF` canary;
- native main-menu entry and 600-frame idle with the canary exact once;
- Equipment-page entry, rendering, and a switch from Crono to Marle;
- native seven-PC party exchange with an actual Crono/Frog roster swap;
- checksum validation and isolated loading of a downloaded pre-Magus SRAM;
- the complete North Cape decision scene through both the native fight and
  full-party Magus recruitment branches;
- reserve registration before Magus name acceptance, followed by native party
  exchange and newly recruited Magus active-party insertion;
- independent Player-1 calibration of all twelve joypad IDs at the native
  Frog-versus-Magus command menu, including navigation, pause, command-window
  position, Tech-submenu entry, one complete Heal selection/self-target/effect
  cycle, and one complete normal-attack target/damage cycle against matched
  controls;
- isolated native slot-1 save followed by fresh-process full reload, including
  byte-exact `$0430-$047F` restoration to `$7E2830-$287F`;
- a normal walk from the recovered Lavos Tunnel save point into Lavos Core,
  followed by bounded dialogue and native final-battle entry;
- an isolated Player-1 Select+Start+L+R soft reset;
- matched 4 MiB/8 MiB inert-ExHiROM field, menu, and Equipment controls.
- a controlled two-profile execution of the canonical Spekkio event `$11C`
  magic-grant branches with matched zero/canary endpoints.

The current-core soft reset visibly returned to the pendulum intro and cleared
the entire candidate block to zero. This is useful vanilla behavior evidence,
not approval of the candidate allocation: Project Epoch still needs a
post-reset initialization path that reconstructs the relocated compatibility
record and Schala state before either can be consumed.

The inert ExHiROM controls are stronger than a boot smoke. After changing only
the BSV2 content CRC, both mappings produced byte-identical raw current-core
states and pixel-identical screenshots at:

- 600-frame field idle;
- native main-menu idle;
- Equipment after switching from Crono to Marle;
- the complete 3,599-frame zero-input field replay.

No production hook, ROM allocation, Epoch data, character record, save layout,
or game content was changed by these tests.

## Emulator pin

### Active installation

- RetroArch: 1.22.2, Git `69a4f0e`
- Installed executable:
  `private\tools\RetroArch-1.22.2\retroarch.exe`
- Executable SHA-256:
  `81c11b6f24932bf7918f05eee8928035bff3887335fd2a081507c75e9d94d06a`
- Portable archive SHA-256:
  `b2139b1d0f9d4526dc6b5ce23cbb3efdc766096fa6f2c3df016818b486ac6372`
- Core:
  `private\tools\RetroArch-1.22.2\cores\bsnes_libretro.dll`
- Core display version: 115
- Core DLL SHA-256:
  `003c7de04adef5f64fa106ef5175a0f66b08032001bde0383af97c5e5b81d470`
- Core download archive SHA-256:
  `6372add6a383a9373c27f97a2378f6a1ed9fb5e4e419d74cb4ba3601f59f2965`

The frontend came from the official
[RetroArch 1.22.2 Win64 stable directory](https://buildbot.libretro.com/stable/1.22.2/windows/x86_64/).
The core came from the official
[current Win64 core directory](https://buildbot.libretro.com/nightly/windows/x86_64/latest/).
The current source line is
[libretro/bsnes-libretro](https://github.com/libretro/bsnes-libretro).

### Preserved legacy installation

- RetroArch 1.7.1 executable SHA-256:
  `bb8d1bb0a781c3fab2c4d08dd9d1dd1abe365cd5c339af6353870e73bdd79a76`
- bsnes2014 Performance DLL SHA-256:
  `4d1708574ae059cb4f43ad995c0276ca03e2693bc6a7612e4e8f4343d48a317d`

Nothing in the new installation overwrote the legacy installation.

## Save-file safety

Current bsnes deliberately returns no frontend `RETRO_MEMORY_SAVE_RAM` buffer.
Its source says to rely on higan to load and save SRAM, and its program layer
opens:

```text
<RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY>/<content-stem>.srm
```

That explains RetroArch's apparently contradictory
`[SRAM] Skipping SRAM load` log. It describes only the frontend memory path;
the core opens the same-stem file itself. The relevant source is
[`libretro.cpp`](https://github.com/libretro/bsnes-libretro/blob/master/bsnes/target-libretro/libretro.cpp)
and
[`program.cpp`](https://github.com/libretro/bsnes-libretro/blob/master/bsnes/target-libretro/program.cpp).

`--sram-mode=noload-nosave` and `load-nosave` do not prevent this
core-managed file from being opened for persistence. Therefore every current
bsnes run must use:

1. an isolated save directory;
2. a disposable SRAM copy whose stem exactly matches the disposable ROM;
3. hashes before and after the run.

The working copies stayed content-identical at SHA-256
`cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203`,
although their timestamps can change when the core closes them. The canonical
recovered save was never used as the core's live output file.

The separately acquired pre-Magus source SRAM and all of its named disposable
copies stayed content-identical at SHA-256
`a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9`.
`tools/inspect_ct_srm.py` validates the exact 8 KiB size, all three slot magic
values, and the game's chained-carry checksums before an acquired file can
enter the harness. Source provenance and slot anchors are in
`docs/vanilla_magus_recruitment_runtime_trace_2026-07-26.md`.

A BSV2 initial state also contains the core's cartridge SRAM. Reusing a movie
recorded against a different save can therefore restore that older SRAM in
emulated memory even when the same-stem disk file is correct. The North Cape
route uses a fresh zero-input recording made with the selected source loaded:
`north_cape_boot_zero_fresh.bsv`, SHA-256
`fbdf79557ee217bc217cee8fe7698c5a9e7a9d9794a01d7898272703309aa2bd`.

## BSV2 model

RetroArch 1.22.2 records a 40-byte BSV2 header, a versioned initial-state
block, and self-sized frames. Each input record is:

```text
u8 port, u8 device, u8 index, u8 pad, u16 id, i16 value
```

The source format is in
[`input/bsv/bsvmovie.c`](https://github.com/libretro/RetroArch/blob/master/input/bsv/bsvmovie.c).
The editor changes only the existing signed 16-bit value of an exact
Player-1 tuple `(port=0, device=1, index=0, id=button)`. It refuses to insert a
record, resize a frame, edit a duplicate/missing event, or start from a
nonzero replay unless explicitly allowed.

The 3,599-frame baseline has:

- 187 frames with no queried input records;
- 3,412 frames with exactly 24 records;
- one record for every Player-1 and Player-2 joypad ID `$00-$0B` in each
  populated frame;
- all values zero;
- no replay checkpoints.

The slot-load replay differs from this baseline in exactly 12 existing
low-value bytes:

- Player-1 Left, ID `$06`, frames 1800-1801;
- Player-1 A, ID `$08`, frames 1950-1959.

No header, initial-state, count, identity tuple, token, frame size, or
back-distance byte changed.

## State and WRAM anchors

The field-exit RASTATE has one replay chunk and one raw `MEM ` core-state
chunk. Its core state is 290,423 bytes, begins with `BST1` version `115.1`,
and has SHA-256
`8eab6e3da63bc1ee48671c175bb09ef65bc92f903f02e5b8e1b18dee4ec7175b`.

The save-slot Lucca and Magus records independently anchor current-core live
WRAM at state offset `$2284`. Therefore:

```text
live WRAM base                  state +$2284
$7E2CA0-$7E2CEF candidate      state +$4F24-$4F73
structural front guard         $7E2C9C-$7E2C9F
rear observation guard         $7E2CF0-$7E2CFF
```

The unmodified checkpoint has an all-zero candidate SHA-256 of
`5b6fb58e61fa475939767d68a446f97f1bff02c0e5935a3ea8bb51e6515783d8`.
The 80-byte canary SHA-256 is
`4e3df1af239b20cefae9d9a2219f384a4934b1916da11b001b9e501b84e06290`.

For reset states where loaded character records no longer exist, the
inspector accepts the `$2284` base only when the exact 290,423-byte current
BST1 `115.1` signature matches. It does not generalize the offset to another
core or state size.

## Runtime evidence

| Check | Input/artifact SHA-256 | Output SHA-256 | Result |
| --- | --- | --- | --- |
| Zero boot record, 3,599 frames | `5c3fc0c4f8f6dc1a8e7afec94337db511115e82fd1b10bc2f1e41606a20be696` | same replay | Zero tagged inputs; no checkpoints |
| Continue and slot-1 load | `e5f3a39be18256fd201609cb49bd985f06ee6629f7221b4cdf1164d6d1a1f917` | screenshot `576750edc0df3330e189aeb1cc1fba03dfc531c9d272c2c56a9a631c18c77aa9` | Reached the saved field |
| Field RASTATE capture | slot-load replay above | `1b90d442e540bc93cc738b87ece25bc0869c8329dadfff2b170996c019930862` | Raw current-core state extracted and anchored |
| Raw field checkpoint | `dc8d69dc42d5a488181c6bdd3c60f2a94b9bff01296750d17d5a1d244eab11f5` | screenshot `bdda05df239a6cefb712409bd5ec07fcb83b1f2239ccfaabaa07ca5a9ae511d3` | Reloaded field; 600-frame idle passed |
| Canary field idle | `45ba83960deedf7e71f07820ea8039eab55d4402a0a34e059b4a8e297bd1c40c` | RASTATE `2dfa7c86805e70741c84254451cc9f138cb3b3e615ad7e03369026e5a1456a27` | Canary exact once; guards zero |
| Native slot-1 save | `a22b74476e2c6d811aff7346405d001a898421ed5c834bd1e388c6044112bf02` | RASTATE `220aebb324a81dc44412c04443411a4b4aa09520c44492b5c286bd3485f62cb1` | Save #63 written; checksum `$FAF7`; protected record/Epoch exact |
| Fresh-process Save #63 reload | `c4bf99b62fbd4e23a3285eedf842d494c7fc9a1eda3a1d00cfebcfa634efaa45` | RASTATE `ea40b5c0480841ae00089d40f66bb026a7ccb5e3a8d694ecfedae5fa4cbed4e0` | Lavos Tunnel `$01DA`; live `$2830-$287F` equals saved `$0430-$047F` |
| Native menu entry | `51624f4d369256b3b9bb37116e90a5b2d4f40ff8fa0437abc9693a66bf29d9e2` | RASTATE `a5cf7f8292f256361a7acd65bb3e8ede6e0218e5ee6316db4524ab6bc02ea05b` | Menu rendered; canary exact once; guards zero |
| Player-1 soft reset | `a0e19ad312cfd127945c81067e01eb748b3dfdf52064dfbc13dbb1250343e7f9` | RASTATE `f14efe2c151d649b4732824e1b5618ccb6916b2fbab1edb28fd8ecb0098dc76d` | Pendulum intro rendered; candidate cleared to all zero |
| Equipment entry | `c2647d4757677f4386a985e5fa50a413d53ce2f0882889235f7cbcd5b3cf774b` | RASTATE `c50e13750ca03d00a31874a0739cd41904d94525bf886d81b7d71b8067bfe9f9` | Crono Equipment rendered; canary exact once |
| Equipment character switch | `3488d4d15ae6d13b42dd2d3c92b375a350fe9065e64d8fbdb6fc1dbee0b9f682` | RASTATE `96371781539966c936b868a28ebef77f67af09eb166a1642cd8d854e9364734e` | Marle selected and rendered; canary exact once |
| Native party swap | `40347e1145e9047a6b7efe6e2fab92c9da7ecf37739340370584f9021c0a7601` | RASTATE `af7dc4eb412612298a22831b162a2deaf2f8550e921f33148c77678ec35ca373` | Crono/Frog roster swap; canary exact once; guards zero |
| North Cape decision checkpoint | `b3cf2dee018c7d2f150663bb9a88113b2254d6c12e49358253fe1a8f9c6ec7f5` | RASTATE `2bed44501a3ed2fabdc7788264520c7d5453a0300cf102cb3712207895737667` | Native fight/forgive choice; canary exact once; Epoch name intact |
| Native Magus fight entry | `65f617eac8a0f783c1a21ddf07a40779f515f837d6be46ec055f1f73e818c6c7` | RASTATE `3452ce75a5f2e39305044c210cd9643bba00322d26e810157fd46087dc844fda` | Visible Frog-versus-Magus battle menu; canary exact once |
| Native Magus battle idle, 600 frames | `9d995f2a346eef5ed42b2c53656dd63cad8fe5eee746b2b13bb665a2c292d131` | RASTATE `dd53b89b785ddd039bb3d2360cd97caf798f5f29f742bcec68a4ad7566890b78` | Remains in battle while enemy AI advances; canary, guards, Epoch name, and SRAM exact |
| Battle Y, frames 60-63 | `ad0be617aac218446bd39d30bfeaa971c4aa754689b9dc286cccdc5b23fb47ed` | RASTATE `3eb5cf3649009addf09da9cdad6e596a90792ba182df2becc5ca71d97d84e1da` | Moves the command/HUD window from bottom to top |
| Battle Start, frames 60-63 | `4c535f8e7dc08e59a56b87646749eba1018059173b305527c09ac5edb5f5dcc1` | RASTATE `a80a242e8ef437aba6a2a87bf03208372bdb17dc83e6fcbd74ee20a92d8c8c90` | Pauses and dims the battle |
| Battle Up, frames 60-63 | `4df2cfe595010d33e46ec5bcddd61c4b5339b0ad6ea6a44d7a7910ba759c3396` | RASTATE `d4a195b61b3b30572ce58ba45c93051b6e199c42726c3d09c303891e72cc46d2` | Wraps the command cursor from Att. to Item |
| Battle Down, frames 60-63 | `90065243510a80920c7c705e00f1d35e3da47aa9ee29327814fccc5ac08f647b` | RASTATE `6fee13742f034b5b378ca3609f9a14808b1ba69bd1888083e89932def6ac3965` | Moves the command cursor from Att. to Tech |
| Battle A, frames 60-63 | `60d5c10ccc0b14c2038216dcac5d80b5f94c99f284fbce660d8cb3098c4f8155` | RASTATE `6477d12e40fe01fedf92fbcc2cd391bc2f36b12e35749f82db8f4ab090a6a1b1` | Confirms Att.; Frog enters attack flow and Magus flashes |
| Battle Tech submenu | `d62df86f2915e9d1f09dab37f5895fbbe466f54e26032fa69ac7a07f1d3c4c7c` | RASTATE `20ba12597bf4644a90c1cbe44971c94cc600d0959de8149660284cf177fa6a6d` | Down then A opens Heal / Leap Slash / Water 2; no tech selected |
| Battle normal-attack resolution | `b82d9bc969544e5c4a07f005c456b395259187fedea6b7bd4cd7d92469d76cdd` | RASTATE `192eb14c9344e808ad3167caa3fb27af016272c824032011f5cbd27bb0740633` | Released second A confirms Magus; HP `6666->6137`; stable command menu returns |
| Magus name accept / party exchange | `b81a82287aface40bb59de34d0089900af2b5dfc77de053aee9d3153e58cfc74` | RASTATE `82335862d34aa8842e6cfc08562e3fee1cd1a0f0276fa48df2497685ba625542` | Magus already registered in reserve; native replacement UI rendered |
| Newly recruited Magus swap | `8e3f26b8af01b3cf0e1fc56df10f38ac1dfa4a6d745ceab23d04ba67e9cf7197` | RASTATE `083ebcad17fc2dd3ecf793b4562900e493f344c294bacd8b798c3d5b288a3498` | Active `06 01 03`; Frog moved to reserve; canary, guards, and Epoch name exact |
| Lavos Tunnel to Lavos Core | `7818e503fb3f2daaedf70f6f87ec53858c161e0fdefbbb90ae48e82ba2116469` | RASTATE `7ebcdfe21984a554092f83371c8db827939b616dfbdf7392252f3724cca87034` | Normal walk changes location `$01DA->$01DB`; canary, guards, Epoch name, and SRAM exact |
| Native Lavos battle entry | `18d865e292ec3e80e3d48bdbae718a41a0b1aea8ff4d37645247a0800937b59c` | RASTATE `83389bf16eca00dcce9e4cb8422a9eea1213912279bc58e46fdaaf665a3a0a4c` | Visible native Lavos command menu; pending battle request `$01`; all protected bytes exact |

The native menu screenshot SHA-256 is
`5d1e340c163cc92b676314c1f4d4a9a6fc188ad420dbf3d5322228b9a809e8bc`.
The reset screenshot SHA-256 is
`246a6fad55b72a3c70e1081edad6ce7f7d1f65b6ea19217c6cfeea1d1f3615fd`.
The Crono Equipment screenshot SHA-256 is
`fc8a8c549e629ca7d7c5ed9cf1c62d1ab6cfbbbe8041383924515cbbddb8ea9a`;
the Marle-selection screenshot SHA-256 is
`be55f935888892e26e4f3863065eb827c562ed525f30fab1d1f86c41babe5bc2`.

Across the North Cape recruitment reference, the pre-decision active/roster
state `04 01 03 / 04 01 03 83 81 84 02 05 80` becomes
`04 01 03 / 04 01 03 06 81 84 02 05 80` before name acceptance. The joined
mask changes from `$FC` to `$FE`. Native party exchange then produces
`06 01 03 / 06 01 03 04 81 84 02 05 80`. Live Epoch name bytes remain
`a4 c9 c8 bc c1 00` at `$7E2C4D-$7E2C52` throughout.

### Twelve-button battle calibration

All twelve Player-1 joypad IDs were independently held for four frames
(`60-63`) from the accepted Frog-versus-Magus battle checkpoint. Each movie
differs from the zero-input checkpoint in exactly four signed value bytes.
Every run used an isolated same-stem clean ROM/SRAM pair and exited normally.

Five controls have a meaningful effect at this top-level menu/timing:

| Control | Raw `MEM ` SHA-256 | Screenshot SHA-256 | Observed result |
| --- | --- | --- | --- |
| Y | `9d4fcfedcada009d5d099d6900c7f8a4252c47cfecf6f780698302333634804e` | `9fd16f7166e33e8acf3d1d699a44743c9ccb8a466f5425905f300d0129ceafa4` | command/HUD window moves to the top |
| Start | `3457fa59c9f7ff5c67bedab06063125a780724a89713f359dc3215c85e594c9f` | `6046bff2b19877a6a39f88c29cb5c6017fd908a164220adf0614fb4c05b13902` | battle pauses and dims |
| Up | `d859ccaba40f3443cc712ce52c07d09d2ac4de25d1e35b98e886ecfbacafcc0d` | `464912b544773d089f5ddba7d7540ec48a8cbe7b89a166b726a3c2151d6cd0b2` | cursor wraps from Att. to Item |
| Down | `0e205423e1d6e1d34c75b330674cab87df67a382d918b298d4b228a4e244e411` | `bb41aee44a8fd23b03e62e1021684e0e45edbd817edf8134c331f8467b9e6b99` | cursor moves from Att. to Tech |
| A | `66ef430121d76ebf714827c2169254aafc72da46de79094da7a77c2357676a7d` | `5156d39a63ce1341e9a695561ad472dbb41704460d38df864fabfa368dc3b02e` | Att. is confirmed; Frog enters attack flow |

B, Select, Left, Right, X, L, and R are inert only in this bounded
top-level context: their extracted core states and screenshots are exactly the
zero-input control (`3823c13e16b7e9b1742246c59c2adc603180cc994acba97ff81703ba8e10736c`
and
`e9a35a682c603c0d248835754bd1ec15b0bddcde5dd1b3cfdb05c37d7a4dfba3`).
That does not classify them as globally inert; submenu, target-selection,
animation, and other timing contexts remain untested.

Across all twelve runs, the relocation canary remains exact once at raw state
offset `$4F24`, both guards are zero, Epoch remains
`a4 c9 c8 bc c1 00`, the clean ROM remains
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`,
and every source/disposable SRAM remains
`a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9`.
Only the five meaningful calibration runs and the separate Tech-open route
are promoted to the accepted artifact set.

### Tech-menu entry, Heal cast, and normal-attack resolution

The accepted Tech route adds Down at frames `60-63` and A at `64-67`.
Its movie differs from the zero-input checkpoint at exactly eight signed
input-value bytes. The exit screenshot hashes to
`d82d87ba73181852e59bc0c6648392cf76b4e026b3e67b62c621fa5a9e66f033`
and visibly shows Frog's native list with the cursor on Heal plus Leap Slash
and Water 2. No tech is selected or cast. The raw `MEM ` state hashes to
`76b40d8b546a802d6ccdb38e2724eed4b75f77ada727c4352eb924b5d98ecb5c`.

A bounded extension selects Heal with A at frames `620-623`, releases for four
frames, then confirms Frog at `628-631`. At frame 1,500, the matched Tech-open
control retains `837/999` HP and `99/99` MP with the Tech list still open. The
cast route has `999/999` HP, `97/99` MP, leaves Magus at `6666/6666`, and is
back at the stable top-level command menu. This proves one native Heal
selection, self-target confirmation, 2-MP charge, effect, and command return;
it does not generalize to offensive, multi-target, or Schala techs.

The Heal movie hashes to
`663e050eec4a26d1041f7444e1954e8202d1ef06766e9609338c33cfee8b4c25`;
its RASTATE, raw `MEM ` state, and screenshot hash respectively to
`9e6218033a97159056bf7e2988efd7e1704bbd4f67f9e290f9105283be799638`,
`ba99417da27edaaca2f22378d939e0320309a92ed7e0ba7e272ceae75f638079`,
and `9153d5117604478a5f6d7493e754f7e0c5116e5491f5abb729ae8642d6644774`.
The matched no-cast RASTATE and raw state hash to
`304c49a0f387dd9fd47b572ad408d79adc4c8341b57f7123b972281329f203b0`
and `5bdb5604eac66c1bc2ee3b88b9ed2c76bcaeb5d9ce1c99fbb24ee393c1370336`.

A matched 1,200-frame A-only follow-up remains a useful negative: Magus's
current/max HP at `$7E5FB0/$7E5FB2` stays `6666/6666`, proving the first A
stops at target choice. A second A after four released frames completes the
flow. At the matched 1,500-frame endpoint, the zero-input control remains
`6666/6666`, while the two-A route is `6137/6666`, a 529-damage normal
attack, and the command menu is stable again. The accepted two-A screenshot
hashes to
`92aea1e305b24a2b6f8a0f9516dd90d4bbe4da0346060706094eac4af1ae8c0c`;
its raw `MEM ` state hashes to
`3228456cca3bdf0e78f7ce4c1d552e2964d449dba1fdecf2b9700ee7c190aad4`.

Second-press timings at frames 68, 76, 92, and 120 all reach the same
`6137/6666` HP result. Only the shortest route plus its matched 1,500-frame
control are promoted; the three redundant timing probes remain exploratory.
Every result preserves the canary, guards, PC `$07`-candidate record bytes,
Epoch name, clean ROM, and isolated SRAM.

### Native slot-1 save and fresh-process reload

The save replay presses A at frames `60-61`, `700-701`, and `1100-1101`.
It overwrites only the disposable slot 1 and visibly reaches Save #63. The
disposable SRAM changes from
`cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203`
to
`25b0e42a278f883be24d0251bf22955773aa92cd1e675c55c534761968f4e6ae`.
Slot 1 remains valid with checksum `$FAF7`; slots 2 and 3 remain exact.
The complete byte diff is:

```text
059C: 3E -> 3F
05AD: D2 -> 31
05E3: 03 -> 06
05E4: 10 -> 2E
05FF: 07 -> 0B
0600: 3A -> 3C
0601: 00 -> 03
1FF0: D6 -> F7
1FF1: 91 -> FA
```

A separately recorded cold-boot replay was edited only to press Left at
frames `1800-1801` and A at `1950-1959`. Playback in a fresh process with
`load-nosave` reaches Lavos Tunnel `$01DA`, active party `00 01 02`,
storyline `$D6`, and live save counter 63. The loaded live
`$7E2830-$7E287F` is byte-identical to slot-1 `$0430-$047F`; both hash to
`b70a2e5d291811c9f58689d7d0dbbfe89b913a3c0b1ef846de4607f0af6d9c73`.
Epoch remains `a4c9c8bcc100`, both relocation guards are zero, and the reload
does not modify the disposable SRAM.

At save time, the injected `$7E2CA0-$7E2CEF` canary is exact. After the
fresh vanilla reload, that candidate block is all zero with SHA-256
`5b6fb58e61fa475939767d68a446f97f1bff02c0e5935a3ea8bb51e6515783d8`.
This is the required negative result: vanilla does not serialize the proposed
relocation block. It proves the native slot path and its preservation
boundary, not a Project Epoch sidecar hook.

### Vanilla valid-sidecar compatibility control

A separate deterministic full SRAM image combines the native Save #63 slot
with one structurally valid v1 slot-1 sidecar. The complete image hashes to
`668aed39e84b63bc5cd1a1d3d146623681e0a0b1e412bf99bf8427826aad3685`;
the `$A0` sidecar hashes to
`1e7e9fc1179bee9f04614e0eb1ccf60a65b6101dee4b9775d8db59fc5a193ce9`
and classifies `valid`, bound to `$FAF7`. Slots 2 and 3 sidecars remain all
`$FF`.

The corrected zero-input recording hashes to
`cc437bc567da39e0719241f68dfbb698517074f44402e56577aa9bb9fa204557`.
Direct initial-state reconstruction finds the exact complete SRAM once at
current-core offset `$022E` and the exact sidecar once at `$202E`. The
reconstructed 290,423-byte `BST1` state hashes to
`c071077cc7861476c2371d4383a30f2a290a63313e0e286a14b97441546b8374`.
The decoder follows the tagged RetroArch 1.22.2 statestream grammar in
[`bsvmovie.c`](https://github.com/libretro/RetroArch/blob/v1.22.2/input/bsv/bsvmovie.c),
with block/superblock sizes from
[`task_movie.c`](https://github.com/libretro/RetroArch/blob/v1.22.2/tasks/task_movie.c)
and zero-object index semantics from
[`uint32s_index.c`](https://github.com/libretro/RetroArch/blob/v1.22.2/input/bsv/uint32s_index.c).
Independent replay/RASTATE inspection reaches the same SRAM result. An earlier
`fa26a04a...` movie embedded baseline SRAM after a concurrent exploratory run
replaced its fixture; it is explicitly rejected and absent from the acceptance
list.

A 3,599-frame playback of the corrected movie produces RASTATE
`670b1f4ba2299e1e8a94c59afdd518ba04c07847c4e323b7d5d0d65189637d76`
and raw current-core state
`5a7af0d00f8803323e4fa6dac1051185cf16c3ec52e06c12f7c752c4f3c41867`.
The exit state still contains that exact full SRAM once at `$022E` and the
valid sidecar once at `$202E`; the same-stem disk SRAM retains its exact
pre-run hash.

The slot-load derivative changes only 12 intended input values: Left at frames
`1800-1801` and A at `1950-1959`. Its movie hashes to
`433a534cf76ffe3e7a8eee7617f89227754a5daeb9d7fd25550a2f2bba175ed6`.
Fresh-process playback reaches Lavos Tunnel `$01DA`, storyline `$D6`, Save
#63, and party `00 01 02`. Exit RASTATE
`356949e724481d7fd86d90e1da48c633a3b881d269d3a0177ed1fc311dd676fc`
contains the exact full SRAM and sidecar once at the same offsets. Live
`$7E2830-$287F` equals saved slot-1 `$0430-$047F` at
`b70a2e5d291811c9f58689d7d0dbbfe89b913a3c0b1ef846de4607f0af6d9c73`;
Epoch remains `a4c9c8bcc100`, and `$7E2CA0-$2CEF` remains all zero. The
pre/post disk SRAM hashes are identical.

Accepted supporting log hashes are:

- corrected zero-input record:
  `aeebc6303b9fbdd00a837d8ba6c1d19323fff76e3afed574bba376f15e626916`;
- 3,599-frame playback:
  `fc00ee3c0425552865f41c22f7f53d6ecb358454095163f169ded629d511cbc8`;
- slot-load playback:
  `0185f492a6da43d83c10225976a917a909b8db2a17393d6b5ea9b69390f80590`.

This is `verified-runtime` compatibility and cold-load preservation evidence
for the vanilla ROM under current bsnes. It does not install a sidecar hook,
declare the gap production-safe, prove collision-resistant slot provenance,
or cover Project Epoch save, New Game+, erase, or slots 2 and 3.

### Recovered final-battle save proof

`tools/inspect_ct_srm.py` validates all three slots in the recovered
`cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203`
SRAM. Slot 1 is location `$01DA`, storyline `$D6`, active party
`00 01 02`, roster `00 01 02 82 80 04 03 06 05`. Its loaded checkpoint is
at the Lavos Tunnel save point.

The accepted route starts from the canary checkpoint and uses:

```text
60:Up:192
260:Left:48
316:Up:432
756:Left:32
796:Up:320
1124:Right:16
1150:Up:64
```

The resulting state changes location to `$01DB` and visibly places the party
in Lavos Core. Its screenshot SHA-256 is
`a08a158fdc398948aee5b0fb033bf66b167f48efd4d81539ca34ef0193cad098`.
A first bounded three-Confirm stage reaches Lucca's final dialogue
(`b0e8609f46caa490d2508e8eac457996a7a7e34a1d0c68ccd5c46aabafd6b04e`
input,
`7d9855644e85acf5e6979549d10d63394eff5e5112324afc814dfc04ba17a5a6`
RASTATE). A second three-Confirm stage reaches the native Lavos battle;
the visible battle screenshot hashes to
`bf37869aa5fa38c778cfe6e876d476a72b52b6f2d875f537a7260ed7e9b459da`.

The complete clean ROM remains
`06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9`.
The source and all same-stem disposable SRAMs remain
`cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203`.
The exact relocation canary, both zero guards, joined mask `$FE`, and Epoch
name bytes remain unchanged through location transition, dialogue, and battle
entry.

### Current-core inert ExHiROM parity

The clean inert scaffold has SHA-256
`26bd7d0ff22927b167685ca741d0c84ae3dc683cd6c788c5ecd95723c2c2ab93`
and CRC32 `100CA949`. The rebind helper changed only BSV2 header bytes
`$08-$0B`; the raw initial core state and every replay frame remain exact.

| Check | 4 MiB core-state SHA-256 | 8 MiB core-state SHA-256 | Screenshot SHA-256 |
| --- | --- | --- | --- |
| Field idle, 600 frames | `669239cc2e8dbec7ecd236449073709f9d8e6b4a3da7dfbe937c5da382c3c1d0` | same | `bdda05df239a6cefb712409bd5ec07fcb83b1f2239ccfaabaa07ca5a9ae511d3` |
| Native main menu | `96a42b146e63abaa698318e1173f44c995aa76e0886ee3f84d029e028d6d3012` | same | `5d1e340c163cc92b676314c1f4d4a9a6fc188ad420dbf3d5322228b9a809e8bc` |
| Equipment, Marle selected | `462cdf2faac7359a3e7f1993be5d21a7d024526c51c864810c215e0601d42b3c` | same | `be55f935888892e26e4f3863065eb827c562ed525f30fab1d1f86c41babe5bc2` |
| Field idle, full 3,599 frames | `cfc1faaa60ef4b76129f70e29a74668fed15533e2e1ae4acc9c4c3cf099ca22b` | same | `4f283cfd6a1364b3b7cc38929543afffab6df3afbf35ba01e9dcccb33be32eef` |

The full-run RASTATE container hashes differ because each includes a replay
chunk with the mapping-specific content CRC. Their extracted `MEM ` core
states are byte-for-byte identical. The canary remains exact once and both
guards remain zero in every output.

The matched inert-ExHiROM controls cover field idle, menu entry/idle,
Equipment entry and character selection, and the vanilla soft-reset effect.
The wider clean-ROM current-core suite additionally covers native seven-PC
party exchange, ordinary North Cape battle entry, and full-party Magus
recruitment, the bounded top-level battle controls, Tech-menu entry, and
one complete native Heal cycle and normal-attack target/damage cycle, plus the
recovered final save through native Lavos battle entry and one isolated native
slot-1 save/fresh reload. The clean-ROM compatibility tranche below adds every
top-level main-menu page, one Tech owner switch, one equipment mutation with
derived-stat recomputation, and one complete Item/list/target/consumption
cycle. The Guardia Forest tranche below additionally covers one natural
victory and field return, and the Cyclone tranche covers one offensive
two-target Tech. The combined suite does not cover shop paths, the remaining
Tech target/effect classes, death/status/criticals, multi-PC victory
presentation, an eighth identity, Project Epoch sidecar mutation or
hook-driven live publication, the other two save slots, New Game+, attract
mode, erase, or Project Epoch's future reset initializer. A valid v1 sidecar
now has a vanilla boot/slot-1 cold-load preservation control only.

### Menu, equipment-mutation, and battle-Item tranche

`verified-runtime` for bounded vanilla paths; PC `$07` remains absent

From the canary-backed field checkpoint, Player-1 X opens the native main
menu. Four-frame Right pulses at frames 120, 160, 200, 240, 280, and 320
produce Item, Tech, Config, Party, Save, and Equip respectively. All six pages
render visibly. Their extracted core-state SHA-256 values are:

```text
Item    f7598b7ad9ee771c26d1abf84b303e9962957ef7206d217cb6d1ef39dfda0dca
Tech    9359a5a733f01674654f6d5157ef3c97555e2e3d0a0e636193ff824550380026
Config  ce43d7d75d513992833e27fc426be350b4c308372ccea5047df0bc924be912ec
Party   124af09e3cc5b8c7f0673e40ae8e16013616417a1730bfd883da770ae9a9fed1
Save    514860bb40fb560974cc3d60a9e086598abd9264c8760e382a00121bca1c6613
Equip   1c2891f36b775081682c2d7d2c92c8e5cc55ab03d2d7a8d000338dacc03cde48
```

The Tech route confirms the page and applies one Player-1 Down pulse. Marle's
single-tech list renders, and the extracted core state hashes to
`afacd3778eee18a0553e71cb47151a15601c6115740d7d4dbfec85954f154e2c`.

The Equipment route opens Crono's weapon selector, then confirms the
highlighted Kali Blade. The before/after extracted core states hash to:

- selector open:
  `f47754cbd7614434c10f0bb243ac0fbef9fe5ab23acc7606d34af0dbe1ff478d`;
- Kali Blade equipped:
  `160f542cb946ee35cd357a67cbdc153f62b037d7089599df3faadd79a2d7d5c0`.

The inspector reports Crono's equipment bytes changing only from
`8f6b559f` to `8f6b0d9f` and current Attack from `$EC` to `$C6`. The state
screen shows Kali Blade equipped and Rainbow returned to inventory. The
disposable SRAM remains
`cc5fa36da8185128e510c63f637842c77cf09dde413a196c3ab770656abff203`.

From the native Frog-versus-Magus command checkpoint, Up at frame 60 wraps
Attack to Item and A at frame 64 opens the list. A at frame 620 selects
MegaElixir; the no-use control stops there, while the use route adds a
released A at frame 628 to confirm Frog. At frame 1,500, battle-inventory row
8 is:

```text
control  c5 81 02 21 00
use      c5 81 02 20 00
```

Only the quantity changes, from 33 to 32; the other populated battle-item rows
remain exact. Both runs return to stable battle states, and the use route
visibly returns to the command menu. Their extracted core-state SHA-256 values
are
`52abd534b64e65334599d061ebe99f7a6c59303a675b660154b9ec2d0902130f`
and
`86653ad80befd6ac44a77f45392df4ac7f9862da0b39fce20d3f03a1d702ffac`.
The disposable SRAM remains
`a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9`.

All thirteen terminal states pass
`tools/inspect_current_wram_candidate.py --require-canary`: the canary occurs
exactly once, its four-byte front guard and sixteen-byte rear guard are zero,
and the matching disposable SRAM is byte-exact. The inspector now reports all
seven live field equipment rows, nonzero field inventory slots, and nonzero
five-byte battle-inventory rows, plus all twelve `$80`-byte battle combatant
records so these claims are source-reproducible rather than screenshot-only.

### Guardia Forest encounter, victory, and field return

`verified-runtime` for one natural vanilla battle lifecycle; structural only,
not a level or balance fixture

The high-level Crono-only slot in the isolated SRAM starts on the 1000 A.D.
overworld. The accepted route enters Guardia Forest (location `$0013`) and
chains four movement checkpoints:

```text
Overworld -> forest:
  Left 60:120, Down 200:180, Left 400:240, Up 680:300,
  Left 1020:300, Up 1340:400, Right 1780:160,
  Left 1980:16, Up 2020:64, A 2120:4
Forest entrance:
  Up 60:600
First bend:
  Right 60:400
East bend:
  Down 60:600
```

Each `start:duration` pair is local to its own checkpoint movie. The entry
movie SHA-256 is
`58931a257013294f488762880eabe7d736875f8d77afdcb94b74cb25588ce50d`;
the subsequent movement movies hash to
`b13f6ebec6daf0986be4b1b935aed9a2b1f25fabe01a832204d2795f3162ed42`,
`64b9602ee3204e990b8c4bda8fe347c8634471dccf12144d78caa6f13864f002`,
and
`3576ff35e21155c3bf0c5d7565943513a1e0d5f868f44775372f8224d4fa0ceb`.

At the Roly approach checkpoint, two otherwise identical movies establish the
encounter boundary:

- Right at frame 60 for 139 frames:
  `b523a6a4a20e82fbd3ea7c5d07e4e4e2254bd0562aed950e93e30d09ecf18d83`,
  field/explore remains `1`, pending request remains `0`;
- Right at frame 60 for 140 frames:
  `e1052485dfe1d5d13481f970d8480b4ea2451e7ee2ead75529371c20e93c1f6c`,
  field/explore becomes `0`, pending request becomes `1`, and the visible
  three-Roly command menu is ready.

The combatant-record inspector reports Crono in slot 0 at `996/999` HP and
enemy slots 3, 4, and 5 with identity `$5E`, each at `14/14` HP.

The command-ready battle checkpoint hashes to
`6681a81b7a44942ac838b167e7222e47929402004d06eb9e390071602f7f0a79`.
The accepted victory movie hashes to
`33d2ba256d929667081d3a3197762d283a1f00160e43e713bf02bf61dfd3626a`
and contains six four-frame A pulses:

```text
Attack/target 1  60, 68
Attack/target 2  620, 628
Attack/target 3  1180, 1188
```

At replay frame 1,800 the screen visibly reports `Found 480G`. At frame 2,600
the party is back in free field movement in location `$0013`; field/explore
is `1` and pending request is `0`. The final RASTATE container SHA-256 is
`efcfd98405f247d158dbbd248e287a4e1a570f62d9d4d52dd2cf7132886b9918`;
its extracted core SHA-256 is
`3f63df9b8d30a0b3d09cc95761a683e9627c869ae74aa8d14e3638c6025a3f5c`.

Independent inspection of the entrance, three movement endpoints, 139/140
boundary pair, reward state, and field-return state finds the relocation
canary exactly once with both zero guards. All eight states preserve
`$0430-$047F` against live `$7E2830-$287F`; every same-stem disposable SRAM
hashes to
`a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9`.

This closes one natural encounter, ordinary attacks, victory reward, battle
teardown, and field return for the compatibility candidate. It does not prove
death/status paths, criticals, multi-PC victory presentation, PC `$07`, or
translated battle-record commit behavior.

### Native Cyclone multi-target cycle

`verified-runtime` for one offensive two-target Tech; no PC `$07` or Project
Epoch command adapter

The three-Roly battle checkpoint starts with enemy slots 3, 4, and 5 at
`[14,14,14]` HP and Crono at 99 MP. The accepted cumulative inputs are:

```text
Down 60:4     select Tech
A 68:4        open the list
A 140:4       select Cyclone
Down 220:4    select the lower Roly cluster
A 300:4       cast
```

The command, list, target, and cast BSV SHA-256 values are:

```text
command  6681a81b7a44942ac838b167e7222e47929402004d06eb9e390071602f7f0a79
list     b332d8c677a858c988427e64493f553051ba5bcc0565422a4fdded80edf4bfd8
target   3dad0f14f247af48bb73883e399d32072f19380b5a6549b7b3802c1cd3218cb0
cast     e951593682c9606ae9e03aeeaa18771212c1200020c3b65700de731631b642fb
```

The matched control is the exact target movie replayed to frame 1,800 without
the final A. It retains enemy HP `[14,14,14]` and Crono MP 99. The cast effect
visibly displays simultaneous `357` and `364` damage values; at frame 1,800,
enemy HP is `[0,14,0]`, Crono MP is 97, only the upper-right Roly remains, and
the command menu has returned. The extracted control/resolution core-state
SHA-256 values are:

```text
control     118aa3337bcb10101cc8f507502129089fb646f8b5d5e1c5f91b9512fb4ffd2e
resolution  954507019a46e157e39b7dcbd0087dfd1efd7df7c98e8357e5ccd285fd0649a7
```

All six command/list/target/effect/control/resolution endpoints pass the exact
canary and zero-guard checks. Live `$7E2830-$287F` matches saved
`$0430-$047F` at SHA-256
`6007023eefa73f3f9c70da546f921dce866d3131e8c98ba978785f7ac28f82c1`;
the disposable SRAM remains
`a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9`.

This proves one vanilla offensive multi-target selection/effect/MP cycle and
rules out passive resolution with a matched control. It does not generalize
to every target geometry, damage/effect type, PC `$07`, or Schala's proposed
high-ID command overlay.

### Spekkio event `$11C` controlled magic-grant baseline

`verified-runtime` for two prepared vanilla event branches; no translated
packet or PC `$07`

No checksum-valid natural pre-grant save was available locally. The accepted
route therefore starts from a late-game, talkable location-`$1D1` checkpoint
and uses `tools/inject_spekkio_event11c_diagnostic.py` to prepare only the
bounded volatile state required by the canonical call: storyline `$4C`, lap
scratch `$7F021C=03`, selected grant bits, and the corresponding compatibility
tech fields. It writes neither ROM nor SRAM and requires the candidate plus
both guards to be zero before preparation.

The preparation chain is pinned by these private BSV2 hashes:

| Artifact | SHA-256 |
| --- | --- |
| talkable zero checkpoint | `50c3bd069faf295790ab5509f0dc19cf0c9c288006afb2d6c909ad9e32e29aa8` |
| Magus/Robo/Frog prepared zero | `fc1aed1644dd00f1a076c3355719525808f60e407e3f6c9221499a69aa30d1fe` |
| Magus/Robo/Frog prepared canary | `42d21c809251c0e3c3852d7e22290ea7b4adb9e32ff2400431c2c3c410fd5482` |
| Crono/Marle/Lucca prepared zero | `b95600aac19bf3ed40a5f0bdb735d609819ed1b0b3c396d68d0c081bf830edc5` |
| Crono/Marle/Lucca prepared canary | `993e141085a55184b3f8291f1a8bdbfbe75e7c6e277522bb72c8c61a7b6708f9` |

The first profile retains the source active party `06 04 03`
(Magus/Robo/Frog). The second synthetically supplies active party `00 01 02`
(Crono/Marle/Lucca); it is not a valid serialized roster. Both replays press A
at frames `60,180,300,420,540,660,780,900,1020,1140`. The
Crono/Marle/Lucca route needs one additional A at frame `1860` to close
Lucca's grant message. The accepted final BSV2 hashes are:

| Profile | Zero | Canary |
| --- | --- | --- |
| Magus/Robo/Frog, frame 1,800 | `76126d47b3e4d0de494402bb0f62312d5eaf669b9ccecfb10a8d118a621fc21a` | `d6bf68d99731d97a105fd2fd997aea532ea1f68b658392b9494244bab888822c` |
| Crono/Marle/Lucca, frame 2,100 | `3f86fbb69e7e46edd399e8b34931a1def3336b10181d49d89d1dabc11610d0c5` | `de3cae3dfc99904492f8763dceae1fd5522fee39abff67ea8146faf103c5d405` |

Both profiles reach storyline `$4D`, magic flags `$5F`, Robo flags `$00`,
and lap scratch `$03`. Their terminal compatibility fields match the static
event decode:

| Profile | Tech counts `$2830-$2836` | Learned masks `$2837-$283D` | Remaining TP |
| --- | --- | --- | --- |
| Magus/Robo/Frog | `08 08 08 08 03 08 08` | seven `$FF` bytes | Frog `160` |
| Crono/Marle/Lucca | `03 03 03 08 08 08 08` | seven `$FF` bytes | Crono/Marle/Lucca `160/150/160` |

The endpoint evidence is:

| Profile | Zero RASTATE / core SHA-256 | Canary RASTATE / core SHA-256 | Pair-identical screenshot SHA-256 |
| --- | --- | --- | --- |
| Magus/Robo/Frog | `ae4bb1438d3b58bd27812c93740e3ac151a1fea8bda8a311c299fc4c8d025f94` / `1a43f9e45af86b467eed388ff347c4dda245ec96bfd2238dd442b29c3347f671` | `ee4ff47b72368fb8c9baa17633bbd2235a64313cd37342d1216496c5cbf04d6c` / `6b32b0f68e8c399576318298f9f28754392a9d764ce90f359bb21444d8587a3a` | `1b10bbad8522be8476d2749da903525507ed4535a17ad9a0a862afd21280c067` |
| Crono/Marle/Lucca | `a9437d70e1521cf0eb008a0bb7ca43de7749f3c948c2b01f0f9c5341374143a0` / `dcc1fbab7f0f5bce3b285d3f3667260ff2259ac0832c9f17a671cfb9b288452d` | `05ca58e4629b861b69ada4d53e2819ca753772f5889126ab3e5ede50c880f38a` / `af2e66bcc9af5062abf314140df1a82a6eba44864a45a395d1839eaf2402779d` | `46cfa8d3dbe3668a56ed5a0290273877457619e0cf6b9e2747d19b277b729dbc` |

For both pairs, `tools/compare_current_wram_canary_pair.py` reports exactly
80 differences at state offsets `20260..20339`, corresponding exactly to
`$7E2CA0-$2CEF`. Normalizing only that span reproduces the zero core hash.
Both guards and the Epoch name remain exact. All four disposable SRAM files
remain byte-identical at SHA-256
`a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9`.
The Frog endpoint is still displaying `SPEKKIO: All right!`; the CML endpoint
is at Spekkio's post-grant practice prompt. Neither enters the practice
battle.

Reproduce the bounded state preparation and pair checks with:

```powershell
python tools\inject_spekkio_event11c_diagnostic.py `
  private\test_runs\retroarch\current\spekkio_talkable_checkpoint_v2_zero.bsv `
  --profile frog-robo `
  --expected-core-sha256 `
    55b147f4b8f8bc9d252862f13d003f47bb9adb616583d527b08e2955d672d264 `
  -o private\test_runs\retroarch\current\spekkio_event11c_frog_prepared_v2_zero.bsv

python tools\inject_bsv2_wram_canary.py `
  private\test_runs\retroarch\current\spekkio_event11c_frog_prepared_v2_zero.bsv `
  --srm <disposable-slot3.srm> --slot 3 `
  -o private\test_runs\retroarch\current\spekkio_event11c_frog_prepared_v2_canary.bsv

python tools\compare_current_wram_canary_pair.py `
  <zero.state.auto> <canary.state.auto> `
  --srm <matching-disposable-slot3.srm> --slot 3
```

Repeat the injector with profile `crono-marle-lucca`, add the documented A
pulses with `tools/edit_retroarch_bsv2_inputs.py`, then replay matched inputs
under the pinned current-bsnes harness. The accepted artifact spec below
captures only the successful preparation/final chain.

This closes the controlled **unmodified-event baseline**. It does not prove a
naturally reached first grant, a valid save/roster, every individual transient
read/write, candidate ownership, an installed translated event, or protection
of Schala's natural record. The installed test must instead allow only the
planned relocated compatibility-field writes and prove `$7E2830-$287F`
unchanged.

#### Native Mesen instruction-level cross-check

`verified-runtime` for the unmodified event handler; no translated packet,
production hook, ROM mutation, or SRAM mutation.

Mesen 2.1.1 is kept under `private/tools/mesen2/`. The executable is
70,470,144 bytes at SHA-256
`d2eb03c2590c648bf329f127ebcfefd70130e7690a9e2ccdba8616faea1fe96b`.
The retained official 34,058,170-byte release archive hashes to
`23ccc2bc060b663c68dad3a8c5d6da7d23a50f872d04f135bafa2b04ff7d5cbe`.
The runtime contract also pins `MesenCore.dll` at
`65f69a7bdb25c35fdca77c9c73e71ef3e8ec233380204d94cfc0179933048c74`,
`libHarfBuzzSharp.dll` at
`eb76238c9e8e41d44b5a5b18167c4c5b39ca5db4277af5dbe92d730f0fc14a7d`,
`libSkiaSharp.dll` at
`9a0d95e8caaa852c70d085af6a40a744242172ad9ea3fd6bc7599875a8a1dbcd`,
`MesenNesDB.txt` at
`cff835b8a3d5b07d9d111382da6c49ccae150cdbaa9a0e49e15aa381af471307`,
and the three-byte empty portable `settings.json` baseline at
`ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356`.
The version, headless command line, callback timing, savestate restriction,
and `emu.stop` behavior were checked against the official
[2.1.1 release](https://github.com/SourMesen/Mesen2/releases/tag/2.1.1),
[TestRunner source](https://github.com/SourMesen/Mesen2/blob/2.1.1/UI/Utilities/TestRunner.cs),
and [Lua API contract](https://github.com/SourMesen/Mesen2/blob/2.1.1/UI/Debugger/Documentation/LuaDocumentation.json).

`tools/mesen_spekkio_checkpoint.lua` starts from a disposable private slot-3
SRAM, selects Continue, navigates from the End of Time to Spekkio, and captures
a native Mesen state while the party is controllable and facing him at
location `$1D1`, coordinates `1568,2623`. Its private route log ends at
emulation frame 3236. The resulting state is 133,993 bytes, SHA-256
`26788b52f63a32a7539d8acb18495df1a458064f700d5411916e2bfc34c4522e`;
the state reports frame count 3237 and direct-page register `$0100`.

`tools/mesen_event11c_trace.lua` loads that state from a main-CPU execution
callback, prepares one bounded volatile profile, supplies the same A pulses as
the current-bsnes baseline, and records a compact JSON trace. Mesen's narrow
physical callbacks were not delivered reliably after native state load, so
collector version 2 retains one broad execution callback and immediately
routes only exact CPU PCs `$C0:6797` and `$C0:6822`. It returns no integer from
the callback, so it cannot replace an instruction's value. Reads are sampled
before `LDA [$CD]`; writes are sampled on the immediately following
instruction after `STA [$D0]`.

All four accepted runs return the intentional test-runner exit code 41:

| Profile | Variant | Callbacks | Result |
| --- | --- | ---: | --- |
| Magus/Robo/Frog | zero | 3 | success |
| Magus/Robo/Frog | canary | 3 | success |
| Crono/Marle/Lucca | zero | 9 | success |
| Crono/Marle/Lucca | canary | 9 | success |

Collapsing each matched zero/canary pair, the traces contain exactly the 12
statically predicted operations; the four files physically contain 24
callback records because each operation is repeated by both variants:
four `$03` writes to `$7E2830/$2831/$2832/$2834`, four `$1F` reads from
`$7E2837/$2838/$2839/$283B`, and four `$FF` writes back to those learned-mask
bytes. Every read uses PC `$C0:6797`; every write uses `$C0:6822`. Each
zero/canary pair has the same sequence, frames, PCs, targets, and values.
Endpoint candidate state, front/rear guards, Epoch name, story, flags, counts,
and masks all pass; paired endpoint PNGs are byte-identical. The Frog endpoint
PNG hashes to
`0882eb8e58d053a0e5b2222c9615ab5a1e4530d8849ddd7388e491803417b7fb`;
the Crono/Marle/Lucca endpoint hashes to
`312a56671d05c8f4a47ca0cbb65aa6dbefda0eb81068736d1dde5eb2aeea8e96`.
The disposable SRAM remains byte-exact at SHA-256
`a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9`.

Use the source-controlled host launcher for each case:

```powershell
python tools\run_mesen_event11c_trace.py `
  --profile frog-robo `
  --variant zero `
  --output-dir private\test_runs\mesen2\<fresh-run>\frog-robo\zero
```

Repeat into fresh directories for `frog-robo/canary`,
`crono-marle-lucca/zero`, and `crono-marle-lucca/canary`. The launcher
resolves every input/output against this workspace's exact non-junction
`private/` root, refuses output collisions, and verifies the pinned
collector, validator, official archive, runtime files, settings, ROM,
checkpoint, and source SRAM. It runs a temporary private copy of the emulator
with an isolated empty `Saves` directory and a uniquely named disposable
ROM/SRAM pair; it never executes against the shared Mesen app or shared saves.
It then requires the strict single-trace semantic contract and the exact
accepted JSON/PNG size and SHA-256 before reporting acceptance. All temporary
copyrighted bytes are removed with the private staging directory, and the
source inputs plus shared Saves tree are post-hash checked.

Finally run `tools/validate_mesen_event11c_trace.py` over the four JSON files
to prove the cross-variant set contract. A four-case launcher replay reproduced
all eight accepted artifact hashes exactly. The curated hash contract is
`references/mesen_event11c_trace_accepted_artifacts_v1.json`; its SHA-256 is
`7798c8100ce2dd1361e6d0ccb6fa6ba7ce40460aa95f18504d7d5df47944ec48`.
The local-only curated manifest hashes to
`a1132bf8e93b997cb79dc3e3aece9a135bdf67061298e115da0be32355f82b67`.
All ROMs, SRAMs, native states, screenshots, and traces remain private.

This closes the transient instruction-level **old-address baseline**. It does
not test a recompressed/installed event, prove `$2CA0-$2CEF` globally free, or
permit the natural PC `$07` record to replace vanilla compatibility state.

#### Native Mesen volatile relocated event `$11C`

`verified-runtime` for the exact already-decompressed WRAM packet only; no ROM
installation, PC `$07`, or persistence adapter

The accepted follow-up collector loads the same native checkpoint and receives
two raw packets derived ephemerally by the host launcher from the pinned
private ROM. It requires the complete source packet at live
`$7F2000-$7F2C6A` (`$0C6B` bytes), verifies the exact 12-site/24-byte
translation, changes those 24 bytes, and requires a complete
transformed-packet match immediately afterward and at termination. Every
explicit collector `write8`/`write16` call targets `snesWorkRam`. It copies all
`$50` bytes from `$7E2830-$287F` to `$7E2CA0-$2CEF` before preparing either
grant profile.

The initial calibration put a canary across the full old `$50`-byte block and
correctly caught normal rock-flag recalculation at `$2857-$285B`. The accepted
matrix therefore uses its zero/canary control only across event target span
`$2830-$283B`, leaving existing learned-mask and rock-flag tail data
untouched. The entire prepared old block must nevertheless remain exact after
the translated grant. Candidate changes are limited to the expected
`$2CA0/$2CA1/$2CA2/$2CA4` counts and
`$2CA7/$2CA8/$2CA9/$2CAB` masks. Candidate non-target bytes, front/rear guards,
and Epoch remain exact.

The exact-PC router now binds every callback to the transformed source
command. CPU Y must equal the corresponding decompressed event-data offset,
direct page must be `$0100`, and M must be set. The live opcode and operand at
`$7F2000 + Y` must equal the pointer resolved through `$CD/$D0`; for each
`STA [$D0]`, low A before the instruction must equal the deferred post-STA
memory byte. Both profiles preserve the old baseline's callback frames,
values, and order at the relocated addresses.

| Profile | Variant | Trace bytes | Trace SHA-256 | PNG bytes | PNG SHA-256 |
| --- | --- | ---: | --- | ---: | --- |
| Magus/Robo/Frog | zero | `5884` | `645f6f4c1ce5ffac18a3a3cb8caf8b5115303fa4a3a5f2b32a089f55e70306fe` | `9503` | `0882eb8e58d053a0e5b2222c9615ab5a1e4530d8849ddd7388e491803417b7fb` |
| Magus/Robo/Frog | canary | `5886` | `27d1330a474391220b47a4a154d06e1ee6d416771456e94110d2332c82d1e7fe` | `9503` | `0882eb8e58d053a0e5b2222c9615ab5a1e4530d8849ddd7388e491803417b7fb` |
| Crono/Marle/Lucca | zero | `7715` | `70006be6c842a940de366a9102c7ee80db1f8829f9078d3bf5369368a69f090b` | `10421` | `312a56671d05c8f4a47ca0cbb65aa6dbefda0eb81068736d1dde5eb2aeea8e96` |
| Crono/Marle/Lucca | canary | `7717` | `579fa7aaace23cbb1fdd1b0a040a00073552eafef2f8337ce4a616b3d644f595` | `10421` | `312a56671d05c8f4a47ca0cbb65aa6dbefda0eb81068736d1dde5eb2aeea8e96` |

The exact PNG gate pins the field frame to zero modulo 16 and Spekkio's sprite
frame to 22 for Magus/Robo/Frog or 4 for Crono/Marle/Lucca. Those conditions
remove the adjacent idle-frame nondeterminism exposed by the exact-image gate.

The strict four-set validator requires one identical source compatibility
block across all cases, identical candidate endpoints and callback sequences
for each zero/canary pair, the exact packet/edit contract, and successful
terminal preservation. The current curated private root is
`private/test_runs/mesen2/event11c_relocated_accepted_hardened_v4`. A separate
pass through the final guarded launcher reproduced all eight artifact hashes
under
`private/test_runs/mesen2/event11c_relocated_launcher_replay_hardened_v4`.
Acceptance v1 and v2 and their accepted/replay roots remain retained as
historical evidence rather than the current acceptance set. V2 mislabeled the
incompatible hardened shape as trace-v1/collector version 1. The current
validator requires trace schema v2 and collector version 2 because the shape
removed synthesized `absolute_frame`, added phase fields, and narrowed the
explicit-write scope. Both current four-trace sets pass that validator and are
byte-identical across all eight JSON/PNG artifacts.

The launcher retains the accepted runner's canonical-path and isolated-runtime
safety behavior. It validates immutable inputs first, exact-byte compiles and
executes the pinned Python modules, and reads plus hashes the legacy launcher
source only for provenance; legacy source is never executed. It derives source
and transformed packets inside a private temporary staging tree, stages the
verified collector and checkpoint, and runs a fully staged Mesen app with a
uniquely named disposable ROM/SRAM pair. Collector outputs remain staged until
strict semantic and exact artifact-hash acceptance, after which the trace/PNG
pair is published with exclusive `xb` creation. A failed pair publication may
roll back only a file whose identity still matches the just-created output.
Source ROM, checkpoint, SRAM, staged inputs, and the shared Mesen `Saves` tree
remain byte-exact. Raw packet files and the complete staging tree are deleted
before success is reported.

This write-scope claim covers only explicit collector `write8`/`write16` calls.
`loadSavestate` and subsequent game execution may change other transient
emulator state; the host proof is that the pinned source files and shared
`Saves` tree remain unchanged.

Use a fresh output directory for each case:

```powershell
python tools\run_mesen_event11c_relocated_trace.py `
  --profile frog-robo `
  --variant zero `
  --output-dir private\test_runs\mesen2\<fresh-run>\frog-robo\zero
```

Repeat for `frog-robo/canary`, `crono-marle-lucca/zero`, and
`crono-marle-lucca/canary`, then validate the four private JSON files:

```powershell
python tools\validate_mesen_event11c_relocated_trace.py `
  private\test_runs\mesen2\event11c_relocated_accepted_hardened_v4\crono-marle-lucca\zero\trace.json `
  private\test_runs\mesen2\event11c_relocated_accepted_hardened_v4\crono-marle-lucca\canary\trace.json `
  private\test_runs\mesen2\event11c_relocated_accepted_hardened_v4\frog-robo\zero\trace.json `
  private\test_runs\mesen2\event11c_relocated_accepted_hardened_v4\frog-robo\canary\trace.json
```

The current 8,934-byte source-controlled acceptance spec is
`references/mesen_event11c_relocated_trace_accepted_artifacts_v3.json`,
SHA-256
`839b86310dbe33273cf14ffec01386aa4ee6b88426b100be2cdc65d17a0790cc`.
This closes the volatile already-decompressed event-consumer gate only. It
does not prove recompression, named ROM allocation, event-pointer
installation, a production hook, global ownership of `$2CA0-$2CEF`, natural
PC `$07`, or save/load/erase/reset/New Game+ integration.

## Attract/demo lifecycle replay

`verified-runtime`

A 29,999-frame zero-input BSV2 recording, SHA-256
`b5b0269eb7ccbf4d18f3b25963034878e9a4dc5d3fe63292063ba06107ad50f2`,
was rebound to the raw current-bsnes title state captured at cold-boot frame
1,800. The resulting zero carrier has SHA-256
`5048166d7c858c70a5e8dd70d70fd18f64993bc82b50a8d6bdc3651d44c10b92`.
The pinned-layout canary injector changes only state offset
`$4F24-$4F73` and deterministically emits the paired carrier at SHA-256
`d17ff3db044713c94acddb017243f3efcbc20b758bcf194513c36f6b20fc7321`.
The replay frames remain byte-identical.

The autonomous replay crosses title timeout, attract initialization, Flea
battle, a Zeal field scene, Zombor battle, and return to the stable title logo
at frame 10,800. Every accepted canary endpoint has one exact candidate
canary, zero guards, unchanged disposable SRAM, and unchanged external
slot-1 `$0430-$047F`. Natural PC `$07` remains zero through frame 2,130 and
changes at frame 2,131, while `$2CA0-$2CEF` remains exact. This is direct
runtime confirmation of the statically reconstructed eight-destination
attract overwrite.

Matched zero/canary checkpoints at frames 431, 4,800, and 10,800 each differ
at exactly the 80 offsets `20260..20339`. The fail-closed pair comparator
normalizes only that span and produces the zero-core hash exactly. The
zero/canary screenshots are byte-identical at all three checkpoints, with
PNG SHA-256:

```text
frame 431    0ed7b26b91b35f00cac8a9909698a5aeec7f2b425d7f4726a7fb21d0427b3bf4
frame 4800   b110e03ffed45b74f3e5be0e37d226c60f86352002c093dfdf43b702450152a7
frame 10800  765e763b6d12fcf0894969ebf373104f67cedf81fdd599ff2d116b1197bb0260
```

The unmodified vanilla route therefore leaves the relocation candidate
untouched but does overwrite natural PC `$07`. It does not install the
Project Epoch attract initializer, initialize relocated compatibility data or
Schala, approve the candidate allocation, or prove a general menu path.

## New Game+ partial-loader replay

`verified-runtime`

The local-only 8,192-byte unlocked SRAM used for this control has SHA-256
`ba2b0a32d8f827f572e08bff381a693ccb192bac45141ed9521421d2a2410ac5`,
global New Game+ flag `$1FE2 = FF`, and two checksum/magic-valid slots. From
cold boot, the accepted input path is Start at frames 1,500-1,503, Up at
1,700-1,701, Up at 1,720-1,721, Right at 1,740-1,741, and A at
1,760-1,761. The resulting frame-2,000 checkpoint visibly shows
`Start using which data?` with slot 1 selected.

That checkpoint was rebound into matched zero and exact-canary BSV2 carriers.
A at replay frames 60-61 confirms slot 1. Between frames 61 and 62, the native
partial loader changes `$7E2830-$287F` from SHA-256
`ca33129e383fea5c0ad8e176d7847f5118ccbbf77ea1098da9ec1f24c0451123`
to
`714d4e95e48bc696bdd1ba7d12471fe1487b8c2df50e1e38385d48b28a36e3f3`.
The latter is byte-exact to selected slot 1 `+$0430-$047F`. At the same
boundary the Epoch name changes from zero to `a4c9c8bcc100`, while roster
bytes remain nine `$80` values and joined remains `$80`. By frame 90 the
roster is `008080808080808080`; by frame 300 the native Battle Mode
Active/Wait prompt is visible.

The relocation candidate contains one exact canary throughout and both guards
remain zero. Every matched zero/canary RASTATE differs only at the 80 state
offsets `20260..20339`:

| Frame | Zero RASTATE SHA-256 | Canary RASTATE SHA-256 |
| ---: | --- | --- |
| 61 | `c5f436871891399971bdcb7fa41bc0baea61c549b96071a759c987ac70975104` | `d11164a0663f84d8bdfd432293e82ff12265e1af92023e4fb8a3b85ed24d4a3a` |
| 62 | `53d439a639f742dc4e159a48cc99b0387c0cbcff4031169301887e0319187997` | `e353f960a90ab3ce9954a8d537cf1ebf59ad21c40160fa258c9cf748313299fe` |
| 90 | `6b553cddd1e7f7fdebdd90486a19f250345c37795291a61265e1872a3079b8e7` | `02266e66f3835aadc20a3ba4d1d475e08b2597b86c39ef66a2cd7950da8088da` |
| 300 | `431fec0016be0a01b5ae4b999ac67c02b324e3931f2e85622e0ce4806e0aa8c4` | `c8fb715a8f93f53891c04dfd45b99b9bf1adc28038a1b78574ac54de86c3c0c0` |

Paired screenshots are byte-identical: frames 61 and 62 hash to
`336c52fd0afa5cab86f772db44d25e9a52d28db47104522b56ca32b3451a68d9`,
frame 90 to
`0ed7b26b91b35f00cac8a9909698a5aeec7f2b425d7f4726a7fb21d0427b3bf4`,
and frame 300 to
`ce8f831618e5204318c587a855d68d5fc3cc9ed14eac701667c152a3ef835658`.
Every disposable SRAM remains byte-exact to the source hash.

This control proves that unmodified New Game+ publishes serialized
compatibility bytes over natural PC `$07` and leaves `$2CA0-$2CEF` untouched.
It confirms the loader-translation requirement. It does not install the
source-modeled four-region translation, apply retained/reset state at
`$FF:FB3B`, approve a hook or WRAM allocation, or write/rebind a sidecar.

## Tools

| Source | SHA-256 |
| --- | --- |
| `tools/retroarch_rastate.py` | `17fe0b99a5fe3ac5462358158dbc08f2efc9b8f01d97fc98ee21aeecc6ad0dbd` |
| `tools/edit_retroarch_bsv2_inputs.py` | `17d6b24276777a1d4615d638a02719dc7ecf23c1f01685ee291ae320971075bb` |
| `tools/inspect_retroarch_bsv2_inputs.py` | `4c016bc69cd4adb57bed27db176e22151b4c6f0bcd1defe7d11894487314840f` |
| `tools/inject_bsv2_wram_canary.py` | `c33054bd565932abde36cc28aad665219f5b39c91e6b8740a6bdcf2f2643f55e` |
| `tools/inject_spekkio_event11c_diagnostic.py` | `d0da31629a492da96423f1e55ffedcdb83aad4b05b00c94cc8a49c0c0e8e64ba` |
| `tools/inspect_current_wram_candidate.py` | `86640656d284469306b15d1102be2efc78216312aecf1dba667f2520e4c9d265` |
| `tools/compare_current_wram_canary_pair.py` | `fa23926246378ced2cbdad6810fa35eb23becca40c0030b2e65cc605810cc236` |
| `tools/inspect_ct_srm.py` | `29ac0d38cb314410fbe2d6021cc8181bda82a49f0d75d7adf8080b04776f6e67` |
| `tools/build_current_emulator_evidence_manifest.py` | `7f0b1c4f2ea29998a2914f2633a775aa2d479abd15fe041fedf5d4f1ad6994ea` |
| `tools/rebind_retroarch_bsv2_content_crc.py` | `8299a94804c500764b291415153f658bfe122758f004eb0210c011d29a73ba2d` |
| `tools/mesen_spekkio_checkpoint.lua` | `6edd5fc924fb272714ccbb56c72f038003c3118f9c02d14dc5a5252c6cb01948` |
| `tools/mesen_event11c_trace.lua` | `c6f8480b4dcfd0ff917529c96629bf8dce3da228bc0be07217639b4bec906931` |
| `tools/run_mesen_event11c_trace.py` | `61915fa772761667c7d286a9a0bce3cefbfb6c730cd311c521168d409acf5f0e` |
| `tools/validate_mesen_event11c_trace.py` | `9dab9e43eae63d0200c2502753b62ffd7c9e368d9a0bca85ba5295a8b9978def` |
| `tools/mesen_event11c_relocated_trace.lua` | `4413876f258c091a728a8d6d53e2aea824206c5e7f9852ca476b5ee5c974070c` |
| `tools/run_mesen_event11c_relocated_trace.py` | `78371ecb3974046d170d6613239d08c3b7a56252681af0bb352dac12e4676b4c` |
| `tools/validate_mesen_event11c_relocated_trace.py` | `2025a749fc3081ff7a6dfeb49b7b1c9aa6ae31241c4744be14c23d63e06de186` |

The three relocated-trace sources above are `35700`, `43512`, and `24820`
bytes, respectively.

The corresponding focused test sources have SHA-256:

- `test_retroarch_rastate.py`:
  `828aad12abc3d4df25b25624ff518406f3b8ad4525c34110ac5c175ea6dd30e5`;
- `test_retroarch_bsv2_inputs.py`:
  `608b4bfb6c1173a2f49e543e9876820fff089e9482b8aa44be35b4a892858c26`;
- `test_retroarch_bsv2_inspector.py`:
  `52a54e3132e5aa42d8a22d716c840ca6e053645e7cb8efd9bb3ffafd1c5bd477`;
- `test_bsv2_wram_canary.py`:
  `75803e5c5c7320f9ca12b9867e068df046721a7a1585a8c398964315de606ae1`;
- `test_spekkio_event11c_diagnostic.py`:
  `e40f281b54275b0328c5e049d5591de81dd17a4812e7a396085ed32120b82743`;
- `test_compare_current_wram_canary_pair.py`:
  `d3feb74534d4ba5e6677f8bcbe15dcbe8853fa3569ab8e1701d0b4ed1ae5ed53`;
- `test_inspect_ct_srm.py`:
  `a19ec7eb74b8cdd87b9eae2b88a8527f36ef83f4894e3c8e68246629153a0950`;
- `test_current_emulator_evidence_manifest.py`:
  `3c0fc33cc3102235e221cd3230f25d2db7c43248016c0ad8b1cc699841d05390`;
- `test_retroarch_bsv2_content_rebind.py`:
  `087905778d83273d208ca5ac70eddd15e5f0e345c2fb9287955d77a9be5e4cbb`;
- `test_mesen_event11c_trace.py`:
  `c73a93e5a61ebb1ff7ed88da3b0889e3efb098a27531b83bb8dfaf39369a316b`;
- `test_run_mesen_event11c_trace.py`:
  `aa65c6ab9d309b0618338c320236bd435e1d07c4f41340cbaabd510f3b315e35`.

The complete suite passes 539 tests, and all 62 source-controlled Python
tools syntax-compile.

## Local artifact manifest

All ROMs, SRAMs, movies, states, logs, video, and screenshots remain ignored
under `private/test_runs/retroarch/current/`. The old 82-file recursive
`evidence_manifest.json` is retained only as a historical baseline; it
predates the North Cape work and must not be regenerated or treated as an
acceptance list because the private tree also contains failed and exploratory
calibrations.

The current accepted set is explicit and fail-closed:

- source-controlled acceptance spec:
  `references/current_emulator_accepted_artifacts_v1.json`;
- spec SHA-256:
  `f7a5a2d0b8f9b59850661afa764be8cb23d986757d54d0a002520489a95140ff`;
- local-only curated manifest:
  `private/test_runs/retroarch/current/accepted_evidence_manifest.json`;
- manifest schema: `project-epoch-current-emulator-evidence-v2`;
- accepted artifacts: 95;
- manifest SHA-256:
  `8bfef666d0f2133a37c1f60c2dab0bf216f04c7834d4396fd0e02ed1d37f3c15`.

Reproduce it with:

```powershell
python tools\build_current_emulator_evidence_manifest.py `
  --acceptance-spec references\current_emulator_accepted_artifacts_v1.json `
  --output private\test_runs\retroarch\current\accepted_evidence_manifest.json
```

The builder rejects absolute/traversing/duplicate paths, unknown evidence
levels or reproduction groups, missing files, and an output that appears in
its own accepted list. It labels only listed artifacts `status: accepted`.
Do not distribute the private tree or its ROM/save/state contents.

The 2026-07-27 compatibility-canary tranche is curated independently so the
historical 95-artifact baseline remains reproducible:

- source-controlled acceptance spec:
  `references/current_compatibility_canary_tranche_accepted_artifacts_v1.json`;
- spec SHA-256:
  `fcd94ed43ff2911bb97983734e4d227501fed12ef072a98e1a595e27df370c0a`;
- local-only curated manifest:
  `private/test_runs/retroarch/current/compatibility_canary_tranche_manifest.json`;
- accepted artifacts: 51;
- manifest SHA-256:
  `9c91fc9a697faab89a144d111723c3d61f7dad2717ad86f3e439d9496978de9d`.

Reproduce the tranche manifest with:

```powershell
python tools\build_current_emulator_evidence_manifest.py `
  --acceptance-spec `
    references\current_compatibility_canary_tranche_accepted_artifacts_v1.json `
  --output `
    private\test_runs\retroarch\current\compatibility_canary_tranche_manifest.json
```

The natural Guardia Forest victory route is curated separately from both
earlier sets:

- source-controlled acceptance spec:
  `references/current_guardia_victory_canary_accepted_artifacts_v1.json`;
- spec SHA-256:
  `629ce925dae9f343dc9a8622c56f519a27bbebda92c2a64753cf940ef6f67f45`;
- local-only curated manifest:
  `private/test_runs/retroarch/current/guardia_victory_canary_manifest.json`;
- accepted artifacts: 37;
- manifest SHA-256:
  `cdd2e58c685ec189879d5a79e69cda6cd475fbe5a47f17cfbd7db20fd9c17a68`.

Reproduce it with:

```powershell
python tools\build_current_emulator_evidence_manifest.py `
  --acceptance-spec `
    references\current_guardia_victory_canary_accepted_artifacts_v1.json `
  --output `
    private\test_runs\retroarch\current\guardia_victory_canary_manifest.json
```

The Cyclone command/list/target/effect/control/resolution chain is a fourth
independent curated set:

- source-controlled acceptance spec:
  `references/current_cyclone_multitarget_canary_accepted_artifacts_v1.json`;
- spec SHA-256:
  `5cb863ef8487ba7756c803391b25e547b587fced5271a171752d40812997fc83`;
- local-only curated manifest:
  `private/test_runs/retroarch/current/cyclone_multitarget_canary_manifest.json`;
- accepted artifacts: 25;
- manifest SHA-256:
  `b41b9788ec286214f0aab7652551378700886e74a47c0b62597db4bc7a024eae`.

Reproduce it with:

```powershell
python tools\build_current_emulator_evidence_manifest.py `
  --acceptance-spec `
    references\current_cyclone_multitarget_canary_accepted_artifacts_v1.json `
  --output `
    private\test_runs\retroarch\current\cyclone_multitarget_canary_manifest.json
```

The title-through-attract lifecycle is a fifth independent curated set:

- source-controlled acceptance spec:
  `references/current_attract_canary_accepted_artifacts_v1.json`;
- spec SHA-256:
  `a8808b4b4e0fdc55fa6594f8d9bb12b093c274cc31ae0dbec103617bf24c74a1`;
- local-only curated manifest:
  `private/test_runs/retroarch/current/attract_canary_manifest.json`;
- accepted artifacts: 37;
- manifest SHA-256:
  `500c393b64bf2fa20629ffc83029b08a4fcc4ec72831451bd74f26fb7ad801ba`.

Reproduce it with:

```powershell
python tools\build_current_emulator_evidence_manifest.py `
  --acceptance-spec `
    references\current_attract_canary_accepted_artifacts_v1.json `
  --output `
    private\test_runs\retroarch\current\attract_canary_manifest.json
```

The New Game+ selected-slot partial-load control is a sixth independent
curated set:

- source-controlled acceptance spec:
  `references/current_ngplus_partial_loader_canary_accepted_artifacts_v1.json`;
- spec SHA-256:
  `3744b91c0868cb1b6d1865b139d12746e2895c26464a1a063071ff0aeeeba819`;
- local-only curated manifest:
  `private/test_runs/retroarch/current/ngplus_partial_loader_canary_manifest.json`;
- accepted artifacts: 34;
- manifest SHA-256:
  `130e275b570f931680f1ebe82d041e8d6d5136eadc1442e2277b0c57f1a07334`.

Reproduce it with:

```powershell
python tools\build_current_emulator_evidence_manifest.py `
  --acceptance-spec `
    references\current_ngplus_partial_loader_canary_accepted_artifacts_v1.json `
  --output `
    private\test_runs\retroarch\current\ngplus_partial_loader_canary_manifest.json
```

The controlled Spekkio event `$11C` baseline is a seventh independent curated
set:

- source-controlled acceptance spec:
  `references/current_spekkio_event11c_canary_accepted_artifacts_v1.json`;
- spec SHA-256:
  `774c74b0ab2593c8120af0e7376d0a501dbcfc3602a1bc129d843b649db15d1c`;
- local-only curated manifest:
  `private/test_runs/retroarch/current/spekkio_event11c_canary_manifest.json`;
- accepted artifacts: 21;
- manifest SHA-256:
  `71cbfce6177d31f54719d27677517da8fd9f95c0b3c1f21c82d6730b0e13de66`.

Reproduce it with:

```powershell
python tools\build_current_emulator_evidence_manifest.py `
  --acceptance-spec `
    references\current_spekkio_event11c_canary_accepted_artifacts_v1.json `
  --output `
    private\test_runs\retroarch\current\spekkio_event11c_canary_manifest.json
```

The volatile relocated Mesen trace is a separate curated private set:

- current source-controlled acceptance spec:
  `references/mesen_event11c_relocated_trace_accepted_artifacts_v3.json`;
- spec size / SHA-256:
  `8934` /
  `839b86310dbe33273cf14ffec01386aa4ee6b88426b100be2cdc65d17a0790cc`;
- accepted private artifact root:
  `private/test_runs/mesen2/event11c_relocated_accepted_hardened_v4`;
- safe-launcher reproduction root:
  `private/test_runs/mesen2/event11c_relocated_launcher_replay_hardened_v4`;
- accepted artifacts: eight JSON/PNG files across four profile/variant cases.

The v1 and v2 specs and their accepted/replay roots remain retained as
historical evidence. V2 used trace-v1/collector version 1 labels for the
incompatibly changed hardened trace shape; v3 with trace schema v2 and
collector version 2 is current.

This Mesen set is validated directly by
`tools/validate_mesen_event11c_relocated_trace.py`; it is not mixed into the
RetroArch/current-bsnes manifest builder.

The generic native-Mesen WRAM ownership census is another separate accepted
private set:

- source-controlled scenario contract:
  `references/mesen_wram_ownership_scenarios_v1.json`;
- source-controlled acceptance spec:
  `references/mesen_wram_ownership_accepted_artifacts_v1.json`;
- spec size / SHA-256:
  `10813` /
  `b8f863ab2db7ed5f17222c59044a026305a05db86a7a0303fc3db84bfa197142`;
- accepted private root:
  `private/test_runs/mesen2/wram_ownership_accepted_v2`;
- independent launcher replay:
  `private/test_runs/mesen2/wram_ownership_replay_v2`;
- accepted artifacts: 16 JSON/PNG files across four scenarios and two
  variants.

The collector registers read and write callbacks and per-byte access counters
for the old compatibility block, roster, joined flag, Epoch name, candidate,
and both structural guards. It runs calibration, field idle, main-menu, and
Frog/event-`$11C` routes from the same exact checkpoint. Candidate preparation
occurs before counters and callbacks arm. The accepted set proves zero access
to `$7E2C9C-$2CFF` in those four routes, no writes to Epoch/roster/joined
state, exact counter/callback reconciliation, and identical zero/canary
observations. The event route supplies the required old-block positive
control. It also exposes and validates 25 same-value vanilla writes at
`$2857-$285B`.

Reproduce one complete accepted set into a new private root:

```powershell
$python = 'python'
$out = 'private\test_runs\mesen2\wram_ownership_reproduction_v1'
$cases = @(
  @('calibration', 'zero'),
  @('calibration', 'canary'),
  @('field-idle', 'zero'),
  @('field-idle', 'canary'),
  @('main-menu', 'zero'),
  @('main-menu', 'canary'),
  @('event11c-frog', 'zero'),
  @('event11c-frog', 'canary')
)
foreach ($case in $cases) {
  & $python tools\run_mesen_wram_ownership_trace.py `
    --scenario $case[0] `
    --variant $case[1] `
    --output-dir "$out\$($case[0])\$($case[1])" `
    --timeout 60
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $python tools\validate_mesen_wram_ownership_trace.py `
  "$out\calibration\zero\trace.json" `
  "$out\calibration\canary\trace.json" `
  "$out\field-idle\zero\trace.json" `
  "$out\field-idle\canary\trace.json" `
  "$out\main-menu\zero\trace.json" `
  "$out\main-menu\canary\trace.json" `
  "$out\event11c-frog\zero\trace.json" `
  "$out\event11c-frog\canary\trace.json"
```

Without `--exploratory`, the launcher requires each trace and screenshot to
match its frozen size and SHA-256 before publishing. It stages a complete
Mesen app and unique same-stem ROM/SRAM pair, exact-byte compiles the pinned
validator, verifies all inputs before and after execution, proves the shared
Mesen `Saves` tree unchanged, and removes staging. The event trace freezes at
the first valid end-of-frame endpoint; if Mesen exposes the adjacent
presentation buffer, only screenshot capture waits for the exact canonical
PNG while observers remain disarmed.

This census is not fed to
`build_current_emulator_evidence_manifest.py`; its own acceptance spec and
strict eight-trace validator are authoritative. It does not approve the
candidate as free or install any Project Epoch runtime behavior.

The accepted menu-only extension is a second, separately versioned set:

- source-controlled scenario contract:
  `references/mesen_wram_ownership_menu_scenarios_v2.json`;
- source-controlled acceptance spec:
  `references/mesen_wram_ownership_menu_accepted_artifacts_v2.json`;
- spec size / SHA-256:
  `11785` /
  `c6978ec88c573dd4181e42d4645cbbd76b85612574cacfe4f8e0ef3d59bd2e04`;
- accepted private root:
  `private/test_runs/mesen2/wram_ownership_menu_v2_accepted_v2`;
- independent launcher replay:
  `private/test_runs/mesen2/wram_ownership_menu_v2_replay_v2`;
- accepted artifacts: 16 JSON/PNG files across Equipment, Tech, Item, and
  Party scenarios with zero/canary variants.

The v2 builder requires the exact accepted v1 collector preimage and emits the
derived Lua collector only into a private temporary directory. The launcher
pins the builder, generated bytes, validator, scenario contract, all v1
ancestry, emulator/runtime inputs, and every output hash. Both final roots are
byte-identical. Candidate and guard access remains zero, Epoch/roster/joined
writes remain zero, and all per-byte counters reconcile.

The Tech route has five allowed old-block writes at frame 221,
`$7E2857-$285B`, from `$C2:82E7/$C2:82F3`. They are accepted only with the
exact sequence/value/PC identities and must remain same-value/no-net-change.
The Party path supplies a substantial positive control with 2,065 roster
reads. The endpoints visibly remain on Frog Equipment, Frog Tech, Item
Use/Move, and Party Exchange pages.

Reproduce the menu-only set into a new private root:

```powershell
$python = 'python'
$out = 'private\test_runs\mesen2\wram_ownership_menu_reproduction_v2'
$scenarios = @(
  'equipment-owner-switch',
  'tech-owner-switch',
  'item-list-cancel',
  'party-page-cancel'
)
foreach ($scenario in $scenarios) {
  foreach ($variant in @('zero', 'canary')) {
    & $python tools\run_mesen_wram_ownership_menu_trace_v2.py `
      --scenario $scenario `
      --variant $variant `
      --output-dir "$out\$scenario\$variant" `
      --timeout 60
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
}

$traces = foreach ($scenario in $scenarios) {
  foreach ($variant in @('zero', 'canary')) {
    "$out\$scenario\$variant\trace.json"
  }
}
& $python tools\validate_mesen_wram_ownership_menu_trace_v2.py @traces
```

The schedules contain no final item-use, equipment-change, party-swap, or save
confirmation. The watched roster/joined state proves no serialized party
change. Inventory and equipment arrays are not part of the census, so the
schedule and endpoint images do not constitute byte-level mutation proof for
those systems. Full leave-page cancellation is also outside this tranche.

### Native-Mesen Lavos checkpoint and bounded battle censuses

Three separately accepted native-Mesen 2.1.1 sets now extend the private
instruction-level evidence without joining the current-bsnes manifest.

The command-ready Lavos Core checkpoint is governed by
`references/mesen_lavos_battle_checkpoint_accepted_artifacts_v1.json`
(`4983` bytes, SHA-256
`67cc7c9f7460a3de30a23c90aca53a079b8334c5e80c1975651fcdc60ba08564`).
Its private root is
`private/test_runs/mesen2/lavos_battle_checkpoint_accepted_v1`. The accepted
deterministic set is the canonical native state plus the acquisition,
fresh-load control, and fresh-load Down TSVs. The state is `261614` bytes,
hashes to
`d5825ffff2f2a3b7edbe3c37e7118155d67727dc02ed672d13257f3824482b8b`,
and contains a `324388`-byte decoded core hashing to
`8369e220290e1afc27138df5a1f999dee83cb4fdb462bc13c152ef1c313ecf4c`.
Matched exploratory runs v15/v16 reproduced all four deterministic artifacts
byte-for-byte. Fresh-process reloads preserve the exact full-HP Lavos battle
anchor; the control remains on Attack and the released Down pulse selects
Tech without executing an action.

`endpoint.png` and `command_down.png` are supporting presentation only.
Their per-run hashes are recorded in `presentation_manifest.json`, but neither
the PNGs nor that manifest are deterministic acceptance gates because
equivalent state/trace runs exposed different continuously rendered frames.

The bounded battle-ownership census is governed by
`references/mesen_wram_ownership_battle_scenarios_v3.json` (`7042` bytes,
SHA-256
`934e56f08585e315c37287f9351773473125874f6ca6296f10e0af746c20f83a`)
and `references/mesen_wram_ownership_battle_accepted_artifacts_v3.json`
(`10855` bytes, SHA-256
`203dd4409d4d662ac76f88c0b52b1f358fe829ddea7efacdf8f86bd1cc3900b3`).
The accepted and independent replay roots are respectively
`private/test_runs/mesen2/wram_ownership_battle_v3_accepted_v2` and
`private/test_runs/mesen2/wram_ownership_battle_v3_replay_v2`. Acceptance
covers eight exact JSON traces: zero/canary pairs for frame-zero calibration,
60-frame idle, Down-then-Up command roundtrip, and Down-to-Tech. The eight PNGs
are again presentation-only.

Across those exact routes, all scenarios share one candidate-normalized
checkpoint preimage; the 196 watched bytes reconcile counters and callbacks;
the candidate and both guards have zero access; the old compatibility block
has zero reads and writes; roster, joined, and Epoch-name writes are absent;
and every accepted trace is byte-identical to its independent replay.

That battle-v3 command census is bounded ownership evidence only. It does not
approve `$7E2CA0-$7E2CEF` as an allocation or `$7E2830-$7E287F` as a
relocation target. It covers no attack, Tech, or Item execution, enemy action,
damage, status, death, victory, teardown, save/load, New Game+, erase, reset,
attract, shop, equipment, or naming path.

The separate battle-action v4 census is governed by
`references/mesen_wram_ownership_battle_action_scenarios_v4.json` (`12552`
bytes, SHA-256
`ad6d686bdc01f93ce9abed3c21beb4a2bac5d5142883f94fc29c6e3f06c6f727`).
The complete source/private-evidence manifest is
`references/mesen_wram_ownership_battle_action_accepted_artifacts_v4.json`
(`11045` bytes, SHA-256
`0d0936cccb1640109eeab09b870281ff638e736bcd75b1b77fc2ce93a319c2d6`).
Its accepted and independent replay roots are respectively
`private/test_runs/mesen2/wram_ownership_battle_action_v4_accepted_critical_v2`
and
`private/test_runs/mesen2/wram_ownership_battle_action_v4_replay_critical_v2`.

The six exact JSON traces are zero/canary pairs for:

| Scenario | Input | Terminal / last signature | Rows | Current HP endpoint | Battle UI | Command-state endpoint |
| --- | --- | --- | ---: | --- | --- | --- |
| action control | none | `606 / 603` | 269 | `739,821,712,8000,12000,20000` | `03bf59` | `00000000000102000300000000` |
| Attack target hold | A `20-23` | `60 / 60` | 17 | `969,898,909,8000,12000,20000` | `0059ac` | `0000000000ffff000100000000` |
| Attack recovery | A `20-23`, A `32-35` | `606 / 606` | 206 | `739,821,712,7038,12000,20000` | `003a00` | `01000000ff01ff010100000000` |

The complete signature-change timeline, not the rendered endpoint, is the
action proof. It pins the control's enemy-only party damage at frame 336; the
target-selection state at frame 20; and, in recovery, player enqueue at frame
32, the same enemy-only damage at frame 337, player dequeue at frame 373,
the `$AE9B` bit-`$80` critical marker at frame 375, enemy-slot-3 damage at
frame 557, and command recovery at frame 606. Control and recovery finish with
identical party HP `739,821,712`; only recovery lowers enemy slot 3 from
`8000` to `7038`.

All 196 watched counters reconcile. The old compatibility block, candidate,
and both guards have zero measured access, and no watched write occurs after
observer arm. In each recovery variant, the only callbacks are two reads of
`$7E2980=$00` at frame 377, with advanced PCs `$C1:4A43` then `$C1:438A`.
The paired observations are otherwise exact, and every accepted JSON trace is
byte-identical to its independent replay. Screenshots remain presentation-only
and outside the acceptance gate; some differ across otherwise byte-identical
trace runs.

This supplies bounded action/resolution evidence for one already-in-flight
enemy action and one Crono critical Attack only. It does not approve either
WRAM range, the relocation, or PC `$07`. Noncritical Attack, attacks by other
PCs, Tech, Item, status, death, victory, teardown, persistence, save/load, New
Game+, erase, reset, attract, shop, equipment, and naming paths remain
untested in this tranche.

Reproduce the accepted route only into fresh ignored private roots. The
launcher defaults to the pinned local Mesen, ROM, SRAM, and checkpoint paths:

```powershell
$epochPython = 'python'
$primary = 'private\test_runs\mesen2\battle_action_v4_reproduction_a'
$replay = 'private\test_runs\mesen2\battle_action_v4_reproduction_b'
$scenarios = @(
  'battle-action-control',
  'battle-attack-target-hold',
  'battle-attack-recovery'
)

foreach ($root in @($primary, $replay)) {
  foreach ($scenario in $scenarios) {
    foreach ($variant in @('zero', 'canary')) {
      & $epochPython tools\run_mesen_wram_ownership_battle_action_trace_v4.py `
        --scenario $scenario `
        --variant $variant `
        --output-dir "$root\$scenario\$variant"
    }
  }
}

& $epochPython tools\validate_mesen_wram_ownership_battle_action_replay_v4.py `
  --primary-root $primary `
  --replay-root $replay
```

Default launcher mode hash-gates each JSON trace. Add `--exploratory` only for
a strict diagnostic that deliberately makes no acceptance claim. The replay
validator independently validates both six-trace sets before requiring exact
JSON bytes; it never compares PNGs.

## Reproduction outline

First stage same-stem disposable ROM/SRAM copies below `current/roms` and
`current/saves`. Never point current bsnes at the canonical recovered SRAM.

Record a zero-input replay:

```powershell
& 'private\tools\RetroArch-1.22.2\retroarch.exe' `
  -c 'private\test_runs\retroarch\current\retroarch-current-null.cfg' `
  -L 'private\tools\RetroArch-1.22.2\cores\bsnes_libretro.dll' `
  -R 'private\test_runs\retroarch\current\boot_zero_3600.bsv' `
  --sram-mode=load-nosave `
  --max-frames=3600 `
  --verbose `
  --log-file 'private\test_runs\retroarch\current\boot_zero_3600.log' `
  'private\test_runs\retroarch\current\roms\chrono_trigger_current_clean.sfc'
```

Add the exact slot-load inputs:

```powershell
python tools\edit_retroarch_bsv2_inputs.py `
  private\test_runs\retroarch\current\boot_zero_3600.bsv `
  private\test_runs\retroarch\current\slot1_load_candidate.bsv `
  --press 1800:left:2 `
  --press 1950:a:10
```

Play that replay with `-P`, stop at frame 2700, and enable the local
`autostate-on-exit.cfg` override to capture the field RASTATE. Convert it into
a raw field checkpoint:

```powershell
python tools\edit_retroarch_bsv2_inputs.py `
  private\test_runs\retroarch\current\boot_zero_3600.bsv `
  private\test_runs\retroarch\current\field_checkpoint_zero.bsv `
  --initial-rastate `
  private\test_runs\retroarch\current\states\chrono_trigger_current_clean.state.auto
```

Inject and verify the candidate canary:

```powershell
python tools\inject_bsv2_wram_canary.py `
  private\test_runs\retroarch\current\field_checkpoint_zero.bsv `
  --srm `
  private\test_runs\retroarch\current\saves\chrono_trigger_current_clean.srm `
  -o private\test_runs\retroarch\current\field_checkpoint_canary.bsv

python tools\inspect_current_wram_candidate.py `
  private\test_runs\retroarch\current\field_checkpoint_canary.bsv `
  --srm `
  private\test_runs\retroarch\current\saves\chrono_trigger_current_clean.srm `
  --require-canary
```

For the title/attract carrier, replace the zero movie's initial state with the
captured frame-1,800 title RASTATE, then use the fail-closed pinned
current-core layout because no loaded record pair exists at title:

```powershell
python tools\edit_retroarch_bsv2_inputs.py `
  private\test_runs\retroarch\current\agent_attract_zero_30000.bsv `
  private\test_runs\retroarch\current\agent_attract_title_checkpoint_zero_30000.bsv `
  --initial-rastate `
  private\test_runs\retroarch\current\states\chrono_trigger_current_agent_attract_boot_1800.state.auto

python tools\inject_bsv2_wram_canary.py `
  private\test_runs\retroarch\current\agent_attract_title_checkpoint_zero_30000.bsv `
  --pinned-current-layout `
  -o `
  private\test_runs\retroarch\current\agent_attract_title_checkpoint_canary_30000.bsv
```

The pinned mode accepts only the exact 290,423-byte current-bsnes
`BST1`/115.1 state and still requires zero candidate bytes and guards. Compare
the matched endpoints with:

```powershell
python tools\compare_current_wram_canary_pair.py `
  private\test_runs\retroarch\current\states\chrono_trigger_current_agent_attract_zero_4800.state.auto `
  private\test_runs\retroarch\current\states\chrono_trigger_current_agent_attract_canary_4800.state.auto `
  --srm private\input\lavos_save\chrono_trigger.srm
```

For the New Game+ control, create the raw slot-selection checkpoint from the
accepted frame-2,000 state, inject the candidate only through the same pinned
current-core layout, and add the two-frame slot confirmation:

```powershell
python tools\edit_retroarch_bsv2_inputs.py `
  private\test_runs\retroarch\current\ngplus_title_zero_2400.bsv `
  private\test_runs\retroarch\current\ngplus_slotselect_checkpoint_zero.bsv `
  --initial-rastate `
  private\test_runs\retroarch\current\states\chrono_trigger_current_ngplus_select_probe.state.auto

python tools\inject_bsv2_wram_canary.py `
  private\test_runs\retroarch\current\ngplus_slotselect_checkpoint_zero.bsv `
  --pinned-current-layout `
  -o `
  private\test_runs\retroarch\current\ngplus_slotselect_checkpoint_canary.bsv

python tools\edit_retroarch_bsv2_inputs.py `
  private\test_runs\retroarch\current\ngplus_slotselect_checkpoint_zero.bsv `
  private\test_runs\retroarch\current\ngplus_slot1_confirm_zero.bsv `
  --press 60:a:2

python tools\edit_retroarch_bsv2_inputs.py `
  private\test_runs\retroarch\current\ngplus_slotselect_checkpoint_canary.bsv `
  private\test_runs\retroarch\current\ngplus_slot1_confirm_canary.bsv `
  --press 60:a:2
```

Play each confirmation movie only against same-stem disposable ROM/SRAM
fixtures created from the pinned local inputs and use
`--sram-mode=load-nosave`. Capture frames 61, 62, 90, and 300, then compare
each matched pair with `compare_current_wram_canary_pair.py`. The source SRAM
and all disposable copies must retain SHA-256
`ba2b0a32d8f827f572e08bff381a693ccb192bac45141ed9521421d2a2410ac5`.

`--require-canary` now means the candidate matches, occurs exactly once, and
retains zero front/rear guards. The inspector also decodes PC1 battle
current/max HP and MP at
`$7E5E30-$7E5E37` plus enemy slot 3 current/max HP at
`$7E5FB0-$7E5FB3`. Its synthetic fixture seeds distinct nonzero little-endian
values for every field so offset and byte-order regressions cannot pass as
zero reads.

Generate menu and reset movies by adding Player-1 X or
Select+Start+L+R at populated frame 60. Play each against its own same-stem
ROM/SRAM fixture, capture an on-exit RASTATE, and inspect with
`--require-canary` or `--require-zero` as appropriate.

For an inert ExHiROM control, change only the replay's content CRC:

```powershell
python tools\rebind_retroarch_bsv2_content_crc.py `
  private\test_runs\retroarch\current\field_checkpoint_canary.bsv `
  private\test_runs\exhirom\project_epoch_inert_exhirom.sfc `
  --expected-source-rom `
  private\test_runs\retroarch\current\roms\chrono_trigger_current_clean.sfc `
  -o `
  private\test_runs\retroarch\current\field_checkpoint_canary_inert_exhirom.bsv
```

Play the original and rebound movies against same-stem disposable fixtures.
Compare the `core_state_sha256` values emitted by
`inspect_current_wram_candidate.py`; container hashes are expected to differ
because their replay chunks contain different content CRCs.
