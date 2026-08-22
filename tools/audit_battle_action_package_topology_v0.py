#!/usr/bin/env python3
"""Audit primary battle action-package topology without decoding scripts.

The auditor accepts only the pinned headerless Chrono Trigger US Rev0 ROM,
reads it without mutation, and prints a closed metadata-only JSON report.  It
follows declared typed selector contexts through five physical package
resolvers, parses only targets selected by those sources, and inventories the
two-mask descriptor geometry plus bank-qualified script entrypoints.  Named
player commands and fixed internal type-2 animation-config indices remain
separate namespaces.

This is deliberately not a battle-animation command decoder.  It never emits
ROM bytes, table payloads, masks, pointer lists, script streams, saves, states,
traces, patches, or an output file.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
import dataclasses
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Final


ROOT: Final = Path(__file__).resolve().parents[1]
REFERENCE_PATH: Final = (
    ROOT / "references" / "battle_action_package_topology_v0.json"
)

REFERENCE_SIZE: Final = 23_353
REFERENCE_SHA256: Final = (
    "e6e3c23fd86927e1fa443cb46e67aed1"
    "00693bb7c0dc14f5c1dce01b7a6419b7"
)

CANONICAL_ROM_SIZE: Final = 0x400000
CANONICAL_ROM_SHA1: Final = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_ROM_SHA256: Final = (
    "06d1c2b06b716052c5596aaa0c2e5632"
    "a027fee1a9a28439e509f813c30829a9"
)

SCHEMA: Final = "project-epoch-battle-action-package-topology-v0"
REFERENCE_SCHEMA: Final = (
    "project-epoch-battle-action-package-topology-contract-v0"
)
AUDITOR_VERSION: Final = "battle-action-package-topology-v0"
STATUS: Final = (
    "pass-metadata-only-declared-package-topology-with-"
    "command-stream-decode-unresolved"
)
DISASSEMBLY_COMMIT: Final = (
    "eeae27acdb6565e96d1d796a3d60792c250c0aa1"
)


class BattlePackageTopologyAuditError(RuntimeError):
    """The canonical input, topology, or source contract drifted."""


@dataclasses.dataclass(frozen=True)
class SpanSpec:
    name: str
    label: str
    start: int
    end_exclusive: int
    expected_sha256: str


@dataclasses.dataclass(frozen=True)
class TableSpec(SpanSpec):
    entry_count: int
    entry_width: int
    role: str


@dataclasses.dataclass(frozen=True)
class RouteSpec:
    name: str
    package_bank: int
    pointer_table: str
    allowed_offset_start: int
    allowed_offset_end_exclusive: int
    context_kind: str


@dataclasses.dataclass(frozen=True)
class DescriptorEntry:
    branch: int
    owner_slot: int
    script_offset: int


@dataclasses.dataclass(frozen=True)
class PackageDescriptor:
    bank: int
    root_offset: int
    end_offset_exclusive: int
    mask0: int
    mask1: int
    entries: tuple[DescriptorEntry, ...]


MACHINE_SPANS: Final = (
    SpanSpec(
        "action_type_dispatch",
        "BattleAnim_LoadActionConfig",
        0xC14310,
        0xC1432C,
        "797fef4227ddc1fdf7225d7e39bb52d5"
        "c9cb9e24ebe4d57b67122aa3db727e37",
    ),
    SpanSpec(
        "pc_normal_attack_loader",
        "action type 1, actor slot 0-2",
        0xC1432C,
        0xC14497,
        "a318e720116100403f7e323156ecc9da3"
        "e8eed95c896b1d9cfc31eae22cd7286",
    ),
    SpanSpec(
        "enemy_attack_loader",
        "action type 1, actor slot 3+",
        0xC14497,
        0xC145A0,
        "f3b3980e6b9151c43ce0eee8e896d219"
        "4d7dad19b7ca7fbfb16d23349dade9cc",
    ),
    SpanSpec(
        "pc_action_type_2_loader",
        "action type 2, actor slot 0-2; raw physical domain is broader than named Tech actions",
        0xC145A0,
        0xC14682,
        "6d4ea34c8fb3a368bab2fcb2dcf9c5f2"
        "db258aa2f11c40eb1d0abef090df4edd",
    ),
    SpanSpec(
        "enemy_tech_loader",
        "action type 2, actor slot 3+",
        0xC14682,
        0xC1475B,
        "97c08bd46ac853553af292435ef258961"
        "3106392b2142adb9d312512d57f3888",
    ),
    SpanSpec(
        "item_loader",
        "action type 3",
        0xC1475B,
        0xC14833,
        "0eddc1f2e801fd1690e658e49b3e472a"
        "7f117d9ec3089fe13022569fa5dfa790",
    ),
    SpanSpec(
        "battle_script_active_slot_runner",
        "active battle script slot runner",
        0xC14BBE,
        0xC14C9E,
        "d65a749d8401c79fae00a9ba24b85ea0"
        "b1e83246a06448735339834e0747945e",
    ),
    SpanSpec(
        "battle_script_dispatcher",
        "primary script dispatch loop",
        0xC14C9E,
        0xC14CF0,
        "f9eee9ad39ebab931c5a65d55bbff455"
        "85670770b528be2f10d65e9cc7dab561",
    ),
    SpanSpec(
        "battle_script_subscript_handlers",
        "commands 1E and 1F",
        0xC156CC,
        0xC15714,
        "a22f0cfecd41b57e14a4b2e796d581e6"
        "83520734f92a8b55a66e36a6062f9575",
    ),
    SpanSpec(
        "battle_script_pointer_advance",
        "script pointer advance helper",
        0xC175BB,
        0xC175CC,
        "81ec99810c0832f34277d117410919282"
        "e14891d51bb3869533e60ae3ef97142",
    ),
    SpanSpec(
        "action_type_target_table",
        "BattleAnim_ActionTypeTable",
        0xC17A63,
        0xC17A6B,
        "e5a449366a0a43d8946ada789564a454"
        "09e824c2e88b9603ceafaf6b0239ce47",
    ),
    SpanSpec(
        "pc_internal_type2_79_helper_call",
        "fixed internal type-2 config 79 helper call",
        0xC1820D,
        0xC18212,
        "908ff818be090855914b5a3b89d03289"
        "08fbaf5942d1b8ede8f08ccfab6d72f3",
    ),
    SpanSpec(
        "pc_internal_type2_7f_helper_call_a",
        "first fixed internal type-2 config 7F helper call",
        0xC18943,
        0xC18948,
        "133f281f241cdb04c841f97f1f82262"
        "f4e9cad29d9d6563f2ea3a45345b6999a",
    ),
    SpanSpec(
        "pc_internal_type2_helper",
        "store caller A to AE93, force actor 00 and action type 02, commit",
        0xC1895B,
        0xC18975,
        "fabede9285afc31871e7fae534c88ea2"
        "48a1ab891910532f79637aefe6d48110",
    ),
    SpanSpec(
        "pc_internal_type2_7f_helper_call_b",
        "second fixed internal type-2 config 7F helper call",
        0xC18BAF,
        0xC18BB4,
        "133f281f241cdb04c841f97f1f82262"
        "f4e9cad29d9d6563f2ea3a45345b6999a",
    ),
    SpanSpec(
        "pc_internal_type2_7a_producer",
        "fixed actor-00 type-2 config 7A producer",
        0xC1B35D,
        0xC1B379,
        "9a952e8aa83a6496e6f24319776d7c8"
        "d96700b39ca2fc7ce3179f4c54d4fc19f",
    ),
    SpanSpec(
        "pc_dynamic_type2_prepare_writer",
        "dynamic queued player type-2 AE93 writer before action prep",
        0xC1BB93,
        0xC1BBB1,
        "34c185445b7a41e76da651e896e92853"
        "fefbe57f456382742cc32030ec4b7581",
    ),
    SpanSpec(
        "pc_dynamic_type2_commit_writer",
        "dynamic queued player type-2 AE93 writer before commit",
        0xC1BBE1,
        0xC1BBF6,
        "9f669982a80dfee2b59765d2a4007c60"
        "0de86c1fc7a09a41be3e234bcdceb468",
    ),
    SpanSpec(
        "pc_internal_type2_7b_7d_producer",
        "actor-below-03 fixed type-2 configs 7B, 7C, and 7D producer",
        0xC1C659,
        0xC1C6A6,
        "5a70ac2b31895c08b450474f7ee94d5"
        "4221e829c95f88847b5bfecabf22db888",
    ),
    SpanSpec(
        "battle_script_command_table",
        "219-word command dispatch table",
        0xC17A6B,
        0xC17C21,
        "59145c787a5a5c57c59de7992ec0e17d"
        "5c6a64f32ef9e1e3273d174f90e8d995",
    ),
)


TABLE_SPECS: Final = (
    TableSpec(
        "pc_normal_attack_selector_families",
        "three logical-PC selector families",
        0xCD4000,
        0xCD4015,
        "89372c122381484720d5abfc94e040a2"
        "7089e31578a1a0bbb29cd85566167ff9",
        21,
        1,
        "selector_source",
    ),
    TableSpec(
        "pc_action_configs",
        "PC action animation configs",
        0xCD45A6,
        0xCD4926,
        "2cbcd73e9b5ef64d99da2f7fe97208f"
        "b8cad245a9c8b148b52088ad5625e74d6",
        128,
        7,
        "selector_source",
    ),
    TableSpec(
        "enemy_attack_param_zero_configs",
        "enemy Attack configs when AE93 equals zero",
        0xCD4926,
        0xCD4F26,
        "2358920a949949341abba4cdafb46055"
        "af6d5ca7e383a78d3643555a40642e5f",
        256,
        6,
        "selector_source",
    ),
    TableSpec(
        "enemy_attack_param_nonzero_configs",
        "alternate enemy Attack configs when AE93 is nonzero",
        0xCD4F26,
        0xCD5526,
        "c08f9286cee449497a2ba2daf38644af"
        "5180935f0129d4225e84cf49f4e97af4",
        256,
        6,
        "selector_source",
    ),
    TableSpec(
        "enemy_tech_configs",
        "enemy Tech action configs",
        0xCD5526,
        0xCD5C26,
        "4697ccdefb2f1d4e6d1672cb96c621e8"
        "37449f5f2bfa2de177f8653aa34c814d",
        256,
        7,
        "selector_source",
    ),
    TableSpec(
        "item_configs",
        "battle item configs",
        0xCD5C26,
        0xCD5EC6,
        "6e05fb15ead22437553b4464a2ebf739"
        "644bcdb07d49543873220e31b700bf2e",
        96,
        7,
        "selector_source",
    ),
    TableSpec(
        "pc_normal_attack_package_resolver",
        "PC normal Attack CE package roots",
        0xCD5EC6,
        0xCD5EF0,
        "f603c4f7413d2cfe48d7459687f51113"
        "3ebcfc8f5f0d1a31d5b11d89f3e63256",
        21,
        2,
        "package_resolver",
    ),
    TableSpec(
        "pc_action_package_resolver",
        "PC action CE package roots",
        0xCD5EF0,
        0xCD5FF0,
        "074a9bca7aaa630085654200634002e8f"
        "3c0f251a5c3874a5b1c1237d713a4d1",
        128,
        2,
        "package_resolver",
    ),
    TableSpec(
        "enemy_attack_package_resolver",
        "enemy Attack CD package roots",
        0xCD5FF0,
        0xCD61F0,
        "31010e7d9b8401a0a2c0309c050d245"
        "f432172f85ef2db91efbacf68822a4bd0",
        256,
        2,
        "package_resolver",
    ),
    TableSpec(
        "enemy_tech_package_resolver",
        "enemy Tech CD package roots",
        0xCD61F0,
        0xCD63F0,
        "f152afaf19caa9a13ad84215974dcb1a"
        "ab67a06fbac8c1de5518173614cf85a4",
        256,
        2,
        "package_resolver",
    ),
    TableSpec(
        "item_package_resolver",
        "battle item CE package roots",
        0xCD63F0,
        0xCD64B0,
        "c26ab54281a907a44000d863ee068fbd"
        "e7e9dc9ba44f478b474b998f0a171431",
        96,
        2,
        "package_resolver",
    ),
)


SELECTOR_VECTOR_HASHES: Final = {
    "pc_normal_attack_selector_families": (
        "89372c122381484720d5abfc94e040a2"
        "7089e31578a1a0bbb29cd85566167ff9"
    ),
    "pc_action_configs": (
        "1b90504f1f08c6a916c9e0eb886eab8"
        "063bfb3a8145770323baabd9b2cbfb235"
    ),
    "enemy_attack_param_zero_configs": (
        "861f5a31b4246fed9ce6d25ef3afe37"
        "f522ead1a272780c121985f04e51dc514"
    ),
    "enemy_attack_param_nonzero_configs": (
        "5ed835859ae1416c04ec6f1609594d92"
        "d11b1e8d75e14af221b9e87f96583af5"
    ),
    "enemy_tech_configs": (
        "84f67f85e534ad2ebbe57b2a685f2f7"
        "6ed3f7c5349f5e56a9a62ab0a31fa8742"
    ),
    "item_configs": (
        "5c3a326f70fa124b86cb8e67b5615358"
        "b813f00e2e8c395360a95e48a52ddd84"
    ),
}

PC_NAMED_SELECTOR_VECTOR_SHA256: Final = (
    "2b3e621028311a2ed5cf773d37e32309"
    "dc79504eed8e551a03298724ace79ba4"
)

PC_INTERNAL_TYPE2_CONTEXTS: Final = (
    ("helper_call", 0xC1820D, 0x79),
    ("helper_call", 0xC18943, 0x7F),
    ("helper_call", 0xC18BAF, 0x7F),
    ("direct_producer", 0xC1B365, 0x7A),
    ("direct_producer", 0xC1C689, 0x7D),
    ("direct_producer", 0xC1C697, 0x7C),
    ("direct_producer", 0xC1C69E, 0x7B),
)

PC_INTERNAL_TYPE2_HELPER_JSR_PCS: Final = (
    0xC1820F,
    0xC18945,
    0xC18BB1,
)

AE93_DIRECT_ABSOLUTE_STORE_PCS: Final = (
    0xC1895B,
    0xC19F3D,
    0xC1AD05,
    0xC1B367,
    0xC1BAB3,
    0xC1BAE6,
    0xC1BB20,
    0xC1BBAE,
    0xC1BBF3,
    0xC1C68B,
    0xC1C699,
    0xC1C6A0,
    0xC1D6BC,
    0xFDAA91,
)

AE93_DIRECT_ABSOLUTE_ZERO_PCS: Final = (
    0xC18D0A,
    0xC1BFB3,
)

AE92_ADJACENT_ABSOLUTE_STORE_PCS: Final = (
    0xC18963,
    0xC19F38,
    0xC1ACFF,
    0xC1B362,
    0xC1BADC,
    0xC1BB17,
    0xC1BBA6,
    0xC1BBED,
    0xC1BFDC,
    0xC1C676,
    0xFDAA8C,
)

AE93_PC_TYPE2_DIRECT_WRITER_PCS: Final = (
    0xC1895B,
    0xC1B367,
    0xC1BBAE,
    0xC1BBF3,
    0xC1C68B,
    0xC1C699,
    0xC1C6A0,
)

AE93_EXCLUDED_DIRECT_ADDRESS_CANDIDATES: Final = {
    "scratch_clear": (0xC18D0A, 0xC1BFB3),
    "enemy_or_ai_context": (0xC19F3D, 0xC1AD05, 0xFDAA91),
    "item_type03_or_precommit_scratch": (
        0xC1BAB3,
        0xC1BAE6,
        0xC1BB20,
    ),
    "explicit_non_type02_rewrite": (0xC1D6BC,),
}

EXPECTED_PC_INTERNAL_TYPE2_PACKAGE_SUMMARY: Final = (
    (0x79, 0x79, 0x81D0, 2, 1),
    (0x7A, 0x7A, 0x81E0, 4, 2),
    (0x7B, 0x7B, 0x821F, 2, 1),
    (0x7C, 0x7C, 0x8234, 4, 2),
    (0x7D, 0x7D, 0x8250, 6, 2),
    (0x7F, 0x7F, 0x8288, 2, 1),
)

AE93_DIRECT_WRITER_CENSUS_SIZE: Final = 464
AE93_DIRECT_WRITER_CENSUS_SHA256: Final = (
    "53ab189afdcd922a766c3df72ae3706a"
    "f5067270a9e1761d07764b54d8094a7b"
)

EXPECTED_RESOLVER_INVENTORY: Final = {
    "pc_normal_attack_package_resolver": {
        "selected_selector_count": 19,
        "ffff_value_count": 2,
        "non_ffff_unselected_count": 0,
    },
    "pc_action_package_resolver": {
        "selected_selector_count": 128,
        "ffff_value_count": 0,
        "non_ffff_unselected_count": 0,
    },
    "enemy_attack_package_resolver": {
        "selected_selector_count": 122,
        "ffff_value_count": 96,
        "non_ffff_unselected_count": 38,
    },
    "enemy_tech_package_resolver": {
        "selected_selector_count": 191,
        "ffff_value_count": 0,
        "non_ffff_unselected_count": 65,
    },
    "item_package_resolver": {
        "selected_selector_count": 32,
        "ffff_value_count": 64,
        "non_ffff_unselected_count": 0,
    },
}


ROUTE_SPECS: Final = {
    "pc_normal_attack": RouteSpec(
        "pc_normal_attack",
        0xCE,
        "pc_normal_attack_package_resolver",
        0x0000,
        0xE000,
        "logical_pc_and_attack_outcome_family",
    ),
    "pc_named_tech": RouteSpec(
        "pc_named_tech",
        0xCE,
        "pc_action_package_resolver",
        0x0000,
        0xE000,
        "named_action_id_01_74",
    ),
    "pc_internal_type2_config": RouteSpec(
        "pc_internal_type2_config",
        0xCE,
        "pc_action_package_resolver",
        0x0000,
        0xE000,
        "fixed_internal_type2_config_index_not_player_command_id",
    ),
    "pc_action_physical": RouteSpec(
        "pc_action_physical",
        0xCE,
        "pc_action_package_resolver",
        0x0000,
        0xE000,
        "all_128_encoded_config_rows_not_a_runtime_domain",
    ),
    "enemy_attack": RouteSpec(
        "enemy_attack",
        0xCD,
        "enemy_attack_package_resolver",
        0x6E0C,
        0x10000,
        "two_actor_config_branches",
    ),
    "enemy_tech": RouteSpec(
        "enemy_tech",
        0xCD,
        "enemy_tech_package_resolver",
        0x6E0C,
        0x10000,
        "all_256_encoded_config_rows_not_runtime_reachability",
    ),
    "battle_item": RouteSpec(
        "battle_item",
        0xCE,
        "item_package_resolver",
        0x0000,
        0xE000,
        "raw_item_ids_BC_DB_only",
    ),
}


EXPECTED_ACTION_TYPE_TARGETS: Final = (
    0x475A,
    0x432C,
    0x45A0,
    0x475B,
)


LIMITATIONS: Final = (
    "The census stops at bank-qualified script entrypoints and does not "
    "decode battle-animation command streams.",
    "Both descriptor masks are structural alternatives; the report does "
    "not claim that both execute simultaneously.",
    "Encoded config coverage is not runtime reachability, frequency, or "
    "story-state evidence.",
    "The command dispatcher, commands 1E/1F, and pointer-advance helper are "
    "hash-pinned only to bound the unresolved decoder problem.",
    "Auxiliary animation, graphics, effect, palette, and sound tables are "
    "outside this primary package-topology tranche.",
    "The seven pinned fixed PC type-2 producer contexts cover config indices "
    "79, 7A, 7B, 7C, 7D, and 7F.  None of those listed contexts uses row 7E, "
    "which remains unclaimed rather than free; adjacent-width, indexed, "
    "direct-page, indirect, pointer-based, block-move, DMA, and other "
    "battle-state writes are not proved absent.",
    "Descriptor owner-bit runtime roles are not classified by this topology "
    "report.",
)


NONCLAIMS: Final = (
    "No battle-animation opcode or operand census is complete.",
    "No CFG, call, subscript, conditional, fallthrough, lifetime, or "
    "execution-frequency proof is claimed.",
    "The encoded-operand AE93 opcode census is not a complete effective-write "
    "CFG and does not exclude adjacent-width, indexed-effective-address, "
    "direct-page, indirect, pointer-based, block-move, or DMA writes; AE92 "
    "overlap candidates are recorded without M-width claims.",
    "The whole-ROM opcode and helper-reference scans are raw byte-pattern "
    "candidate censuses, not instruction-start, DBR, call-graph, or runtime "
    "proof, and their result is not generalized beyond the pinned ROM.",
    "No script entrypoint is assigned a visual pose or gameplay semantic.",
    "No unselected resolver word, FFFF value, table gap, or adjacent byte is "
    "claimed free space.",
    "No logical PC 07, Schala action, Focus weapon, original battle frame, "
    "or playable eighth-character runtime binding is proved.",
    "No production hook, allocation, expanded-bank reader, ROM mutation, "
    "patch, save, state, trace, or emulator runtime evidence is produced.",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")


def _metadata_ledger_sha256(value: Any) -> str:
    return _sha256_bytes(_canonical_json_bytes(value))


def _hex2(value: int) -> str:
    return f"{value:02X}"


def _hex4(value: int) -> str:
    return f"{value:04X}"


def _hex6(value: int) -> str:
    return f"{value:06X}"


def snes_hirom_to_file(address: int) -> int:
    if type(address) is not int or not 0xC00000 <= address <= 0xFFFFFF:
        raise BattlePackageTopologyAuditError(
            f"unsupported HiROM address: {address!r}"
        )
    return address & 0x3FFFFF


def _slice_snes(rom: bytes, start: int, end_exclusive: int) -> bytes:
    start_offset = snes_hirom_to_file(start)
    end_offset = snes_hirom_to_file(end_exclusive)
    if end_offset <= start_offset:
        raise BattlePackageTopologyAuditError(
            "bounded SNES extent does not map forward"
        )
    result = rom[start_offset:end_offset]
    if len(result) != end_offset - start_offset:
        raise BattlePackageTopologyAuditError("bounded ROM read truncated")
    return result


def _find_pattern_snes_pcs(rom: bytes, pattern: bytes) -> list[int]:
    if not pattern:
        raise BattlePackageTopologyAuditError("empty opcode pattern")
    result: list[int] = []
    cursor = 0
    while True:
        offset = rom.find(pattern, cursor)
        if offset < 0:
            return result
        result.append(0xC00000 + offset)
        cursor = offset + 1


def _observe_ae93_encoded_operand_opcode_census(
    rom: bytes,
) -> dict[str, Any]:
    direct_word_opcodes = {
        "sta_abs": 0x8D,
        "sta_abs_x": 0x9D,
        "sta_abs_y": 0x99,
        "stx_abs": 0x8E,
        "sty_abs": 0x8C,
        "stz_abs": 0x9C,
        "stz_abs_x": 0x9E,
        "asl_abs": 0x0E,
        "asl_abs_x": 0x1E,
        "lsr_abs": 0x4E,
        "lsr_abs_x": 0x5E,
        "rol_abs": 0x2E,
        "rol_abs_x": 0x3E,
        "ror_abs": 0x6E,
        "ror_abs_x": 0x7E,
        "dec_abs": 0xCE,
        "dec_abs_x": 0xDE,
        "inc_abs": 0xEE,
        "inc_abs_x": 0xFE,
        "trb_abs": 0x1C,
        "tsb_abs": 0x0C,
    }
    candidates = {
        name: [
            _hex6(pc)
            for pc in _find_pattern_snes_pcs(
                rom,
                bytes((opcode, 0x93, 0xAE)),
            )
        ]
        for name, opcode in direct_word_opcodes.items()
    }
    candidates["sta_long"] = [
        _hex6(pc)
        for pc in _find_pattern_snes_pcs(
            rom,
            bytes((0x8F, 0x93, 0xAE, 0x7E)),
        )
    ]
    candidates["sta_long_x"] = [
        _hex6(pc)
        for pc in _find_pattern_snes_pcs(
            rom,
            bytes((0x9F, 0x93, 0xAE, 0x7E)),
        )
    ]
    expected = {name: [] for name in candidates}
    expected["sta_abs"] = [
        _hex6(pc) for pc in AE93_DIRECT_ABSOLUTE_STORE_PCS
    ]
    expected["stz_abs"] = [
        _hex6(pc) for pc in AE93_DIRECT_ABSOLUTE_ZERO_PCS
    ]
    if candidates != expected:
        raise BattlePackageTopologyAuditError(
            "direct-address AE93 opcode candidate census drifted"
        )
    canonical = _canonical_json_bytes(candidates)
    if (
        len(canonical) != AE93_DIRECT_WRITER_CENSUS_SIZE
        or _sha256_bytes(canonical) != AE93_DIRECT_WRITER_CENSUS_SHA256
    ):
        raise BattlePackageTopologyAuditError(
            "direct-address AE93 candidate ledger identity drifted"
        )
    adjacent_ae92_candidates = {
        name: [
            _hex6(pc)
            for pc in _find_pattern_snes_pcs(
                rom,
                bytes((opcode, 0x92, 0xAE)),
            )
        ]
        for name, opcode in direct_word_opcodes.items()
    }
    adjacent_ae92_candidates["sta_long"] = [
        _hex6(pc)
        for pc in _find_pattern_snes_pcs(
            rom,
            bytes((0x8F, 0x92, 0xAE, 0x7E)),
        )
    ]
    adjacent_ae92_candidates["sta_long_x"] = [
        _hex6(pc)
        for pc in _find_pattern_snes_pcs(
            rom,
            bytes((0x9F, 0x92, 0xAE, 0x7E)),
        )
    ]
    expected_adjacent_ae92 = {
        name: [] for name in adjacent_ae92_candidates
    }
    expected_adjacent_ae92["sta_abs"] = [
        _hex6(pc) for pc in AE92_ADJACENT_ABSOLUTE_STORE_PCS
    ]
    if adjacent_ae92_candidates != expected_adjacent_ae92:
        raise BattlePackageTopologyAuditError(
            "adjacent AE92 encoded-operand candidate census drifted"
        )
    helper_reference_candidates = {
        "jsr_abs": _find_pattern_snes_pcs(
            rom,
            bytes((0x20, 0x5B, 0x89)),
        ),
        "jmp_abs": _find_pattern_snes_pcs(
            rom,
            bytes((0x4C, 0x5B, 0x89)),
        ),
        "jsl_long_hirom_mirrors": sorted(
            pc
            for target_bank in (0x01, 0x41, 0x81, 0xC1)
            for pc in _find_pattern_snes_pcs(
                rom,
                bytes((0x22, 0x5B, 0x89, target_bank)),
            )
        ),
        "jml_long_hirom_mirrors": sorted(
            pc
            for target_bank in (0x01, 0x41, 0x81, 0xC1)
            for pc in _find_pattern_snes_pcs(
                rom,
                bytes((0x5C, 0x5B, 0x89, target_bank)),
            )
        ),
        "jsr_abs_x_indirect": _find_pattern_snes_pcs(
            rom,
            bytes((0xFC, 0x5B, 0x89)),
        ),
    }
    expected_helper_references = {
        "jsr_abs": list(PC_INTERNAL_TYPE2_HELPER_JSR_PCS),
        "jmp_abs": [],
        "jsl_long_hirom_mirrors": [],
        "jml_long_hirom_mirrors": [],
        "jsr_abs_x_indirect": [],
    }
    if helper_reference_candidates != expected_helper_references:
        raise BattlePackageTopologyAuditError(
            "fixed PC type-2 helper reference candidate census drifted"
        )
    accepted = set(AE93_PC_TYPE2_DIRECT_WRITER_PCS)
    excluded = {
        pc
        for pcs in AE93_EXCLUDED_DIRECT_ADDRESS_CANDIDATES.values()
        for pc in pcs
    }
    direct_candidates = set(AE93_DIRECT_ABSOLUTE_STORE_PCS) | set(
        AE93_DIRECT_ABSOLUTE_ZERO_PCS
    )
    if accepted & excluded or accepted | excluded != direct_candidates:
        raise BattlePackageTopologyAuditError(
            "direct-address AE93 candidate classification drifted"
        )
    return {
        "scope": (
            "whole canonical ROM raw byte-pattern candidates whose encoded "
            "operand is AE93, across direct absolute, absolute-indexed, and "
            "long-store opcode families"
        ),
        "candidate_ledger_size": len(canonical),
        "candidate_ledger_sha256": _sha256_bytes(canonical),
        "candidates": candidates,
        "adjacent_ae92_encoded_operand_candidates": (
            adjacent_ae92_candidates
        ),
        "adjacent_ae92_effective_write_to_ae93_proved": False,
        "fixed_helper_reference_candidates": {
            kind: [_hex6(pc) for pc in pcs]
            for kind, pcs in helper_reference_candidates.items()
        },
        "helper_entry_cfg_complete_claimed": False,
        "pc_type02_encoded_operand_ae93_writers": [
            _hex6(pc) for pc in AE93_PC_TYPE2_DIRECT_WRITER_PCS
        ],
        "excluded_encoded_operand_ae93_candidates": {
            category: [_hex6(pc) for pc in pcs]
            for category, pcs in (
                AE93_EXCLUDED_DIRECT_ADDRESS_CANDIDATES.items()
            )
        },
        "encoded_operand_ae93_candidate_partition_complete": True,
        "exclusion_classification_authority": (
            "canonical candidate addresses plus pinned interpretive "
            "disassembly; not runtime reachability"
        ),
        "fixed_pc_type02_contexts": [
            {
                "producer_kind": kind,
                "fixed_value_load_pc": _hex6(fixed_value_load_pc),
                "config_index": _hex2(config_index),
            }
            for (
                kind,
                fixed_value_load_pc,
                config_index,
            ) in PC_INTERNAL_TYPE2_CONTEXTS
        ],
        "fixed_pc_type02_config_indices": [
            _hex2(value)
            for value in sorted(
                {row[2] for row in PC_INTERNAL_TYPE2_CONTEXTS}
            )
        ],
        "config_index_7E_fixed_encoded_operand_writer_found": False,
        "all_effective_writes_to_ae93_claimed": False,
        "indirect_or_pointer_writer_absence_claimed": False,
        "complete_writer_cfg_claimed": False,
    }


def _u16le(value: bytes, offset: int) -> int:
    if offset < 0 or offset + 2 > len(value):
        raise BattlePackageTopologyAuditError(
            "little-endian word read truncated"
        )
    return value[offset] | (value[offset + 1] << 8)


def require_vanilla_pc_normal_attack_id(logical_pc_id: int) -> int:
    """Return a valid vanilla PC ID before any seven-byte family lookup."""
    if type(logical_pc_id) is not int or not 0 <= logical_pc_id <= 6:
        raise BattlePackageTopologyAuditError(
            "PC normal Attack logical ID is outside vanilla domain 00-06"
        )
    return logical_pc_id


def require_named_pc_tech_action_id(action_id: int) -> int:
    """Return a canonical named-Tech row; basic IDs use another route."""
    if type(action_id) is not int or not 0x01 <= action_id <= 0x74:
        raise BattlePackageTopologyAuditError(
            "PC Tech action is outside canonical named domain 01-74"
        )
    return action_id


def battle_item_record_index(raw_item_id: int) -> int:
    """Map the proved BC-DB battle-item domain before table access."""
    if type(raw_item_id) is not int or not 0xBC <= raw_item_id <= 0xDB:
        raise BattlePackageTopologyAuditError(
            "item is outside canonical battle-package domain BC-DB"
        )
    return raw_item_id - 0xBC


def _reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BattlePackageTopologyAuditError(
                f"duplicate JSON key: {key}"
            )
        result[key] = value
    return result


def _require_exact_keys(
    value: Any,
    expected: set[str],
    label: str,
) -> None:
    if not isinstance(value, Mapping):
        raise BattlePackageTopologyAuditError(f"{label} is not an object")
    observed = set(value)
    if observed != expected:
        raise BattlePackageTopologyAuditError(
            f"{label} keys drifted: expected {sorted(expected)}, "
            f"observed {sorted(observed)}"
        )


def _require_same_json_shape(value: Any, pinned: Any, label: str) -> None:
    """Reject unknown keys, missing rows, and JSON scalar type drift."""
    if isinstance(pinned, Mapping):
        if not isinstance(value, Mapping):
            raise BattlePackageTopologyAuditError(
                f"{label} changed from object"
            )
        if set(value) != set(pinned):
            raise BattlePackageTopologyAuditError(
                f"{label} nested keys drifted"
            )
        for key in pinned:
            _require_same_json_shape(
                value[key],
                pinned[key],
                f"{label}.{key}",
            )
        return
    if isinstance(pinned, list):
        if not isinstance(value, list) or len(value) != len(pinned):
            raise BattlePackageTopologyAuditError(
                f"{label} array shape drifted"
            )
        for index, (child, pinned_child) in enumerate(
            zip(value, pinned, strict=True)
        ):
            _require_same_json_shape(
                child,
                pinned_child,
                f"{label}[{index}]",
            )
        return
    if type(value) is not type(pinned):
        raise BattlePackageTopologyAuditError(
            f"{label} scalar type drifted"
        )


def _json_schema_shape(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            "type": "object",
            "properties": {
                key: _json_schema_shape(value[key])
                for key in sorted(value)
            },
        }
    if isinstance(value, list):
        return {
            "type": "array",
            "length": len(value),
            "items": [_json_schema_shape(child) for child in value],
        }
    if value is None:
        return "null"
    if type(value) is bool:
        return "boolean"
    if type(value) is int:
        return "integer"
    if type(value) is str:
        return "string"
    raise BattlePackageTopologyAuditError(
        f"report contains non-JSON-native value: {type(value).__name__}"
    )


def _auditor_source_identity() -> dict[str, Any]:
    try:
        source = Path(__file__).resolve().read_bytes()
    except OSError as exc:
        raise BattlePackageTopologyAuditError(
            "cannot read auditor source for artifact identity"
        ) from exc
    return {
        "path": "tools/audit_battle_action_package_topology_v0.py",
        "size": len(source),
        "sha256": _sha256_bytes(source),
    }


def _attach_artifact_identity(report: dict[str, Any]) -> dict[str, Any]:
    if "artifact_identity" in report:
        raise BattlePackageTopologyAuditError(
            "artifact identity envelope already exists"
        )
    semantic_payload = _canonical_json_bytes(report)
    schema_shape = _json_schema_shape(report)
    result = dict(report)
    result["artifact_identity"] = {
        "identity_scope": "report excluding artifact_identity envelope",
        "canonicalization": (
            "ASCII JSON; ensure_ascii=true; sorted keys; compact separators"
        ),
        "semantic_payload_size": len(semantic_payload),
        "semantic_payload_sha256": _sha256_bytes(semantic_payload),
        "schema_shape_sha256": _metadata_ledger_sha256(schema_shape),
        "full_report_self_hash_included": False,
    }
    return result


def load_reference_contract(
    path: Path = REFERENCE_PATH,
) -> Mapping[str, Any]:
    try:
        source = path.read_bytes()
    except OSError as exc:
        raise BattlePackageTopologyAuditError(
            f"cannot read pinned reference contract: {path}"
        ) from exc
    if len(source) != REFERENCE_SIZE:
        raise BattlePackageTopologyAuditError(
            "reference contract size drifted"
        )
    if _sha256_bytes(source) != REFERENCE_SHA256:
        raise BattlePackageTopologyAuditError(
            "reference contract SHA-256 drifted"
        )
    try:
        value = json.loads(
            source.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except BattlePackageTopologyAuditError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BattlePackageTopologyAuditError(
            "reference contract is not valid UTF-8 JSON"
        ) from exc
    _validate_reference_contract(value)
    return value


def _validate_reference_contract(value: Any) -> None:
    _require_exact_keys(
        value,
        {
            "schema",
            "version",
            "evidence_level",
            "scope",
            "canonical_rom",
            "action_type_contract",
            "descriptor_contract",
            "route_contracts",
            "expected_results",
            "hazards",
            "limitations",
            "nonclaims",
        },
        "reference root",
    )
    if (
        value.get("schema") != REFERENCE_SCHEMA
        or type(value.get("version")) is not int
        or value.get("version") != 1
        or value.get("evidence_level") != "verified-static"
    ):
        raise BattlePackageTopologyAuditError(
            "reference contract identity drifted"
        )
    canonical = value.get("canonical_rom")
    _require_exact_keys(
        canonical,
        {"identity", "size", "sha1", "sha256"},
        "canonical_rom",
    )
    if (
        canonical.get("identity")
        != "Chrono Trigger US Rev0 headerless"
        or canonical.get("size") != CANONICAL_ROM_SIZE
        or canonical.get("sha1") != CANONICAL_ROM_SHA1
        or canonical.get("sha256") != CANONICAL_ROM_SHA256
    ):
        raise BattlePackageTopologyAuditError(
            "canonical ROM contract drifted"
        )
    if value.get("limitations") != list(LIMITATIONS):
        raise BattlePackageTopologyAuditError(
            "reference limitations drifted"
        )
    if value.get("nonclaims") != list(NONCLAIMS):
        raise BattlePackageTopologyAuditError(
            "reference nonclaims drifted"
        )
    route_contracts = value.get("route_contracts")
    if not isinstance(route_contracts, list):
        raise BattlePackageTopologyAuditError(
            "reference route_contracts is not an array"
        )
    if [row.get("name") for row in route_contracts] != list(ROUTE_SPECS):
        raise BattlePackageTopologyAuditError(
            "reference route order drifted"
        )
    results = value.get("expected_results")
    _require_exact_keys(
        results,
        {
            "routes",
            "declared_context_union",
            "config_selected_structural_union",
            "cross_route_script_aliases",
        },
        "expected_results",
    )
    if set(results["routes"]) != set(ROUTE_SPECS):
        raise BattlePackageTopologyAuditError(
            "reference expected route result set drifted"
        )


def validate_canonical_rom(rom: bytes) -> dict[str, Any]:
    if not isinstance(rom, bytes) or len(rom) != CANONICAL_ROM_SIZE:
        raise BattlePackageTopologyAuditError(
            f"expected {CANONICAL_ROM_SIZE:#x} ROM bytes"
        )
    sha1 = hashlib.sha1(rom).hexdigest()
    sha256 = hashlib.sha256(rom).hexdigest()
    if sha1 != CANONICAL_ROM_SHA1 or sha256 != CANONICAL_ROM_SHA256:
        raise BattlePackageTopologyAuditError(
            "ROM hash does not match headerless US Rev0"
        )
    return {
        "identity": "Chrono Trigger US Rev0 headerless",
        "size": len(rom),
        "sha1": sha1,
        "sha256": sha256,
    }


def _table_map() -> dict[str, TableSpec]:
    result = {spec.name: spec for spec in TABLE_SPECS}
    if len(result) != len(TABLE_SPECS):
        raise BattlePackageTopologyAuditError(
            "built-in table names are not unique"
        )
    return result


def _observe_span(rom: bytes, spec: SpanSpec) -> dict[str, Any]:
    source = _slice_snes(rom, spec.start, spec.end_exclusive)
    observed_sha256 = _sha256_bytes(source)
    if observed_sha256 != spec.expected_sha256:
        raise BattlePackageTopologyAuditError(
            f"bounded preimage drifted: {spec.name}"
        )
    return {
        "name": spec.name,
        "label": spec.label,
        "snes_start": _hex6(spec.start),
        "snes_end_exclusive": _hex6(spec.end_exclusive),
        "length": spec.end_exclusive - spec.start,
        "observed_sha256": observed_sha256,
    }


def _selector_vector(rom: bytes, spec: TableSpec) -> list[int]:
    if spec.role != "selector_source":
        raise BattlePackageTopologyAuditError(
            f"table is not a selector source: {spec.name}"
        )
    source = _slice_snes(rom, spec.start, spec.end_exclusive)
    expected_length = spec.entry_count * spec.entry_width
    if len(source) != expected_length:
        raise BattlePackageTopologyAuditError(
            f"selector table geometry drifted: {spec.name}"
        )
    vector = list(source[:: spec.entry_width])
    observed_hash = _sha256_bytes(bytes(vector))
    if observed_hash != SELECTOR_VECTOR_HASHES[spec.name]:
        raise BattlePackageTopologyAuditError(
            f"selector vector drifted: {spec.name}"
        )
    return vector


def _pointer_table(rom: bytes, spec: TableSpec) -> list[int]:
    if spec.role != "package_resolver" or spec.entry_width != 2:
        raise BattlePackageTopologyAuditError(
            f"table is not a package resolver: {spec.name}"
        )
    source = _slice_snes(rom, spec.start, spec.end_exclusive)
    if len(source) != spec.entry_count * 2:
        raise BattlePackageTopologyAuditError(
            f"pointer table geometry drifted: {spec.name}"
        )
    return [_u16le(source, index * 2) for index in range(spec.entry_count)]


def parse_package_descriptor(
    rom: bytes,
    *,
    bank: int,
    root_offset: int,
    allowed_offset_start: int,
    allowed_offset_end_exclusive: int,
) -> PackageDescriptor:
    """Parse one selected descriptor; FFFF is auditor-invalid, not safe."""
    if type(bank) is not int or not 0xC0 <= bank <= 0xFF:
        raise BattlePackageTopologyAuditError("invalid package bank")
    if any(
        type(value) is not int
        for value in (
            root_offset,
            allowed_offset_start,
            allowed_offset_end_exclusive,
        )
    ):
        raise BattlePackageTopologyAuditError(
            "descriptor bounds must be integers"
        )
    if not (
        0
        <= allowed_offset_start
        < allowed_offset_end_exclusive
        <= 0x10000
    ):
        raise BattlePackageTopologyAuditError(
            "invalid audited bank region"
        )
    if root_offset == 0xFFFF:
        raise BattlePackageTopologyAuditError(
            "selected resolver target is FFFF; engine has no local rejection"
        )
    if not allowed_offset_start <= root_offset < allowed_offset_end_exclusive:
        raise BattlePackageTopologyAuditError(
            "selected descriptor root is outside the audited bank region"
        )
    if root_offset + 4 > allowed_offset_end_exclusive:
        raise BattlePackageTopologyAuditError(
            "selected descriptor header is truncated at the audited bank "
            "boundary"
        )
    header_address = (bank << 16) | root_offset
    header = _slice_snes(rom, header_address, header_address + 4)
    mask0 = (header[0] << 8) | header[1]
    mask1 = (header[2] << 8) | header[3]
    entry_count = mask0.bit_count() + mask1.bit_count()
    end_offset_exclusive = root_offset + 4 + entry_count * 2
    if end_offset_exclusive > allowed_offset_end_exclusive:
        raise BattlePackageTopologyAuditError(
            "selected descriptor is truncated at the audited bank boundary"
        )
    pointer_bytes = (
        _slice_snes(
            rom,
            header_address + 4,
            header_address + 4 + entry_count * 2,
        )
        if entry_count
        else b""
    )
    entries: list[DescriptorEntry] = []
    pointer_index = 0
    for branch, mask in enumerate((mask0, mask1)):
        for owner_slot in range(16):
            if not mask & (0x8000 >> owner_slot):
                continue
            script_offset = _u16le(pointer_bytes, pointer_index * 2)
            pointer_index += 1
            if not (
                allowed_offset_start
                <= script_offset
                < allowed_offset_end_exclusive
            ):
                raise BattlePackageTopologyAuditError(
                    "selected script entrypoint is outside the audited bank "
                    "region"
                )
            entries.append(
                DescriptorEntry(branch, owner_slot, script_offset)
            )
    if pointer_index != entry_count:
        raise BattlePackageTopologyAuditError(
            "descriptor mask/pointer consumption drifted"
        )
    return PackageDescriptor(
        bank,
        root_offset,
        end_offset_exclusive,
        mask0,
        mask1,
        tuple(entries),
    )


def _build_route_contexts(
    rom: bytes,
) -> dict[str, list[list[int | str]]]:
    tables = _table_map()
    pc_attack = _selector_vector(
        rom,
        tables["pc_normal_attack_selector_families"],
    )
    pc_action = _selector_vector(rom, tables["pc_action_configs"])
    enemy_attack_zero = _selector_vector(
        rom,
        tables["enemy_attack_param_zero_configs"],
    )
    enemy_attack_nonzero = _selector_vector(
        rom,
        tables["enemy_attack_param_nonzero_configs"],
    )
    enemy_tech = _selector_vector(rom, tables["enemy_tech_configs"])
    items = _selector_vector(rom, tables["item_configs"])

    result: dict[str, list[list[int | str]]] = {
        "pc_normal_attack": [],
        "pc_named_tech": [
            [action_id, pc_action[action_id]]
            for action_id in map(
                require_named_pc_tech_action_id,
                range(0x01, 0x75),
            )
        ],
        "pc_internal_type2_config": [
            [
                producer_kind,
                _hex6(fixed_value_load_pc),
                config_index,
                pc_action[config_index],
            ]
            for (
                producer_kind,
                fixed_value_load_pc,
                config_index,
            ) in PC_INTERNAL_TYPE2_CONTEXTS
        ],
        "pc_action_physical": [
            [action_id, selector]
            for action_id, selector in enumerate(pc_action)
        ],
        "enemy_attack": [
            ["attack_param_zero", record_id, selector]
            for record_id, selector in enumerate(enemy_attack_zero)
        ]
        + [
            ["attack_param_nonzero", record_id, selector]
            for record_id, selector in enumerate(enemy_attack_nonzero)
        ],
        "enemy_tech": [
            [record_id, selector]
            for record_id, selector in enumerate(enemy_tech)
        ],
        "battle_item": [
            [raw_item_id, items[battle_item_record_index(raw_item_id)]]
            for raw_item_id in range(0xBC, 0xDC)
        ],
    }
    family_names = (
        "noncritical_9930_zero",
        "noncritical_9930_nonzero",
        "critical",
    )
    for family_index, family_name in enumerate(family_names):
        start = family_index * 7
        for logical_pc_id in range(7):
            logical_pc_id = require_vanilla_pc_normal_attack_id(
                logical_pc_id
            )
            result["pc_normal_attack"].append(
                [
                    family_name,
                    logical_pc_id,
                    pc_attack[start + logical_pc_id],
                ]
            )

    if pc_action != list(range(128)):
        mismatch_count = sum(
            action_id != selector
            for action_id, selector in enumerate(pc_action)
        )
        if mismatch_count != 27 or sorted(pc_action) != list(range(128)):
            raise BattlePackageTopologyAuditError(
                "PC action selector permutation geometry drifted"
            )
    else:
        raise BattlePackageTopologyAuditError(
            "PC action selectors unexpectedly became identity-mapped"
        )
    if (
        _sha256_bytes(bytes(pc_action[0x01:0x75]))
        != PC_NAMED_SELECTOR_VECTOR_SHA256
    ):
        raise BattlePackageTopologyAuditError(
            "ordered named-PC-Tech selector mapping drifted"
        )
    internal_indices = [row[2] for row in PC_INTERNAL_TYPE2_CONTEXTS]
    if (
        sorted(set(internal_indices))
        != [0x79, 0x7A, 0x7B, 0x7C, 0x7D, 0x7F]
        or internal_indices.count(0x7F) != 2
        or any(pc_action[index] != index for index in internal_indices)
    ):
        raise BattlePackageTopologyAuditError(
            "fixed PC type-2 config context geometry drifted"
        )
    if any(selector != 0xFF for selector in items[0x20:]):
        raise BattlePackageTopologyAuditError(
            "battle item invalid-tail selector geometry drifted"
        )
    return result


def _descriptor_ledger_row(
    descriptor: PackageDescriptor,
) -> list[Any]:
    return [
        descriptor.bank,
        descriptor.root_offset,
        descriptor.mask0,
        descriptor.mask1,
        [
            [entry.branch, entry.owner_slot, entry.script_offset]
            for entry in descriptor.entries
        ],
    ]


def _analyze_route(
    rom: bytes,
    spec: RouteSpec,
    contexts: list[list[int | str]],
) -> tuple[dict[str, Any], dict[int, PackageDescriptor]]:
    tables = _table_map()
    resolver_spec = tables[spec.pointer_table]
    resolver = _pointer_table(rom, resolver_spec)
    selectors = sorted({int(row[-1]) for row in contexts})
    if not selectors:
        raise BattlePackageTopologyAuditError(
            f"route has no selectors: {spec.name}"
        )
    descriptors: dict[int, PackageDescriptor] = {}
    selector_rows: list[list[int]] = []
    selector_relation_rows: list[list[int]] = []
    for selector in selectors:
        if not 0 <= selector < len(resolver):
            raise BattlePackageTopologyAuditError(
                f"selected selector exceeds resolver: {spec.name}"
            )
        root = resolver[selector]
        descriptor = parse_package_descriptor(
            rom,
            bank=spec.package_bank,
            root_offset=root,
            allowed_offset_start=spec.allowed_offset_start,
            allowed_offset_end_exclusive=(
                spec.allowed_offset_end_exclusive
            ),
        )
        prior = descriptors.setdefault(root, descriptor)
        if prior != descriptor:
            raise BattlePackageTopologyAuditError(
                "one descriptor root decoded inconsistently"
            )
        selector_rows.append([selector, spec.package_bank, root])
        for entry in descriptor.entries:
            selector_relation_rows.append(
                [
                    selector,
                    spec.package_bank,
                    root,
                    entry.branch,
                    entry.owner_slot,
                    entry.script_offset,
                ]
            )

    ordered_descriptors = [descriptors[root] for root in sorted(descriptors)]
    descriptor_rows = [
        _descriptor_ledger_row(descriptor)
        for descriptor in ordered_descriptors
    ]
    relation_rows: list[list[int]] = []
    for descriptor in ordered_descriptors:
        for entry in descriptor.entries:
            relation_rows.append(
                [
                    descriptor.bank,
                    descriptor.root_offset,
                    entry.branch,
                    entry.owner_slot,
                    entry.script_offset,
                ]
            )

    physical_scripts = {
        (row[0], row[-1])
        for row in relation_rows
    }
    if not physical_scripts:
        raise BattlePackageTopologyAuditError(
            f"route has no script entrypoints: {spec.name}"
        )
    root_offsets = sorted(descriptors)
    script_offsets = sorted(offset for _, offset in physical_scripts)
    physical_mask_counts = [
        sum(descriptor.mask0.bit_count() for descriptor in ordered_descriptors),
        sum(descriptor.mask1.bit_count() for descriptor in ordered_descriptors),
    ]
    selector_mask_counts = [
        sum(
            descriptors[resolver[selector]].mask0.bit_count()
            for selector in selectors
        ),
        sum(
            descriptors[resolver[selector]].mask1.bit_count()
            for selector in selectors
        ),
    ]
    metrics = {
        "source_context_count": len(contexts),
        "distinct_selector_count": len(selectors),
        "selector_min": _hex2(min(selectors)),
        "selector_max": _hex2(max(selectors)),
        "distinct_descriptor_count": len(descriptors),
        "selector_to_descriptor_alias_count": (
            len(selectors) - len(descriptors)
        ),
        "physical_mask0_set_bit_count": physical_mask_counts[0],
        "physical_mask1_set_bit_count": physical_mask_counts[1],
        "selector_mapping_mask0_set_bit_count": selector_mask_counts[0],
        "selector_mapping_mask1_set_bit_count": selector_mask_counts[1],
        "physical_script_pointer_occurrence_count": len(relation_rows),
        "selector_mapping_script_pointer_occurrence_count": len(
            selector_relation_rows
        ),
        "distinct_physical_script_entrypoint_count": len(physical_scripts),
        "physical_script_pointer_alias_count": (
            len(relation_rows) - len(physical_scripts)
        ),
        "maximum_descriptor_script_pointer_count": max(
            len(descriptor.entries) for descriptor in ordered_descriptors
        ),
        "descriptor_root_min": _hex4(root_offsets[0]),
        "descriptor_root_max": _hex4(root_offsets[-1]),
        "script_entrypoint_min": _hex4(script_offsets[0]),
        "script_entrypoint_max": _hex4(script_offsets[-1]),
        "source_context_ledger_sha256": _metadata_ledger_sha256(contexts),
        "selector_descriptor_ledger_sha256": _metadata_ledger_sha256(
            selector_rows
        ),
        "physical_descriptor_ledger_sha256": _metadata_ledger_sha256(
            descriptor_rows
        ),
        "physical_relation_ledger_sha256": _metadata_ledger_sha256(
            relation_rows
        ),
    }
    return metrics, descriptors


def _validate_descriptor_geometry(
    route_descriptors: Mapping[str, Mapping[int, PackageDescriptor]],
    *,
    route_names: Sequence[str],
    union_semantics: str = (
        "declared structural union, not runtime reachability"
    ),
) -> dict[str, Any]:
    physical: dict[tuple[int, int], PackageDescriptor] = {}
    for route_name in route_names:
        for descriptor in route_descriptors[route_name].values():
            key = (descriptor.bank, descriptor.root_offset)
            prior = physical.setdefault(key, descriptor)
            if prior != descriptor:
                raise BattlePackageTopologyAuditError(
                    "shared descriptor root decoded inconsistently"
                )

    ordered = sorted(physical.values(), key=lambda row: (row.bank, row.root_offset))
    for left, right in zip(ordered, ordered[1:]):
        if left.bank != right.bank:
            continue
        if left.end_offset_exclusive > right.root_offset:
            raise BattlePackageTopologyAuditError(
                "selected package descriptor spans overlap"
            )

    physical_scripts: set[tuple[int, int]] = set()
    observed_slots: set[int] = set()
    relation_count = 0
    for descriptor in ordered:
        relation_count += len(descriptor.entries)
        for entry in descriptor.entries:
            observed_slots.add(entry.owner_slot)
            physical_scripts.add((descriptor.bank, entry.script_offset))
    if observed_slots & {5, 6, 7}:
        raise BattlePackageTopologyAuditError(
            "selected descriptors unexpectedly use owner bits 05-07"
        )
    if not observed_slots & set(range(8, 16)):
        raise BattlePackageTopologyAuditError(
            "selected descriptors unexpectedly lack owner bits 08-15"
        )
    for bank, script_offset in physical_scripts:
        for descriptor in ordered:
            if descriptor.bank != bank:
                continue
            if (
                descriptor.root_offset
                <= script_offset
                < descriptor.end_offset_exclusive
            ):
                raise BattlePackageTopologyAuditError(
                    "selected script entrypoint targets descriptor bytes"
                )

    descriptor_banks = Counter(descriptor.bank for descriptor in ordered)
    script_banks = Counter(bank for bank, _ in physical_scripts)
    descriptor_rows = [_descriptor_ledger_row(row) for row in ordered]
    relation_rows = [
        [
            route_name,
            descriptor.bank,
            descriptor.root_offset,
            entry.branch,
            entry.owner_slot,
            entry.script_offset,
        ]
        for route_name in route_names
        for descriptor in sorted(
            route_descriptors[route_name].values(),
            key=lambda row: row.root_offset,
        )
        for entry in descriptor.entries
    ]
    return {
        "included_routes": list(route_names),
        "union_semantics": union_semantics,
        "distinct_descriptor_count": len(ordered),
        "descriptor_count_by_bank": {
            _hex2(bank): descriptor_banks[bank]
            for bank in sorted(descriptor_banks)
        },
        "physical_script_pointer_occurrence_count": relation_count,
        "distinct_physical_script_entrypoint_count": len(physical_scripts),
        "script_entrypoint_count_by_bank": {
            _hex2(bank): script_banks[bank]
            for bank in sorted(script_banks)
        },
        "descriptor_spans_disjoint": True,
        "script_entrypoints_outside_descriptor_spans": True,
        "descriptor_slots_05_07_unset": True,
        "descriptor_owner_bits_08_15_present": True,
        "physical_descriptor_ledger_sha256": _metadata_ledger_sha256(
            descriptor_rows
        ),
        "route_relation_ledger_sha256": _metadata_ledger_sha256(
            relation_rows
        ),
    }


def _physical_script_set(
    descriptors: Mapping[int, PackageDescriptor],
) -> set[tuple[int, int]]:
    return {
        (descriptor.bank, entry.script_offset)
        for descriptor in descriptors.values()
        for entry in descriptor.entries
    }


def _pc_internal_type2_package_summary(
    rom: bytes,
    descriptors: Mapping[int, PackageDescriptor],
) -> list[dict[str, Any]]:
    tables = _table_map()
    config_selectors = _selector_vector(rom, tables["pc_action_configs"])
    resolver = _pointer_table(
        rom,
        tables["pc_action_package_resolver"],
    )
    observed: list[tuple[int, int, int, int, int]] = []
    for config_index in sorted(
        {row[2] for row in PC_INTERNAL_TYPE2_CONTEXTS}
    ):
        package_selector = config_selectors[config_index]
        descriptor_root = resolver[package_selector]
        descriptor = descriptors.get(descriptor_root)
        if descriptor is None or descriptor.bank != 0xCE:
            raise BattlePackageTopologyAuditError(
                "fixed PC type-2 summary descriptor is unavailable"
            )
        observed.append(
            (
                config_index,
                package_selector,
                descriptor_root,
                len(descriptor.entries),
                len({entry.script_offset for entry in descriptor.entries}),
            )
        )
    if tuple(observed) != EXPECTED_PC_INTERNAL_TYPE2_PACKAGE_SUMMARY:
        raise BattlePackageTopologyAuditError(
            "fixed PC type-2 package summary drifted"
        )
    return [
        {
            "config_index": _hex2(config_index),
            "package_selector": _hex2(package_selector),
            "package_bank": "CE",
            "descriptor_root": _hex4(descriptor_root),
            "descriptor_relation_count": relation_count,
            "distinct_direct_script_count": distinct_script_count,
        }
        for (
            config_index,
            package_selector,
            descriptor_root,
            relation_count,
            distinct_script_count,
        ) in observed
    ]


def _cross_route_aliases(
    route_descriptors: Mapping[str, Mapping[int, PackageDescriptor]],
) -> list[dict[str, Any]]:
    route_names = (
        "pc_normal_attack",
        "pc_named_tech",
        "pc_internal_type2_config",
        "enemy_attack",
        "enemy_tech",
        "battle_item",
    )
    sets = {
        name: _physical_script_set(route_descriptors[name])
        for name in route_names
    }
    result: list[dict[str, Any]] = []
    for left_index, left in enumerate(route_names):
        for right in route_names[left_index + 1 :]:
            shared = sets[left] & sets[right]
            if not shared:
                continue
            banks = Counter(bank for bank, _ in shared)
            result.append(
                {
                    "left": left,
                    "right": right,
                    "same_bank_physical_script_entrypoint_count": len(
                        shared
                    ),
                    "count_by_bank": {
                        _hex2(bank): banks[bank]
                        for bank in sorted(banks)
                    },
                }
            )
    return result


def _cross_bank_same_low_controls(
    route_descriptors: Mapping[str, Mapping[int, PackageDescriptor]],
    *,
    route_names: Sequence[str],
) -> dict[str, Any]:
    roots_by_low: dict[int, set[int]] = {}
    scripts_by_low: dict[int, set[int]] = {}
    for route_name in route_names:
        for descriptor in route_descriptors[route_name].values():
            roots_by_low.setdefault(descriptor.root_offset, set()).add(
                descriptor.bank
            )
            for entry in descriptor.entries:
                scripts_by_low.setdefault(entry.script_offset, set()).add(
                    descriptor.bank
                )
    root_collisions = sorted(
        offset for offset, banks in roots_by_low.items() if len(banks) > 1
    )
    script_collisions = sorted(
        offset
        for offset, banks in scripts_by_low.items()
        if len(banks) > 1
    )
    expected_roots = [0x8171]
    expected_scripts = [0x6E56, 0x76F9, 0x7750, 0x81CE]
    if (
        root_collisions != expected_roots
        or script_collisions != expected_scripts
    ):
        raise BattlePackageTopologyAuditError(
            "cross-bank same-low negative controls drifted"
        )
    return {
        "descriptor_low_offsets_present_in_both_CD_and_CE": [
            _hex4(value) for value in root_collisions
        ],
        "script_low_offsets_present_in_both_CD_and_CE": [
            _hex4(value) for value in script_collisions
        ],
        "bank_omission_would_merge_distinct_nodes": True,
    }


def _observe_tables(
    rom: bytes,
    route_contexts: Mapping[str, list[list[int | str]]],
) -> list[dict[str, Any]]:
    selected_by_resolver = {
        "pc_normal_attack_package_resolver": {
            int(row[-1]) for row in route_contexts["pc_normal_attack"]
        },
        "pc_action_package_resolver": {
            int(row[-1]) for row in route_contexts["pc_action_physical"]
        },
        "enemy_attack_package_resolver": {
            int(row[-1]) for row in route_contexts["enemy_attack"]
        },
        "enemy_tech_package_resolver": {
            int(row[-1]) for row in route_contexts["enemy_tech"]
        },
        "item_package_resolver": {
            int(row[-1]) for row in route_contexts["battle_item"]
        },
    }
    result: list[dict[str, Any]] = []
    for spec in TABLE_SPECS:
        observation = _observe_span(rom, spec)
        observation.update(
            {
                "entry_count": spec.entry_count,
                "entry_width": spec.entry_width,
                "role": spec.role,
            }
        )
        if spec.role == "selector_source":
            vector = _selector_vector(rom, spec)
            observation["selector_vector_sha256"] = (
                SELECTOR_VECTOR_HASHES[spec.name]
            )
            observation["distinct_selector_count"] = len(set(vector))
            observation["selector_min"] = _hex2(min(vector))
            observation["selector_max"] = _hex2(max(vector))
        else:
            pointers = _pointer_table(rom, spec)
            selected = selected_by_resolver[spec.name]
            if any(pointer == 0xFFFF for index, pointer in enumerate(pointers) if index in selected):
                raise BattlePackageTopologyAuditError(
                    f"selected resolver value became FFFF: {spec.name}"
                )
            observation["selected_selector_count"] = len(selected)
            observation["ffff_value_count"] = sum(
                pointer == 0xFFFF for pointer in pointers
            )
            observation["non_ffff_unselected_count"] = sum(
                pointer != 0xFFFF and index not in selected
                for index, pointer in enumerate(pointers)
            )
            observation["selected_targets_are_non_ffff"] = True
            observation["engine_local_ffff_rejection_proved"] = False
            inventory = {
                "selected_selector_count": observation[
                    "selected_selector_count"
                ],
                "ffff_value_count": observation["ffff_value_count"],
                "non_ffff_unselected_count": observation[
                    "non_ffff_unselected_count"
                ],
            }
            if inventory != EXPECTED_RESOLVER_INVENTORY[spec.name]:
                raise BattlePackageTopologyAuditError(
                    f"resolver inventory drifted: {spec.name}"
                )
        result.append(observation)
    return result


def _observe_action_type_contract(rom: bytes) -> dict[str, Any]:
    table = _slice_snes(rom, 0xC17A63, 0xC17A6B)
    targets = tuple(_u16le(table, index * 2) for index in range(4))
    if targets != EXPECTED_ACTION_TYPE_TARGETS:
        raise BattlePackageTopologyAuditError(
            "action-type target table drifted"
        )
    return {
        "top_level_dispatch_key": "AE92_action_type",
        "action_parameter_register": "AE93_route_specific_parameter",
        "complete_package_selection_key": "route_specific",
        "out_of_range_action_type_behavior": (
            "AE92 values 04-FF are coerced to type 00 before dispatch"
        ),
        "targets": [
            {
                "action_type": _hex2(action_type),
                "target_pc": f"C1{target:04X}",
                "route": route,
            }
            for action_type, target, route in (
                (0, targets[0], "no_package_load_rts"),
                (1, targets[1], "attack_actor_split"),
                (2, targets[2], "tech_actor_split"),
                (3, targets[3], "battle_item"),
            )
        ],
    }


def _expected_route_result(
    contract: Mapping[str, Any],
    route_name: str,
) -> Mapping[str, Any]:
    value = contract["expected_results"]["routes"].get(route_name)
    if not isinstance(value, Mapping):
        raise BattlePackageTopologyAuditError(
            f"missing expected route result: {route_name}"
        )
    return value


def audit_rom(
    rom: bytes,
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pinned_contract = load_reference_contract()
    if contract is None:
        contract = pinned_contract
    else:
        _validate_reference_contract(contract)
        _require_same_json_shape(
            contract,
            pinned_contract,
            "caller-supplied reference contract",
        )
        if contract != pinned_contract:
            raise BattlePackageTopologyAuditError(
                "caller-supplied reference contract differs from pinned file"
            )
    rom_identity = validate_canonical_rom(rom)
    machine = [_observe_span(rom, span) for span in MACHINE_SPANS]
    contexts = _build_route_contexts(rom)
    route_metrics: dict[str, dict[str, Any]] = {}
    route_descriptors: dict[str, dict[int, PackageDescriptor]] = {}
    for route_name, spec in ROUTE_SPECS.items():
        metrics, descriptors = _analyze_route(
            rom,
            spec,
            contexts[route_name],
        )
        expected = _expected_route_result(contract, route_name)
        if metrics != expected:
            raise BattlePackageTopologyAuditError(
                f"route topology drifted: {route_name}"
            )
        route_metrics[route_name] = metrics
        route_descriptors[route_name] = descriptors

    declared_context_names = (
        "pc_normal_attack",
        "pc_named_tech",
        "pc_internal_type2_config",
        "enemy_attack",
        "enemy_tech",
        "battle_item",
    )
    declared_context_union = _validate_descriptor_geometry(
        route_descriptors,
        route_names=declared_context_names,
    )
    config_selected_names = (
        "pc_normal_attack",
        "pc_action_physical",
        "enemy_attack",
        "enemy_tech",
        "battle_item",
    )
    config_selected_structural_union = _validate_descriptor_geometry(
        route_descriptors,
        route_names=config_selected_names,
        union_semantics=(
            "config-selected structural supplement union, not runtime "
            "reachability"
        ),
    )
    expected_results = contract["expected_results"]
    if (
        declared_context_union
        != expected_results["declared_context_union"]
    ):
        raise BattlePackageTopologyAuditError(
            "declared context-union topology drifted"
        )
    if (
        config_selected_structural_union
        != expected_results["config_selected_structural_union"]
    ):
        raise BattlePackageTopologyAuditError(
            "config-selected structural-union topology drifted"
        )
    cross_aliases = _cross_route_aliases(route_descriptors)
    if cross_aliases != expected_results["cross_route_script_aliases"]:
        raise BattlePackageTopologyAuditError(
            "cross-route script alias topology drifted"
        )
    cross_bank_controls = _cross_bank_same_low_controls(
        route_descriptors,
        route_names=config_selected_names,
    )

    report = {
        "schema": SCHEMA,
        "version": 1,
        "auditor_version": AUDITOR_VERSION,
        "status": STATUS,
        "evidence_ceiling": (
            "verified-static metadata-only structural possible-context "
            "census, complete only for the explicitly listed selector and "
            "config domains plus the listed fixed PC type-02 direct-address "
            "producer contexts"
        ),
        "scope": dict(contract["scope"]),
        "inputs": {
            "rom": rom_identity,
            "reference_contract": {
                "path": "references/battle_action_package_topology_v0.json",
                "size": REFERENCE_SIZE,
                "sha256": REFERENCE_SHA256,
            },
            "interpretive_disassembly": {
                "repository": "dscotton/ct_disassembly",
                "commit": DISASSEMBLY_COMMIT,
                "authority": "documented-interpretive-only",
                "canonical_machine_preimages_are_authoritative": True,
            },
        },
        "action_type_contract": _observe_action_type_contract(rom),
        "ae93_encoded_operand_opcode_census": (
            _observe_ae93_encoded_operand_opcode_census(rom)
        ),
        "machine_code_contract": machine,
        "table_contract": _observe_tables(rom, contexts),
        "selector_namespaces": list(contract["route_contracts"]),
        "package_topology": {
            "routes": route_metrics,
            "pc_internal_type2_index_selector_descriptor_summary": (
                _pc_internal_type2_package_summary(
                    rom,
                    route_descriptors["pc_internal_type2_config"],
                )
            ),
            "declared_context_union": declared_context_union,
            "config_selected_structural_union": (
                config_selected_structural_union
            ),
        },
        "script_topology": {
            "identity_key": ["package_bank", "script_offset"],
            "cross_route_same_bank_aliases": cross_aliases,
            "config_selected_cross_bank_same_low_negative_controls": (
                cross_bank_controls
            ),
            "equal_offsets_in_different_banks_are_distinct": True,
            "command_stream_decode_complete": False,
        },
        "descriptor_contract": dict(contract["descriptor_contract"]),
        "hazards": list(contract["hazards"]),
        "gates": {
            "canonical_rom_hash_matched": True,
            "all_machine_preimages_matched": True,
            "encoded_operand_ae93_opcode_candidate_census_matched": True,
            "all_table_preimages_matched": True,
            "all_selected_resolver_targets_non_ffff": True,
            "all_selected_descriptors_bounded": True,
            "all_selected_descriptor_spans_disjoint": True,
            "all_selected_scripts_outside_descriptor_spans": True,
            "both_structural_mask_lists_consumed": True,
            "battle_command_decoder_complete": False,
            "runtime_performed": False,
            "rom_save_state_trace_mutation_performed": False,
            "patch_rom_or_output_file_emitted": False,
            "allocation_or_hook_approved": False,
        },
        "evidence": {
            "level": "verified-static",
            "runtime": False,
            "static_only": True,
            "canonical_rom_read_only": True,
            "metadata_only": True,
        },
        "reproduction": {
            "command": [
                "python",
                "tools/audit_battle_action_package_topology_v0.py",
                "<canonical-us-rev0-headerless-rom>",
                "--compact",
            ],
            "output": "metadata-only JSON on stdout",
            "output_file_option_available": False,
            "expected_exit_code": 0,
            "expected_stderr": "empty",
            "expected_side_effects": "none",
            "auditor_source": _auditor_source_identity(),
            "reference_contract": {
                "path": (
                    "references/battle_action_package_topology_v0.json"
                ),
                "size": REFERENCE_SIZE,
                "sha256": REFERENCE_SHA256,
            },
        },
        "limitations": list(LIMITATIONS),
        "nonclaims": list(NONCLAIMS),
    }
    return _attach_artifact_identity(report)


def audit_rom_path(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file():
            raise BattlePackageTopologyAuditError(
                f"ROM input is not a regular file: {path}"
            )
        if path.stat().st_size != CANONICAL_ROM_SIZE:
            raise BattlePackageTopologyAuditError(
                f"expected {CANONICAL_ROM_SIZE:#x} ROM bytes"
            )
        rom = path.read_bytes()
    except BattlePackageTopologyAuditError:
        raise
    except OSError as exc:
        raise BattlePackageTopologyAuditError(
            f"cannot read ROM input: {path}"
        ) from exc
    return audit_rom(rom)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "rom",
        type=Path,
        help="headerless Chrono Trigger US Rev0 ROM; read-only",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="print compact JSON",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = audit_rom_path(args.rom)
    except (
        BattlePackageTopologyAuditError,
        OSError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            result,
            indent=None if args.compact else 2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
