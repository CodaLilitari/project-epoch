#!/usr/bin/env python3
"""Audit the vanilla 0x50-byte playable-character initialization record.

This tool is intentionally non-extractive. It accepts only the canonical
headerless Chrono Trigger US Rev0 ROM, validates the small tables and
initialization invariants needed by Project Epoch, and emits semantic metadata,
addresses, counts, hashes, and bounded exception lists. It never emits a raw
character record, a ROM slice, graphics, text, or other copyrighted payload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from collections.abc import ByteString, Sequence
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DISASSEMBLY_ROOT = ROOT / "references" / "ct_disassembly"

CANONICAL_ROM_SIZE = 0x400000
CANONICAL_ROM_SHA1 = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_ROM_SHA256 = (
    "06d1c2b06b716052c5596aaa0c2e5632"
    "a027fee1a9a28439e509f813c30829a9"
)

PINNED_DISASSEMBLY_COMMIT = "eeae27acdb6565e96d1d796a3d60792c250c0aa1"
PINNED_SOURCE_HASHES = {
    "bank_C1.asm": (
        "298ad8f0ef01097b1018e1cdd154a4e6"
        "3d52b6debaa1d94dd85ecf2b8aaa15aa"
    ),
    "bank_C2.asm": (
        "d96c0d9707d9150dbdb3ad7d995f7ae1"
        "35e87ebb6329691cab2eb86447611032"
    ),
    "bank_FD.asm": (
        "0f8a0d59e97de7d60945fdfef1b61421"
        "7e3d673cca1e14f543234d789a87779e"
    ),
    "battle_work.asm": (
        "aa7384d56be567947dd6dad2191058c27"
        "b419bcbbf57293a73f6bf296851587a"
    ),
    "data/char_init.asm": (
        "a90f351087671234682a56e024d41995"
        "8d42901d306ae49fc33b19da2a106f68"
    ),
    "data/hp_growth.asm": (
        "f0dad5f5a7970a113798624e5a8b0b40"
        "3eabd99315db30124239ced2514eac98"
    ),
    "data/mp_growth.asm": (
        "8d25a287e1b595013c31f20e27659136"
        "2c4979c9daa6c215e5e52843ff9750f3"
    ),
    "data/stat_growth.asm": (
        "64e5973ed6eb02bf9bc7d0213a54f5f0"
        "1caee850429279c8672cc2fc7da03fa9"
    ),
    "data/xp_to_next.asm": (
        "79bc2fd492d4d94a9d1889b18a029e1e"
        "0a9ec64e5645f40fb938616fd29e1b34"
    ),
    "data/tp_to_next.asm": (
        "e81b8a8417c830f8dd77e0237ba1dda"
        "afbc22ee68863d465838d091a33ff4796"
    ),
    "data/dual_tech_req.asm": (
        "d2b70c65046c4ca535a8189dd4fbf21c"
        "1adcc4b96ed967026b146f8221f2b76c"
    ),
    "data/combo_req.asm": (
        "5a439f3467964d6e6667e6714027b444"
        "9485dbe2a0c7d62f289a8aaed8bed6ad"
    ),
}

SOURCE_ANCHORS = {
    "bank_C1.asm": (
        "Battle_UpdateNearFatalFlag:",
        "Battle_CommitPartyRecordsToLive:",
        "Battle_ReloadPartyCharInitData:",
        "Battle_AwardTp:",
        "Tech_Learn:",
        "Battle_LevelUp_RecomputeStats:",
        "Battle_LevelUpCheck:",
        "Battle_ApplyHpMpGrowth:",
        "Battle_AddXpToChar:",
        "Battle_RecalcEquipStats",
        "Battle_DerivedStats_PerSlot:",
    ),
    "bank_C2.asm": (
        "Menu_LoadCharRecordToBuf:",
        "Menu_CommitComputedStats:",
        "Menu_AccumEquipSlotStats:",
        "NewGame_SeedCharStatsAndTechs:",
        "Menu_RecalcAllCharStats:",
        "Item_ApplyStatTab:",
    ),
    "bank_FD.asm": (
        "Battle_LoadPcRecordToWork:",
        "NewGame_InitCharacterData:",
        "CopyCharInitData:",
        "Battle_InitElemModifiers:",
        "NewGameHpMpPtrTable:",
        "DATA8_FDBA4A = $FDBA4A",
    ),
    "battle_work.asm": (
        "BatWork_StatusCur0",
        "BatWork_StatusPerm0",
        "BatWork_CurPower",
        "BatWork_CurMaxHp",
    ),
    "data/char_init.asm": (
        "CharInitData = $CC0000",
        'incbin "data/bank_CC.bin":$0000..$0230',
    ),
    "data/hp_growth.asm": (
        "HpGrowthTable = $CC258A",
        'incbin "data/bank_CC.bin":$258A..$25C2',
    ),
    "data/mp_growth.asm": (
        "MpGrowthTable = $CC25C2",
        'incbin "data/bank_CC.bin":$25C2..$25FA',
    ),
    "data/stat_growth.asm": (
        "StatGrowthTable = $CC25FA",
        'incbin "data/bank_CC.bin":$25FA..$2632',
    ),
    "data/xp_to_next.asm": (
        "XpToNextLevelTable = $CC2632",
        'incbin "data/bank_CC.bin":$2632..$26FA',
    ),
    "data/tp_to_next.asm": (
        "TpToNextTechTable = $CC26FA",
        'incbin "data/bank_CC.bin":$26FA..$276A',
    ),
    "data/dual_tech_req.asm": (
        "DualTechReqTable = $CC2778",
        'incbin "data/bank_CC.bin":$2778..$27FA',
    ),
    "data/combo_req.asm": (
        "ComboReqLists = $CC27FA",
        'incbin "data/bank_CC.bin":$27FA..$28DB',
    ),
}

PC_NAMES = ("Crono", "Marle", "Lucca", "Robo", "Frog", "Ayla", "Magus")
PC_RECORD_SIZE = 0x50
PC_RECORD_COUNT = 7

CHAR_INIT_FILE = 0x0C0000
CHAR_INIT_LENGTH = PC_RECORD_COUNT * PC_RECORD_SIZE
CHAR_INIT_SHA256 = (
    "083676606d3339767c5b189594390dcc"
    "bcb922adf27380178a4cb96cadc35fa0"
)

COMPATIBILITY_FILE = 0x0C0230
COMPATIBILITY_LENGTH = 0x50
COMPATIBILITY_SHA256 = (
    "ca33129e383fea5c0ad8e176d7847f5"
    "118ccbbf77ea1098da9ec1f24c0451123"
)

START_TECH_COUNT_FILE = 0x0C0230
START_TECH_MASK_FILE = 0x0C0237
EXPECTED_START_TECH_COUNTS = (0, 0, 0, 2, 1, 0, 3)
EXPECTED_START_TECH_MASKS = (0x00, 0x00, 0x00, 0xC0, 0x80, 0x00, 0xE0)

HP_GROWTH_FILE = 0x0C258A
HP_GROWTH_LENGTH = 7 * 8
HP_GROWTH_SHA256 = (
    "cefb961e2f1c15f0b129903c242c36f"
    "937d69c729699aad5c626fdd4c27fecc3"
)

MP_GROWTH_FILE = 0x0C25C2
MP_GROWTH_LENGTH = 7 * 8
MP_GROWTH_SHA256 = (
    "b95a1315c22dde61e9d3811f94d51718"
    "6db010323ba5e348ff22ab3caa7a7641"
)

STAT_GROWTH_FILE = 0x0C25FA
STAT_GROWTH_ROW_SIZE = 7
STAT_GROWTH_COUNT = 8
STAT_GROWTH_LENGTH = STAT_GROWTH_ROW_SIZE * STAT_GROWTH_COUNT
STAT_GROWTH_SHA256 = (
    "899a8c7c2858b9e0190a37c5866fdb07"
    "3c6167f2ab32be509cde49777fe8e94d"
)

XP_TO_NEXT_FILE = 0x0C2632
XP_TO_NEXT_COUNT = 100
XP_TO_NEXT_LENGTH = XP_TO_NEXT_COUNT * 2
XP_TO_NEXT_SHA256 = (
    "e487b79afff9984803da858c47042702"
    "a8bdda1fea95d427e16210b0743a0727"
)

TP_TO_NEXT_FILE = 0x0C26FA
TP_TO_NEXT_ROW_SIZE = 0x10
TP_TO_NEXT_COUNT = 7
TP_TO_NEXT_LENGTH = TP_TO_NEXT_ROW_SIZE * TP_TO_NEXT_COUNT
TP_TO_NEXT_SHA256 = (
    "8a47a0529a92c6d02aa5598e19c35e53"
    "e115721f9aa4c1b43ebca222c69287df"
)

DUAL_TECH_REQ_FILE = 0x0C2778
DUAL_TECH_REQ_RECORD_SIZE = 5
DUAL_TECH_REQ_RECORD_COUNT = 26
DUAL_TECH_REQ_LENGTH = (
    DUAL_TECH_REQ_RECORD_SIZE * DUAL_TECH_REQ_RECORD_COUNT
)
DUAL_TECH_REQ_SHA256 = (
    "cbe1b5bf58a5b808ea161cc2e6a64b4"
    "c57a01871a96db1aef5e539e14370519f"
)
COMBO_REQ_LISTS_SNES_START = 0x27FA
COMBO_REQ_LISTS_SNES_END_EXCLUSIVE = 0x28DB

# The first span resets the five-byte record index, walks to a first-byte
# $FF sentinel, and stores $283E + index in direct-page pointer $00. The
# second consumes that pointer at $C1:F5C1/$C1:F5C7. Hashes pin the exact
# canonical code without emitting its bytes.
COMBO_LEARN_SCAN_CODE_FILE = 0x01F25F
COMBO_LEARN_SCAN_CODE_LENGTH = 0x42
COMBO_LEARN_SCAN_CODE_SHA256 = (
    "fa1b904e8f0c304665ca57d8ace0a808"
    "7f1b7b83ed3a87490af6c502e83583a2"
)
COMBO_LEARN_ACCESS_CODE_FILE = 0x01F565
COMBO_LEARN_ACCESS_CODE_LENGTH = 0x65
COMBO_LEARN_ACCESS_CODE_SHA256 = (
    "221c5499dbc55476a702aa2eec365f217"
    "140986c0feec847d863c2a716d9ba0b"
)
COMBO_LEARN_WRAM_BASE = 0x283E
ROCK_LEARNED_FLAGS_WRAM_START = 0x2857

# Three little-endian pointers end at $FD:B9A1. The following bytes at
# $FD:B9A2 are the first block's initial HP value ($0320), not a fourth
# pointer, even though the pinned disassembly renders all eight bytes in one
# db directive.
FD_HP_MP_POINTER_FILE = 0x3DB99C
FD_HP_MP_POINTER_LENGTH = 6
FD_HP_MP_POINTER_SHA256 = (
    "a0c4aff4501d253400f370a56c1cc1bf"
    "f57def9f9e850c6f670fdfd85f0d2776"
)
EXPECTED_FD_HP_MP_POINTER_WORDS = (0xB9A2, 0xB9DA, 0xBA12)
FD_HP_MP_BLOCKS = (
    (
        0x3DB9A2,
        "a2e29ab43f62814f9c917825da0658e5"
        "476e76717b9442e45c660bd1a013a61a",
    ),
    (
        0x3DB9DA,
        "a2e29ab43f62814f9c917825da0658e5"
        "476e76717b9442e45c660bd1a013a61a",
    ),
    (
        0x3DBA12,
        "859d2e26f81b1edc3679137bfd0dfade"
        "c8583d6691e667ecadece4fd66a692d2",
    ),
)
FD_HP_MP_DATA_END_FILE = 0x3DBA4A

EXPECTED_BYTE01 = (0x86, 0x2A, 0x1A, 0x44, 0x24, 0x1C, 0x42)
EXPECTED_BYTE02 = 0x80

# The engine consumes the stat-growth row in this order. It is deliberately
# not the base-stat byte order at record +0x0B.
STAT_GROWTH_LAYOUT = (
    {
        "name": "power",
        "growth_index": 0,
        "base_offset": 0x0B,
        "baseline_offset": 0x2F,
        "recomputed": True,
    },
    {
        "name": "stamina",
        "growth_index": 1,
        "base_offset": 0x0C,
        "baseline_offset": 0x30,
        "recomputed": True,
    },
    {
        "name": "speed",
        "growth_index": 2,
        "base_offset": 0x0D,
        "baseline_offset": 0x31,
        "recomputed": False,
    },
    {
        "name": "hit",
        "growth_index": 3,
        "base_offset": 0x0F,
        "baseline_offset": 0x32,
        "recomputed": True,
    },
    {
        "name": "evade",
        "growth_index": 4,
        "base_offset": 0x10,
        "baseline_offset": 0x33,
        "recomputed": True,
    },
    {
        "name": "magic",
        "growth_index": 5,
        "base_offset": 0x0E,
        "baseline_offset": 0x34,
        "recomputed": True,
    },
    {
        "name": "magic_defense",
        "growth_index": 6,
        "base_offset": 0x11,
        "baseline_offset": 0x35,
        "recomputed": True,
    },
)

# Non-overlapping primary byte ownership for the full 0x50-byte record. Some
# rows have multiple context-specific meanings described in "semantic".
FIELD_SCHEMA = (
    {
        "offset": 0x00,
        "size": 1,
        "name": "logical_identity",
        "semantic": (
            "logical/portrait identity; indexes growth and name/formula paths"
        ),
        "evidence": "verified-static",
    },
    {
        "offset": 0x01,
        "size": 1,
        "name": "innate_element_and_unmapped_flags",
        "semantic": (
            "bits 7..4 select one of four innate-element modifier slots; "
            "bits 3..0 remain unmapped"
        ),
        "evidence": "verified-static",
        "mapping_status": "partial",
    },
    {
        "offset": 0x02,
        "size": 1,
        "name": "pc_progress_flags",
        "semantic": (
            "bit0 near-fatal; bit4 all single techs learned; other bits "
            "unmapped in this bounded audit"
        ),
        "evidence": "verified-static",
        "mapping_status": "partial",
    },
    {
        "offset": 0x03,
        "size": 2,
        "name": "current_hp",
        "semantic": "current HP, little-endian u16",
        "evidence": "verified-static",
    },
    {
        "offset": 0x05,
        "size": 2,
        "name": "base_max_hp",
        "semantic": (
            "base max HP, little-endian u16; level growth mutates it; battle "
            "temporarily applies HP accessories then restores it before commit"
        ),
        "evidence": "verified-static",
    },
    {
        "offset": 0x07,
        "size": 2,
        "name": "current_mp",
        "semantic": "current MP, little-endian u16",
        "evidence": "verified-static",
    },
    {
        "offset": 0x09,
        "size": 2,
        "name": "base_max_mp",
        "semantic": "base max MP, little-endian u16; level growth mutates it",
        "evidence": "verified-static",
    },
    {
        "offset": 0x0B,
        "size": 1,
        "name": "base_power",
        "semantic": "persistent base Power",
        "evidence": "verified-static",
    },
    {
        "offset": 0x0C,
        "size": 1,
        "name": "base_stamina",
        "semantic": "persistent base Stamina",
        "evidence": "verified-static",
    },
    {
        "offset": 0x0D,
        "size": 1,
        "name": "base_speed",
        "semantic": "persistent base Speed; not growth-recomputed",
        "evidence": "verified-static",
    },
    {
        "offset": 0x0E,
        "size": 1,
        "name": "base_magic",
        "semantic": "persistent base Magic",
        "evidence": "verified-static",
    },
    {
        "offset": 0x0F,
        "size": 1,
        "name": "base_hit",
        "semantic": "persistent base Hit",
        "evidence": "verified-static",
    },
    {
        "offset": 0x10,
        "size": 1,
        "name": "base_evade",
        "semantic": "persistent base Evade",
        "evidence": "verified-static",
    },
    {
        "offset": 0x11,
        "size": 1,
        "name": "base_magic_defense",
        "semantic": "persistent base Magic Defense",
        "evidence": "verified-static",
    },
    {
        "offset": 0x12,
        "size": 1,
        "name": "level",
        "semantic": "level, capped at 99",
        "evidence": "verified-static",
    },
    {
        "offset": 0x13,
        "size": 3,
        "name": "total_experience",
        "semantic": "cumulative EXP, little-endian u24, capped at 9,999,999",
        "evidence": "verified-static",
    },
    {
        "offset": 0x16,
        "size": 3,
        "name": "total_tech_points",
        "semantic": "cumulative TP, little-endian u24, capped at 9,999,999",
        "evidence": "verified-static",
    },
    {
        "offset": 0x19,
        "size": 1,
        "name": "combatant_category_mask",
        "semantic": (
            "battle target/category mask; canonical PC templates seed zero"
        ),
        "evidence": "verified-static",
        "mapping_status": "partial",
    },
    {
        "offset": 0x1A,
        "size": 1,
        "name": "combatant_effect_flags",
        "semantic": (
            "secondary battle effect-eligibility/category byte; canonical PC "
            "templates seed zero"
        ),
        "evidence": "verified-static",
        "mapping_status": "partial",
    },
    {
        "offset": 0x1B,
        "size": 1,
        "name": "enemy_attack_variant",
        "semantic": (
            "enemy-side attack variant/context byte; canonical PC templates "
            "seed zero"
        ),
        "evidence": "verified-static",
        "mapping_status": "partial",
    },
    {
        "offset": 0x1C,
        "size": 1,
        "name": "unmapped_1c",
        "semantic": "canonical PC templates seed zero; no PC meaning proved",
        "evidence": "verified-static",
        "mapping_status": "unmapped",
    },
    {
        "offset": 0x1D,
        "size": 5,
        "name": "current_status_groups",
        "semantic": "five current battle-status groups",
        "evidence": "verified-static",
        "mapping_status": "partial",
    },
    {
        "offset": 0x22,
        "size": 5,
        "name": "permanent_status_groups",
        "semantic": (
            "five permanent/equipment-innate status and immunity groups"
        ),
        "evidence": "verified-static",
        "mapping_status": "partial",
    },
    {
        "offset": 0x27,
        "size": 1,
        "name": "helmet_id",
        "semantic": "equipped helmet item ID",
        "evidence": "verified-static",
    },
    {
        "offset": 0x28,
        "size": 1,
        "name": "armor_id",
        "semantic": "equipped armor item ID",
        "evidence": "verified-static",
    },
    {
        "offset": 0x29,
        "size": 1,
        "name": "weapon_id",
        "semantic": "equipped weapon item ID",
        "evidence": "verified-static",
    },
    {
        "offset": 0x2A,
        "size": 1,
        "name": "accessory_id",
        "semantic": "equipped accessory item ID",
        "evidence": "verified-static",
    },
    {
        "offset": 0x2B,
        "size": 2,
        "name": "experience_to_next_level",
        "semantic": "remaining EXP to the next level, little-endian u16",
        "evidence": "verified-static",
    },
    {
        "offset": 0x2D,
        "size": 2,
        "name": "tech_points_to_next_single",
        "semantic": "remaining TP to the next single tech, little-endian u16",
        "evidence": "verified-static",
    },
    {
        "offset": 0x2F,
        "size": 1,
        "name": "level1_power_baseline",
        "semantic": "Power baseline used by level-up recomputation",
        "evidence": "verified-static",
    },
    {
        "offset": 0x30,
        "size": 1,
        "name": "level1_stamina_baseline",
        "semantic": "Stamina baseline used by level-up recomputation",
        "evidence": "verified-static",
    },
    {
        "offset": 0x31,
        "size": 1,
        "name": "unused_speed_baseline",
        "semantic": "zero placeholder; the level-up routine skips Speed growth",
        "evidence": "verified-static",
    },
    {
        "offset": 0x32,
        "size": 1,
        "name": "level1_hit_baseline",
        "semantic": "Hit baseline used by level-up recomputation",
        "evidence": "verified-static",
    },
    {
        "offset": 0x33,
        "size": 1,
        "name": "level1_evade_baseline",
        "semantic": "Evade baseline used by level-up recomputation",
        "evidence": "verified-static",
    },
    {
        "offset": 0x34,
        "size": 1,
        "name": "level1_magic_baseline",
        "semantic": "Magic baseline used by level-up recomputation",
        "evidence": "verified-static",
    },
    {
        "offset": 0x35,
        "size": 1,
        "name": "level1_magic_defense_baseline",
        "semantic": "Magic Defense baseline used by level-up recomputation",
        "evidence": "verified-static",
    },
    {
        "offset": 0x36,
        "size": 1,
        "name": "derived_power",
        "semantic": "equipment-adjusted/live Power",
        "evidence": "verified-static",
    },
    {
        "offset": 0x37,
        "size": 1,
        "name": "derived_stamina",
        "semantic": "equipment-adjusted/live Stamina",
        "evidence": "verified-static",
    },
    {
        "offset": 0x38,
        "size": 1,
        "name": "derived_speed",
        "semantic": "equipment-adjusted/live Speed",
        "evidence": "verified-static",
    },
    {
        "offset": 0x39,
        "size": 1,
        "name": "derived_magic",
        "semantic": "equipment-adjusted/live Magic",
        "evidence": "verified-static",
    },
    {
        "offset": 0x3A,
        "size": 1,
        "name": "derived_hit",
        "semantic": "equipment-adjusted/live Hit",
        "evidence": "verified-static",
    },
    {
        "offset": 0x3B,
        "size": 1,
        "name": "derived_evade",
        "semantic": "equipment-adjusted/live Evade",
        "evidence": "verified-static",
    },
    {
        "offset": 0x3C,
        "size": 1,
        "name": "derived_magic_defense",
        "semantic": "equipment-adjusted/live Magic Defense",
        "evidence": "verified-static",
    },
    {
        "offset": 0x3D,
        "size": 1,
        "name": "derived_attack",
        "semantic": "derived/live Attack",
        "evidence": "verified-static",
    },
    {
        "offset": 0x3E,
        "size": 1,
        "name": "derived_defense",
        "semantic": "derived/live Defense",
        "evidence": "verified-static",
    },
    {
        "offset": 0x3F,
        "size": 4,
        "name": "context_derived_3f_42",
        "semantic": (
            "menu/live view: +3F..40 is equipment-adjusted max HP; battle "
            "view: +3F..42 is overwritten with four element modifiers"
        ),
        "evidence": "verified-static",
        "mapping_status": "contextual",
    },
    {
        "offset": 0x43,
        "size": 5,
        "name": "battle_weapon_descriptor",
        "semantic": (
            "battle-reloaded weapon descriptor remainder; template bytes are "
            "initial FF sentinels, not authoring space"
        ),
        "evidence": "verified-static",
        "mapping_status": "contextual",
    },
    {
        "offset": 0x48,
        "size": 3,
        "name": "battle_armor_descriptor",
        "semantic": (
            "battle-reloaded armor descriptor; template bytes are initial FF "
            "sentinels"
        ),
        "evidence": "verified-static",
        "mapping_status": "contextual",
    },
    {
        "offset": 0x4B,
        "size": 4,
        "name": "battle_accessory_descriptor",
        "semantic": (
            "battle-reloaded accessory descriptor; template bytes are initial "
            "FF sentinels"
        ),
        "evidence": "verified-static",
        "mapping_status": "contextual",
    },
    {
        "offset": 0x4F,
        "size": 1,
        "name": "unmapped_4f",
        "semantic": (
            "initial FF sentinel; no durable source meaning proved by this "
            "bounded audit"
        ),
        "evidence": "verified-static",
        "mapping_status": "unmapped",
    },
)

ENGINE_ROUTES = (
    {
        "address": "$C2:956E",
        "name": "NewGame_SeedCharStatsAndTechs",
        "effect": (
            "MVN copies $0280 bytes from $CC:0000 to $7E:2600: seven "
            "$50-byte records plus the first $50 bytes of compatibility/"
            "tech state"
        ),
        "pc07_gate": (
            "natural record $7E:2830 receives compatibility state, not a "
            "record"
        ),
    },
    {
        "address": "$FD:B2DE",
        "name": "NewGame_InitCharacterData",
        "effect": (
            "attract/demo initialization calls the $0230-byte copy helper, "
            "then loops eight $50-byte destinations and overwrites +0B/+0E "
            "with $23, +0C with $80, and +03/+05/+07/+09 from a selected "
            "seven-row HP/MP block"
        ),
        "pc07_gate": (
            "the eighth iteration mutates $7E:2830 and reads beyond the "
            "selected seven-row HP/MP block"
        ),
    },
    {
        "address": "$FD:B33F",
        "name": "CopyCharInitData",
        "effect": "copies exactly $0230 bytes from $CC:0000 to $7E:2600",
        "pc07_gate": "does not provide an eighth record",
    },
    {
        "address": "$C2:8839",
        "name": "Menu_LoadCharRecordToBuf",
        "effect": "copies $50 bytes from $7E:2600 + id*$50 to $7E:9A90",
        "pc07_gate": (
            "ID $07 resolves to compatibility state; record +00 also drives "
            "the vanilla name/formula index"
        ),
    },
    {
        "address": "$C2:9137",
        "name": "Menu_CommitComputedStats",
        "effect": (
            "recomputes equipment stats, writes current HP +03, and copies "
            "eleven derived bytes to +36..40"
        ),
        "pc07_gate": "requires a valid natural record and item adapters",
    },
    {
        "address": "$C2:99B2",
        "name": "Menu_RecalcAllCharStats",
        "effect": "loads/recomputes only character IDs $00-$06",
        "pc07_gate": "hard-coded seven-character bound must be adapted",
    },
    {
        "address": "$FD:AE52",
        "name": "Battle_LoadPcRecordToWork",
        "effect": (
            "copies the full $50-byte live record to an $80-byte battle work "
            "record and zero-fills +50..7F"
        ),
        "pc07_gate": "ID $07 aliases compatibility state until relocation",
    },
    {
        "address": "$C1:B442",
        "name": "Battle_CommitPartyRecordsToLive",
        "effect": (
            "copies all first $50 battle-work bytes back to "
            "$7E:2600 + id*$50"
        ),
        "pc07_gate": (
            "ID $07 would overwrite compatibility state; contextual tail "
            "bytes are committed too"
        ),
    },
    {
        "address": "$C1:CF15",
        "name": "Battle_ReloadPartyCharInitData",
        "effect": (
            "reloads weapon, helmet, armor, and accessory descriptors for "
            "three party work records"
        ),
        "pc07_gate": "requires valid ID-$07 equipment source resolution",
    },
    {
        "address": "$C1:F630",
        "name": "Battle_LevelUp_RecomputeStats",
        "effect": (
            "uses record +00 to select a seven-byte stat-growth row and "
            "recomputes six stats from +2F..35 baselines; Speed is skipped"
        ),
        "pc07_gate": (
            "row $07 exists but is all zero and must not be treated as a "
            "finished growth definition"
        ),
    },
    {
        "address": "$C1:F871",
        "name": "Battle_ApplyHpMpGrowth",
        "effect": (
            "uses record +00 to select four (level ceiling, gain) pairs from "
            "each seven-row HP/MP table"
        ),
        "pc07_gate": (
            "ID $07 indexes past both table extents into following data"
        ),
    },
    {
        "address": "$C1:F7B9",
        "name": "Battle_LevelUpCheck",
        "effect": (
            "consumes +2B remaining EXP, increments +12, and reloads +2B "
            "from the shared 100-entry XP table"
        ),
        "pc07_gate": "record initialization must bind level, total EXP, and +2B",
    },
    {
        "address": "$C1:F39A",
        "name": "Battle_AwardTp",
        "effect": (
            "uses char*16 + learned_count*2 to read one of eight u16 TP "
            "thresholds; updates +2D and the u24 total at +16"
        ),
        "pc07_gate": "the table has only seven character rows",
    },
)


class AuditError(RuntimeError):
    """Raised when a pinned source, ROM, table, or schema invariant drifts."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _slice(data: ByteString, offset: int, length: int, label: str) -> bytes:
    if offset < 0 or length < 0 or offset + length > len(data):
        raise AuditError(
            f"{label}: slice {offset:#x}+{length:#x} outside input "
            f"length {len(data):#x}"
        )
    return bytes(data[offset : offset + length])


def _u16(data: ByteString, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise AuditError(f"u16 read outside input at {offset:#x}")
    return data[offset] | (data[offset + 1] << 8)


def _u24(data: ByteString, offset: int) -> int:
    if offset < 0 or offset + 3 > len(data):
        raise AuditError(f"u24 read outside input at {offset:#x}")
    return data[offset] | (data[offset + 1] << 8) | (data[offset + 2] << 16)


def _hex_byte(value: int) -> str:
    return f"${value:02X}"


def _hex_word(value: int) -> str:
    return f"${value:04X}"


def _assert_hash(data: bytes, expected: str, label: str) -> str:
    actual = _sha256(data)
    if actual != expected:
        raise AuditError(f"{label}: SHA-256 mismatch")
    return actual


def _read_disassembly_commit() -> str:
    git_dir = DISASSEMBLY_ROOT / ".git"
    head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    if head.startswith("ref: "):
        ref_name = head.removeprefix("ref: ")
        ref_path = git_dir.joinpath(*ref_name.split("/"))
        if ref_path.exists():
            return ref_path.read_text(encoding="utf-8").strip()
        packed = git_dir / "packed-refs"
        if packed.exists():
            for line in packed.read_text(encoding="utf-8").splitlines():
                if line and not line.startswith(("#", "^")):
                    commit, name = line.split(" ", 1)
                    if name == ref_name:
                        return commit
        raise AuditError(f"unable to resolve disassembly ref {ref_name}")
    return head


def validate_disassembly_sources() -> dict[str, Any]:
    commit = _read_disassembly_commit()
    if commit != PINNED_DISASSEMBLY_COMMIT:
        raise AuditError("ct_disassembly commit drift")

    rows: dict[str, Any] = {}
    for relative, expected_hash in PINNED_SOURCE_HASHES.items():
        path = DISASSEMBLY_ROOT / relative
        encoded = path.read_bytes()
        digest = _sha256(encoded)
        if digest != expected_hash:
            raise AuditError(f"{relative}: source hash drift")
        text = encoded.decode("utf-8")
        missing = [
            anchor for anchor in SOURCE_ANCHORS[relative] if anchor not in text
        ]
        if missing:
            raise AuditError(f"{relative}: missing source anchors: {missing}")
        rows[relative] = {
            "sha256": digest,
            "anchor_count": len(SOURCE_ANCHORS[relative]),
        }
    return {"commit": commit, "files": rows}


def validate_field_schema() -> dict[str, Any]:
    ownership: list[str | None] = [None] * PC_RECORD_SIZE
    for field in FIELD_SCHEMA:
        offset = int(field["offset"])
        size = int(field["size"])
        if offset < 0 or size <= 0 or offset + size > PC_RECORD_SIZE:
            raise AuditError(f"{field['name']}: invalid field extent")
        for byte_offset in range(offset, offset + size):
            if ownership[byte_offset] is not None:
                raise AuditError(
                    f"field overlap at +{byte_offset:02X}: "
                    f"{ownership[byte_offset]} and {field['name']}"
                )
            ownership[byte_offset] = str(field["name"])
    gaps = [offset for offset, owner in enumerate(ownership) if owner is None]
    if gaps:
        raise AuditError(f"field schema gaps: {gaps}")
    return {
        "record_size": PC_RECORD_SIZE,
        "field_count": len(FIELD_SCHEMA),
        "coverage": "$00-$4F",
        "unmapped_fields": [
            field["name"]
            for field in FIELD_SCHEMA
            if field.get("mapping_status") == "unmapped"
        ],
    }


def validate_canonical_rom(rom: bytes) -> dict[str, Any]:
    if len(rom) != CANONICAL_ROM_SIZE:
        raise AuditError(
            f"expected ROM size {CANONICAL_ROM_SIZE:#x}, got {len(rom):#x}"
        )
    sha1 = hashlib.sha1(rom).hexdigest()
    sha256 = _sha256(rom)
    if sha1 != CANONICAL_ROM_SHA1:
        raise AuditError("canonical ROM SHA-1 mismatch")
    if sha256 != CANONICAL_ROM_SHA256:
        raise AuditError("canonical ROM SHA-256 mismatch")
    return {"size": len(rom), "sha1": sha1, "sha256": sha256}


def decode_byte01(value: int) -> dict[str, Any]:
    if not 0 <= value <= 0xFF:
        raise AuditError(f"byte +01 outside u8 range: {value}")
    priority = (
        (0x80, 0, "slot_0_conventionally_lightning"),
        (0x40, 1, "slot_1_conventionally_shadow"),
        (0x20, 2, "slot_2_conventionally_water"),
        (0x10, 3, "slot_3_conventionally_fire"),
    )
    selected = next(
        (
            {"bit": _hex_byte(bit), "slot": slot, "label": label}
            for bit, slot, label in priority
            if value & bit
        ),
        None,
    )
    return {
        "value": _hex_byte(value),
        "selected_high_nibble": selected,
        "low_nibble": _hex_byte(value & 0x0F),
        "low_nibble_status": "unmapped",
    }


def expected_high_first_mask(learned_count: int) -> int:
    if not 0 <= learned_count <= 8:
        raise AuditError(f"learned count outside 0..8: {learned_count}")
    if learned_count == 0:
        return 0
    return (0xFF << (8 - learned_count)) & 0xFF


def project_level_stats(
    record: ByteString, growth_row: ByteString
) -> dict[str, dict[str, Any]]:
    if len(record) != PC_RECORD_SIZE:
        raise AuditError(
            f"record projection expected {PC_RECORD_SIZE:#x} bytes, "
            f"got {len(record):#x}"
        )
    if len(growth_row) != STAT_GROWTH_ROW_SIZE:
        raise AuditError(
            f"growth projection expected {STAT_GROWTH_ROW_SIZE} bytes, "
            f"got {len(growth_row)}"
        )
    level = record[0x12]
    if level < 1:
        raise AuditError("level must be at least 1 for stat projection")

    projected: dict[str, dict[str, Any]] = {}
    for layout in STAT_GROWTH_LAYOUT:
        name = str(layout["name"])
        base_offset = int(layout["base_offset"])
        baseline_offset = int(layout["baseline_offset"])
        growth_index = int(layout["growth_index"])
        recomputed = bool(layout["recomputed"])
        actual = record[base_offset]
        if recomputed:
            value = min(
                99,
                record[baseline_offset]
                + growth_row[growth_index] * (level - 1) // 100,
            )
            formula = "baseline + floor(growth*(level-1)/100), capped 99"
        else:
            value = min(actual, 50)
            formula = "not growth-recomputed; retained then capped at 50"
        projected[name] = {
            "actual": actual,
            "projected": value,
            "delta": actual - value,
            "recomputed": recomputed,
            "formula": formula,
            "growth_index": growth_index,
            "base_offset": f"+{base_offset:02X}",
            "baseline_offset": f"+{baseline_offset:02X}",
        }
    return projected


def _validate_pinned_table(
    rom: ByteString,
    offset: int,
    length: int,
    expected_hash: str,
    label: str,
    check_hashes: bool,
) -> tuple[bytes, str]:
    data = _slice(rom, offset, length, label)
    digest = _sha256(data)
    if check_hashes and digest != expected_hash:
        raise AuditError(f"{label}: SHA-256 mismatch")
    return data, digest


def audit_combo_learn_group_index(
    rom: ByteString, *, check_hashes: bool = True
) -> dict[str, Any]:
    """Bound the post-battle $283E + group-index read/modify/write.

    The canonical code hashes pin the scan and access instructions. This
    function emits only structural metadata and hashes, never the table
    records themselves.
    """

    table, table_digest = _validate_pinned_table(
        rom,
        DUAL_TECH_REQ_FILE,
        DUAL_TECH_REQ_LENGTH,
        DUAL_TECH_REQ_SHA256,
        "dual-tech requirement index",
        check_hashes,
    )
    _scan_code, scan_digest = _validate_pinned_table(
        rom,
        COMBO_LEARN_SCAN_CODE_FILE,
        COMBO_LEARN_SCAN_CODE_LENGTH,
        COMBO_LEARN_SCAN_CODE_SHA256,
        "combo-learn index scan code",
        check_hashes,
    )
    _access_code, access_digest = _validate_pinned_table(
        rom,
        COMBO_LEARN_ACCESS_CODE_FILE,
        COMBO_LEARN_ACCESS_CODE_LENGTH,
        COMBO_LEARN_ACCESS_CODE_SHA256,
        "combo-learn indexed access code",
        check_hashes,
    )

    records = tuple(
        table[
            index * DUAL_TECH_REQ_RECORD_SIZE :
            (index + 1) * DUAL_TECH_REQ_RECORD_SIZE
        ]
        for index in range(DUAL_TECH_REQ_RECORD_COUNT)
    )
    sentinel_indices = tuple(
        index for index, record in enumerate(records) if record[0] == 0xFF
    )
    if sentinel_indices != (DUAL_TECH_REQ_RECORD_COUNT - 1,):
        raise AuditError(
            "dual-tech requirement sentinel is not one exact final record"
        )

    live_records = records[: sentinel_indices[0]]
    if not live_records:
        raise AuditError("dual-tech requirement index has no live records")
    if any(record[1] == 0xFF for record in live_records):
        raise AuditError("a live combo group uses the sentinel group ID")

    dual_count = 15
    expected_group_ids = (
        *range(0x39, 0x66, 3),
        *range(0x66, 0x70),
    )
    actual_group_ids = tuple(record[1] for record in live_records)
    if actual_group_ids != expected_group_ids:
        raise AuditError("combo group ID sequence drifted")

    expected_widths = (3,) * dual_count + (1,) * (
        len(live_records) - dual_count
    )
    actual_widths = tuple(record[2] for record in live_records)
    if actual_widths != expected_widths:
        raise AuditError("combo requirement widths drifted")

    participant_masks = tuple(record[0] for record in live_records)
    if (
        any(mask == 0 for mask in participant_masks)
        or len(set(participant_masks)) != len(participant_masks)
    ):
        raise AuditError("combo participant masks are not unique nonzero keys")
    if any(mask & 0x01 for mask in participant_masks):
        raise AuditError("a vanilla combo group unexpectedly includes PC $07")

    for record in live_records:
        requirement_pointer = _u16(record, 3)
        requirement_end = requirement_pointer + record[2] * 3
        if not (
            COMBO_REQ_LISTS_SNES_START
            <= requirement_pointer
            < requirement_end
            <= COMBO_REQ_LISTS_SNES_END_EXCLUSIVE
        ):
            raise AuditError(
                "combo requirement pointer leaves the pinned list extent"
            )

    maximum_live_index = len(live_records) - 1
    maximum_wram_address = COMBO_LEARN_WRAM_BASE + maximum_live_index
    if maximum_wram_address != ROCK_LEARNED_FLAGS_WRAM_START - 1:
        raise AuditError(
            "combo-learn maximum no longer stops before rock flags"
        )

    return {
        "table_address": "$CC:2778-$CC:27F9",
        "table_sha256": table_digest,
        "record_size": DUAL_TECH_REQ_RECORD_SIZE,
        "record_count_including_sentinel": DUAL_TECH_REQ_RECORD_COUNT,
        "live_group_count": len(live_records),
        "dual_group_count": dual_count,
        "triple_group_count": len(live_records) - dual_count,
        "sentinel_record_index": sentinel_indices[0],
        "counter": "$7E:B2D2, reset at $C1:F265",
        "pointer_formula": "$7E:283E + live record index at $C1:F29C",
        "maximum_live_index": maximum_live_index,
        "maximum_effective_wram_address": (
            f"$7E:{maximum_wram_address:04X}"
        ),
        "relocated_effective_wram_range": "$7E:2CAE-$7E:2CC6",
        "rock_flags_start": f"$7E:{ROCK_LEARNED_FLAGS_WRAM_START:04X}",
        "relocated_rock_flags_start": "$7E:2CC7",
        "rock_flags_reachable_by_this_path": False,
        "pc07_participant_group_count": 0,
        "read_modify_write": "$C1:F5C1/$C1:F5C7",
        "scan_code_sha256": scan_digest,
        "access_code_sha256": access_digest,
        "evidence": "verified-static",
    }


def audit_record_tables(
    rom: ByteString, *, check_hashes: bool = True
) -> dict[str, Any]:
    char_data, char_digest = _validate_pinned_table(
        rom,
        CHAR_INIT_FILE,
        CHAR_INIT_LENGTH,
        CHAR_INIT_SHA256,
        "CharInitData",
        check_hashes,
    )
    compatibility, compatibility_digest = _validate_pinned_table(
        rom,
        COMPATIBILITY_FILE,
        COMPATIBILITY_LENGTH,
        COMPATIBILITY_SHA256,
        "compatibility span",
        check_hashes,
    )
    hp_growth, hp_digest = _validate_pinned_table(
        rom,
        HP_GROWTH_FILE,
        HP_GROWTH_LENGTH,
        HP_GROWTH_SHA256,
        "HP growth table",
        check_hashes,
    )
    mp_growth, mp_digest = _validate_pinned_table(
        rom,
        MP_GROWTH_FILE,
        MP_GROWTH_LENGTH,
        MP_GROWTH_SHA256,
        "MP growth table",
        check_hashes,
    )
    stat_growth, stat_digest = _validate_pinned_table(
        rom,
        STAT_GROWTH_FILE,
        STAT_GROWTH_LENGTH,
        STAT_GROWTH_SHA256,
        "stat growth table",
        check_hashes,
    )
    xp_data, xp_digest = _validate_pinned_table(
        rom,
        XP_TO_NEXT_FILE,
        XP_TO_NEXT_LENGTH,
        XP_TO_NEXT_SHA256,
        "XP-to-next table",
        check_hashes,
    )
    tp_data, tp_digest = _validate_pinned_table(
        rom,
        TP_TO_NEXT_FILE,
        TP_TO_NEXT_LENGTH,
        TP_TO_NEXT_SHA256,
        "TP-to-next table",
        check_hashes,
    )
    fd_pointer_data, fd_pointer_digest = _validate_pinned_table(
        rom,
        FD_HP_MP_POINTER_FILE,
        FD_HP_MP_POINTER_LENGTH,
        FD_HP_MP_POINTER_SHA256,
        "FD HP/MP pointer table",
        check_hashes,
    )
    combo_learn_group_index = audit_combo_learn_group_index(
        rom, check_hashes=check_hashes
    )

    records = [
        char_data[index * PC_RECORD_SIZE : (index + 1) * PC_RECORD_SIZE]
        for index in range(PC_RECORD_COUNT)
    ]
    if tuple(record[0] for record in records) != tuple(range(PC_RECORD_COUNT)):
        raise AuditError("record +00 logical identities are not 0..6")
    if tuple(record[1] for record in records) != EXPECTED_BYTE01:
        raise AuditError("record +01 canonical bitfields drifted")
    if any(record[2] != EXPECTED_BYTE02 for record in records):
        raise AuditError("record +02 canonical seed is not uniformly $80")
    if any(record[3:5] != record[5:7] for record in records):
        raise AuditError("a template current HP does not equal base max HP")
    if any(record[7:9] != record[9:11] for record in records):
        raise AuditError("a template current MP does not equal base max MP")
    if any(record[0x19:0x27] != bytes(0x0E) for record in records):
        raise AuditError("template +19..26 zero invariant drifted")
    if any(record[0x31] != 0 for record in records):
        raise AuditError("template +31 speed-baseline placeholder is not zero")
    if any(record[0x36:0x50] != bytes((0xFF,)) * 0x1A for record in records):
        raise AuditError("template +36..4F FF sentinel invariant drifted")

    start_counts = tuple(
        _slice(
            rom,
            START_TECH_COUNT_FILE,
            PC_RECORD_COUNT,
            "starting-tech counts",
        )
    )
    start_masks = tuple(
        _slice(
            rom,
            START_TECH_MASK_FILE,
            PC_RECORD_COUNT,
            "starting-tech masks",
        )
    )
    if start_counts != EXPECTED_START_TECH_COUNTS:
        raise AuditError("starting-tech count vector drifted")
    if start_masks != EXPECTED_START_TECH_MASKS:
        raise AuditError("starting-tech mask vector drifted")
    if any(
        mask != expected_high_first_mask(count)
        for count, mask in zip(start_counts, start_masks, strict=True)
    ):
        raise AuditError("starting-tech masks are not high-bit-first")

    if stat_growth[7 * STAT_GROWTH_ROW_SIZE :] != bytes(
        STAT_GROWTH_ROW_SIZE
    ):
        raise AuditError("stat-growth row 7 is no longer the canonical zero row")

    xp_values = tuple(
        _u16(xp_data, index * 2) for index in range(XP_TO_NEXT_COUNT)
    )
    xp_total_exceptions: list[dict[str, Any]] = []
    xp_next_exceptions: list[dict[str, Any]] = []
    stat_projection_exceptions: list[dict[str, Any]] = []
    tp_binding_rows: list[dict[str, Any]] = []

    for pc_id, (pc_name, record) in enumerate(
        zip(PC_NAMES, records, strict=True)
    ):
        level = record[0x12]
        total_xp = _u24(record, 0x13)
        expected_total_xp = sum(xp_values[:level])
        if total_xp != expected_total_xp:
            xp_total_exceptions.append(
                {
                    "pc_id": pc_id,
                    "pc": pc_name,
                    "level": level,
                    "actual": total_xp,
                    "shared_curve_projection": expected_total_xp,
                }
            )

        xp_to_next = _u16(record, 0x2B)
        expected_xp_to_next = xp_values[level]
        if xp_to_next != expected_xp_to_next:
            matching_indices = [
                index
                for index, value in enumerate(xp_values)
                if value == xp_to_next
            ]
            xp_next_exceptions.append(
                {
                    "pc_id": pc_id,
                    "pc": pc_name,
                    "level": level,
                    "actual": xp_to_next,
                    "shared_curve_at_level": expected_xp_to_next,
                    "matching_table_indices": matching_indices,
                }
            )

        learned_count = start_counts[pc_id]
        if learned_count >= 8:
            raise AuditError(f"{pc_name}: learned count cannot index TP row")
        tp_threshold = _u16(
            tp_data, pc_id * TP_TO_NEXT_ROW_SIZE + learned_count * 2
        )
        record_tp_to_next = _u16(record, 0x2D)
        if record_tp_to_next != tp_threshold:
            raise AuditError(
                f"{pc_name}: +2D does not match TP row at learned count"
            )
        tp_binding_rows.append(
            {
                "pc_id": pc_id,
                "pc": pc_name,
                "learned_count": learned_count,
                "learned_mask": _hex_byte(start_masks[pc_id]),
                "record_plus_2d_matches_threshold": True,
            }
        )

        growth_row = stat_growth[
            pc_id
            * STAT_GROWTH_ROW_SIZE : (pc_id + 1)
            * STAT_GROWTH_ROW_SIZE
        ]
        projection = project_level_stats(record, growth_row)
        for stat_name, values in projection.items():
            if values["recomputed"] and values["delta"] != 0:
                stat_projection_exceptions.append(
                    {
                        "pc_id": pc_id,
                        "pc": pc_name,
                        "stat": stat_name,
                        "actual": values["actual"],
                        "formula_projection": values["projected"],
                        "delta": values["delta"],
                    }
                )

    if xp_total_exceptions:
        raise AuditError(
            "canonical total EXP no longer matches the shared cumulative curve"
        )

    pointer_words = tuple(
        _u16(fd_pointer_data, index * 2)
        for index in range(FD_HP_MP_POINTER_LENGTH // 2)
    )
    if pointer_words != EXPECTED_FD_HP_MP_POINTER_WORDS:
        raise AuditError("FD HP/MP pointer words drifted")
    if (
        FD_HP_MP_POINTER_FILE + FD_HP_MP_POINTER_LENGTH
        != FD_HP_MP_BLOCKS[0][0]
    ):
        raise AuditError(
            "FD HP/MP pointer table does not end at the first data block"
        )
    expected_block_offsets = tuple(
        0x3D0000 + pointer for pointer in pointer_words
    )
    actual_block_offsets = tuple(
        file_offset for file_offset, _expected_hash in FD_HP_MP_BLOCKS
    )
    if actual_block_offsets != expected_block_offsets:
        raise AuditError("FD HP/MP block starts do not match pointer words")
    if (
        FD_HP_MP_BLOCKS[-1][0] + PC_RECORD_COUNT * 8
        != FD_HP_MP_DATA_END_FILE
    ):
        raise AuditError("FD HP/MP blocks do not end at the pinned data boundary")
    fd_blocks: list[dict[str, Any]] = []
    for file_offset, expected_hash in FD_HP_MP_BLOCKS:
        block = _slice(
            rom, file_offset, PC_RECORD_COUNT * 8, "FD HP/MP block"
        )
        digest = _sha256(block)
        if check_hashes and digest != expected_hash:
            raise AuditError(
                f"FD HP/MP block at {file_offset:#x}: SHA-256 mismatch"
            )
        fd_blocks.append(
            {
                "file_offset": f"0x{file_offset:06X}",
                "row_count": 7,
                "row_size": 8,
                "sha256": digest,
            }
        )

    return {
        "char_init": {
            "address": "$CC:0000-$CC:022F",
            "file_offset": "0x0C0000",
            "record_count": PC_RECORD_COUNT,
            "record_size": PC_RECORD_SIZE,
            "sha256": char_digest,
            "canonical_invariants": {
                "logical_identity_sequence": "$00-$06",
                "byte_02_seed": "$80 for every template",
                "current_hp_equals_base_max_hp": True,
                "current_mp_equals_base_max_mp": True,
                "plus_19_through_26": "$00 for every template",
                "plus_31": "$00 for every template",
                "plus_36_through_4f": (
                    "$FF initial sentinels for every template"
                ),
            },
        },
        "byte_01": {
            "canonical_by_pc": {
                pc_name: decode_byte01(record[1])
                for pc_name, record in zip(PC_NAMES, records, strict=True)
            },
            "selector_priority": "$80, $40, $20, $10",
            "proved_consumers": ("$FD:B3FE", "$C1:E440"),
            "low_nibble_status": "unmapped",
            "schala_constraint": (
                "Shadow selects high bit $40; the low nibble is unresolved, "
                "so copying Magus's complete $42 is not approved"
            ),
        },
        "byte_02": {
            "canonical_seed_set": ("$80",),
            "mapped_bits": {
                "$01": "near-fatal; recomputed from current/base max HP",
                "$10": (
                    "all single techs learned; suppresses further TP learning"
                ),
            },
            "unmapped_bits": ("$02", "$04", "$08", "$20", "$40", "$80"),
            "warning": (
                "uniform template seed $80 is an observed invariant, not a "
                "proved semantic default for a new PC"
            ),
        },
        "compatibility_collision": {
            "rom_address": "$CC:0230-$CC:027F",
            "live_address": "$7E:2830-$7E:287F",
            "sha256": compatibility_digest,
            "first_structures": {
                "$CC:0230-$CC:0236": "seven learned-single counts",
                "$CC:0237-$CC:023D": "seven learned-single masks",
            },
            "starting_tech_state": {
                pc_name: {
                    "learned_count": start_counts[index],
                    "learned_mask": _hex_byte(start_masks[index]),
                }
                for index, pc_name in enumerate(PC_NAMES)
            },
            "record_07_status": "not a vanilla PC record",
        },
        "growth_tables": {
            "hp": {
                "address": "$CC:258A-$CC:25C1",
                "rows": 7,
                "row_size": 8,
                "sha256": hp_digest,
                "pc07": "out-of-bounds into MP growth data",
            },
            "mp": {
                "address": "$CC:25C2-$CC:25F9",
                "rows": 7,
                "row_size": 8,
                "sha256": mp_digest,
                "pc07": "out-of-bounds into stat growth data",
            },
            "stat": {
                "address": "$CC:25FA-$CC:2631",
                "rows": 8,
                "row_size": 7,
                "sha256": stat_digest,
                "engine_order": (
                    "power",
                    "stamina",
                    "speed_ignored",
                    "hit",
                    "evade",
                    "magic",
                    "magic_defense",
                ),
                "pc07": "row exists but is all zero; not a finished definition",
                "join_template_projection_exceptions": (
                    stat_projection_exceptions
                ),
                "interpretation": (
                    "vanilla join templates include deliberate overrides; "
                    "baselines/growth are future level-up inputs, not a rule "
                    "that every join template must already equal"
                ),
            },
        },
        "experience": {
            "table_address": "$CC:2632-$CC:26F9",
            "entry_count": XP_TO_NEXT_COUNT,
            "entry_size": 2,
            "sha256": xp_digest,
            "total_xp_matches_cumulative_curve_for_all_templates": True,
            "xp_to_next_exceptions": xp_next_exceptions,
        },
        "tech_points": {
            "table_address": "$CC:26FA-$CC:2769",
            "row_count": TP_TO_NEXT_COUNT,
            "row_size_bytes": TP_TO_NEXT_ROW_SIZE,
            "u16_thresholds_per_row": 8,
            "sha256": tp_digest,
            "template_bindings": tp_binding_rows,
            "pc07": "no row; ID $07 enters following table data",
        },
        "combo_learn_group_index": combo_learn_group_index,
        "fd_attract_hp_mp_overlay": {
            "pointer_table_address": "$FD:B99C-$FD:B9A1",
            "pointer_count": len(pointer_words),
            "pointer_table_sha256": fd_pointer_digest,
            "pointer_words": tuple(_hex_word(value) for value in pointer_words),
            "data_extent": "$FD:B9A2-$FD:BA49",
            "bounded_seven_row_blocks": fd_blocks,
            "loop_bound": "eight destinations through Y=$027F",
            "pc07": (
                "the eighth iteration reads eight bytes past each bounded "
                "seven-row block and writes record-shaped fields into "
                "$7E:2830-$7E:287F"
            ),
        },
    }


def audit(rom_path: pathlib.Path) -> dict[str, Any]:
    rom = rom_path.read_bytes()
    return {
        "schema_version": 1,
        "evidence": "verified-static",
        "status": "audit_only_no_pc07_record_installed",
        "copyright_boundary": (
            "semantic metadata only; no raw character records, ROM slices, "
            "graphics, text, saves, states, or patches emitted"
        ),
        "rom": validate_canonical_rom(rom),
        "disassembly": validate_disassembly_sources(),
        "field_schema_validation": validate_field_schema(),
        "field_schema": FIELD_SCHEMA,
        "record_and_tables": audit_record_tables(rom),
        "engine_routes": ENGINE_ROUTES,
        "pc07_activation_gates": (
            "relocate and prove the complete $7E:2830-$7E:287F compatibility "
            "block before using the natural record",
            "author a complete original $50-byte PC record; do not serialize "
            "the separate $48-byte progression descriptor as a vanilla record",
            "resolve +01 low nibble and +02 bit7 semantics before final seed",
            "add bounded ID-$07 HP, MP, stat, TP, equipment, menu, battle, "
            "save/load, New Game+, attract/demo, erase, and reset adapters",
            "recompute the contextual +36..4F tail; do not treat template FF "
            "sentinels or battle residue as durable authoring data",
        ),
        "reproduction": {
            "command": (
                "python tools/audit_pc_init_record_schema.py "
                '--rom "private/input/rom_archive/Chrono Trigger (USA).sfc"'
            ),
            "focused_tests": (
                "python tests/test_pc_init_record_schema_audit.py -v"
            ),
        },
    }


def _write_report(path: pathlib.Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rom",
        required=True,
        type=pathlib.Path,
        help="headerless Chrono Trigger US Rev0 ROM",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        help="optional metadata-only JSON report path",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="emit compact JSON instead of indented JSON",
    )
    args = parser.parse_args()

    report = audit(args.rom)
    if args.output is not None:
        _write_report(args.output, report)
    print(
        json.dumps(
            report,
            indent=None if args.compact else 2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
