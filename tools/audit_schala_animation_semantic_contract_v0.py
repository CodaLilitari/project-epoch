#!/usr/bin/env python3
"""Audit the source-only Schala animation semantic contract, version 0.

The command accepts only a private, headerless Chrono Trigger US Rev0 ROM.
It validates small canonical tables and code spans in memory and emits a
metadata-only JSON report to stdout.  It cannot write a ROM, animation blob,
patch, report, save, state, trace, image, or extracted byte stream.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib
import json
import pathlib
import sys
from collections.abc import Mapping, Sequence
from typing import Any, Final


ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
TOOL_VERSION: Final = "1.0.0"
SCHEMA_VERSION: Final = 1

CANONICAL_ROM_SIZE: Final = 0x400000
CANONICAL_ROM_SHA1: Final = "de5822f4f2f7a55acb8926d4c0eaa63d5d989312"
CANONICAL_ROM_SHA256: Final = (
    "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"
)
DISASSEMBLY_COMMIT: Final = "eeae27acdb6565e96d1d796a3d60792c250c0aa1"

CURRENT_BODY_REPORT_REL: Final = pathlib.PurePosixPath(
    "references/schala_current_body_packet_v0.json"
)
CURRENT_BODY_REPORT_SIZE: Final = 11953
CURRENT_BODY_REPORT_SHA256: Final = (
    "c5a04304739e5fac3125cb840e9745bafae0f45b0b2869b4743b5d25c1c1313b"
)

PRIMARY_POINTER_TABLE_FILE: Final = 0x242600
AUX_POINTER_TABLE_FILE: Final = 0x242800
ANIMATION_BANK_FILE_BASE: Final = 0x240000
FACING_COUNT: Final = 4
ENTRYPOINT_STRIDE: Final = 4
PRIMARY_TERMINATOR: Final = 0xFF
AUX_TERMINATOR: Final = 0x00

EXPECTED_PRIMARY_BOUNDARIES: Final = (
    0x3000,
    0x34A0,
    0x3880,
    0x3CF0,
    0x4160,
    0x45C0,
    0x4B00,
    0x4ED0,
)
EXPECTED_AUX_POINTERS: Final = (
    0xA800,
    0xA928,
    0xAA20,
    0xAB3C,
    0xAC58,
    0xAD70,
    0xAEC0,
    0xB600,
)

FIELD_ENTRYPOINTS: Final = (0x00, 0x01, 0x06, 0x17, 0x19, 0x1B, 0x21)
BATTLE_FIXED_ENTRYPOINTS: Final = (0x03, 0x08, 0x0A, 0x0C, 0x12, 0x1A, 0x23)
DECLARED_ANCHORS: Final = tuple(
    sorted(set(FIELD_ENTRYPOINTS + BATTLE_FIXED_ENTRYPOINTS))
)

BATTLE_STATE_SELECTOR_VALUES: Final = (0x00, 0x03, 0x08, 0x1A, 0x23, 0xFF)
BATTLE_STATE_TABLE_FILE_START: Final = 0x0CF77F
BATTLE_STATE_TABLE_FILE_END: Final = 0x0CF7C0
BATTLE_STATE_TABLE_SHA256: Final = (
    "1cfdd78e4dbe9c9c759d7b267053078b62ecd48fd1cf44d1df02346098cf07d7"
)


class AnimationContractError(ValueError):
    """Raised whenever an input or a claimed invariant fails closed."""


@dataclasses.dataclass(frozen=True)
class PcAnimationProfile:
    pc_id: int
    name: str
    primary_start: int
    primary_end: int
    aux_start: int
    aux_contract_end: int
    primary_sha256: str
    aux_sha256: str

    @property
    def facing_span(self) -> int:
        return (self.primary_end - self.primary_start) // FACING_COUNT


PC_PROFILES: Final = (
    PcAnimationProfile(
        0,
        "Crono",
        0x3000,
        0x34A0,
        0xA800,
        0xA928,
        "43c629e4e3ab32a5bce56189cb4ef7821d920b6c12318aa45edd742eded95dff",
        "721eab0b7857ceb614276ad28ec5ad7c0c79e7578666e9afea7ec8833ed31666",
    ),
    PcAnimationProfile(
        1,
        "Marle",
        0x34A0,
        0x3880,
        0xA928,
        0xAA20,
        "7fc62fe6ed719de9e3448c68d03f90f171ba4b31a420db58a0c9fe20bac751bf",
        "dfe632c8ae53d36d679d54e161d42314e022d0185549b95be0610d85807ac1ad",
    ),
    PcAnimationProfile(
        2,
        "Lucca",
        0x3880,
        0x3CF0,
        0xAA20,
        0xAB3C,
        "850c331267d16be7b11611d4f69d2120fac8e0f314102794b47b09fa7c200607",
        "ab76d471427face95fd53534352f59dbf4e2f301bf41e27d480b82e62e16645c",
    ),
    PcAnimationProfile(
        3,
        "Robo",
        0x3CF0,
        0x4160,
        0xAB3C,
        0xAC58,
        "3fd15908dd98720e53c3601b3750ec587717997d1b7f1ab65be6ce69ccf57fe6",
        "862ab3327146c980562b6572bb7c12f1b0122a75f4651615cdb7379959bf0ea4",
    ),
    PcAnimationProfile(
        4,
        "Frog",
        0x4160,
        0x45C0,
        0xAC58,
        0xAD70,
        "48ec0306a22490165efb296fad3dc4f8353c49db10f01c28713bb80776fd3ceb",
        "aad2cdba240e6e3b74c066851924601156026bef8a2abc5543a9bbb1cd20c224",
    ),
    PcAnimationProfile(
        5,
        "Ayla",
        0x45C0,
        0x4B00,
        0xAD70,
        0xAEC0,
        "ece49a6d2c7dc2af775489f49b917c55672991c766758c3444ba0b2545b87717",
        "92b4d35a23dadb946495b958ffcd0ce413e3b9bd86c0f97b8fdc178a814de4b7",
    ),
    PcAnimationProfile(
        6,
        "Magus",
        0x4B00,
        0x4ED0,
        0xAEC0,
        0xAFB4,
        "2875f534a1baa2e7064a62f05d5efaaf9e130dea9de195e66f256571c2464896",
        "c696370f63352d53654b7b7abf2fb605462c8440330d9ac6b2cd2941db9d76c8",
    ),
)


@dataclasses.dataclass(frozen=True)
class EngineSpan:
    label: str
    file_start: int
    file_end: int
    sha256: str
    claim: str


ENGINE_SPANS: Final = (
    EngineSpan(
        "primary_pointer_table",
        0x242600,
        0x242610,
        "714256243fcc785111f753cee8ad7570ad92851b29c89aec2e791065c0374112",
        "eight canonical primary animation boundaries",
    ),
    EngineSpan(
        "auxiliary_pointer_table",
        0x242800,
        0x242810,
        "76ffb90a88c1313ba4fcac38ef7631649f6e9b9022c8665ea4466d0448e704c6",
        "seven PC auxiliary starts plus occupied entry 7",
    ),
    EngineSpan(
        "field_pc_animation_pointer_load",
        0x0044E4,
        0x004509,
        "cb0d8f108a3028627706f191bfd145acabd727d0c12ee5768ea641a4649943d1",
        "primary and auxiliary pointers are loaded independently",
    ),
    EngineSpan(
        "field_event_animation_commands",
        0x002E67,
        0x002F96,
        "2cf746461f3607687fc0038f29663074523a641b112cf4c5256f4f8f4695f7a1",
        "AA AB AC AE B3 B4 B7 animation command namespace split",
    ),
    EngineSpan(
        "field_automatic_animation_selectors",
        0x00A171,
        0x00A26B,
        "b605ee4acc2186c7c1026516527feec9d7daeb262289be7bdbb7275c4e6b7d83",
        "automatic field entrypoints 00 01 06 17 19 1B 21",
    ),
    EngineSpan(
        "field_auxiliary_tick",
        0x00CA18,
        0x00CA76,
        "f456b80280496233d7ff4d15347fcdba1293fe623d82f288d2109dcc79bc2a58",
        "entrypoint times four, auxiliary delay read, zero termination",
    ),
    EngineSpan(
        "field_primary_reader",
        0x00CBB1,
        0x00CBDC,
        "0a07d56c0d022796fdfaa3b660be8431df4c3b3e6263a9d29205c23c9a308861",
        "four-facing primary read and FF loop/end behavior",
    ),
    EngineSpan(
        "battle_preload_entrypoint_0C",
        0x0134E4,
        0x013502,
        "807712b62546d9c98d35910371f582e0a7b0b30c4850785901615d2c50d41ee3",
        "fixed byte offset 30 selects entrypoint 0C",
    ),
    EngineSpan(
        "battle_preload_entrypoint_0A",
        0x0135B7,
        0x0135D6,
        "7b156e8c31b34b24bfb8d992714c87e6b7158001d40b8e58097edd0413e49f0d",
        "fixed byte offset 28 selects entrypoint 0A",
    ),
    EngineSpan(
        "battle_preload_eight_step_copy",
        0x013616,
        0x01365C,
        "a96a085cb099e0f2c813d08f150466755034914706f9270953674de35f82b3e1",
        "eight auxiliary bytes shifted right once and eight primary bytes copied",
    ),
    EngineSpan(
        "battle_animation_tick",
        0x0142B0,
        0x014310,
        "b4a519762310d5826d14779f0b9630441f11dc36a266e7e76a797cae9559efcf",
        "auxiliary zero stop and raw delay with parallel primary read",
    ),
    EngineSpan(
        "battle_play_animation_setup",
        0x014D04,
        0x014D79,
        "99655d5542c731178a6b491ef8628cf43d973c7ac514e16a1d896caf9070190d",
        "command 02 adds entrypoint times four to both stream bases",
    ),
    EngineSpan(
        "battle_state_animation_selector",
        0x012F97,
        0x01305C,
        "ff121e39f6b11466ede6146f3d825a9e60386524c49ac4da229a7b439dbaa202",
        "state table selector, FF branch rule, and critical-HP entrypoint 12",
    ),
    EngineSpan(
        "battle_state_animation_table",
        BATTLE_STATE_TABLE_FILE_START,
        BATTLE_STATE_TABLE_FILE_END,
        BATTLE_STATE_TABLE_SHA256,
        "sixteen four-byte records followed by FF terminator",
    ),
)


FIELD_CONSUMER_ROLES: Final = (
    {
        "role_id": "field_00",
        "entrypoint": 0x00,
        "consumer": "default and reset path",
        "conditions": "no stronger visual claim",
        "evidence": "verified-static",
    },
    {
        "role_id": "field_01",
        "entrypoint": 0x01,
        "consumer": "walking path",
        "conditions": "movement below run threshold",
        "evidence": "verified-static",
    },
    {
        "role_id": "field_06",
        "entrypoint": 0x06,
        "consumer": "normal run path",
        "conditions": "run path outside the alternate player branch",
        "evidence": "verified-static",
    },
    {
        "role_id": "field_17",
        "entrypoint": 0x17,
        "consumer": "player-specific alternate run branch",
        "conditions": "$1D32 == 0 and $1D33 == 0 and object is player and $E5 == 0",
        "evidence": "verified-static",
    },
    {
        "role_id": "field_19",
        "entrypoint": 0x19,
        "consumer": "player-specific no-movement branch",
        "conditions": "$62 == 2 and object is player",
        "evidence": "verified-static",
    },
    {
        "role_id": "field_1B",
        "entrypoint": 0x1B,
        "consumer": "special movement branch",
        "conditions": "move-mode bit 2 set and vertical facing component nonzero",
        "evidence": "verified-static",
    },
    {
        "role_id": "field_21",
        "entrypoint": 0x21,
        "consumer": "rare no-movement RNG branch",
        "conditions": "idle counter and random gate pass",
        "evidence": "verified-static",
    },
)


AUTHORING_ROLES: Final = (
    {
        "role_id": "field_idle_cardinal",
        "context": "field",
        "current_frame_ids": (
            "schala_field_idle_down_f00_v0",
            "schala_field_idle_up_f00_v0",
            "schala_field_idle_left_f00_v0",
            "schala_field_idle_right_f00_v0",
        ),
        "coverage": "complete-source-role-only",
        "related_engine_role_ids": ("field_00",),
    },
    {
        "role_id": "field_walk",
        "context": "field",
        "current_frame_ids": (
            "schala_field_walk_down_f00_v0",
            "schala_field_walk_down_f01_v0",
            "schala_field_walk_down_f02_v0",
        ),
        "coverage": "partial-down-only",
        "related_engine_role_ids": ("field_01",),
    },
    {
        "role_id": "battle_ready",
        "context": "battle",
        "current_frame_ids": ("schala_battle_ready_f00_v0",),
        "coverage": "partial-one-pose",
        "related_engine_role_ids": (),
    },
    {
        "role_id": "battle_cast",
        "context": "battle",
        "current_frame_ids": (
            "schala_battle_cast_gather_f00_v0",
            "schala_battle_cast_release_f00_v0",
        ),
        "coverage": "partial-two-poses",
        "related_engine_role_ids": (),
    },
    {
        "role_id": "battle_basic_attack",
        "context": "battle",
        "current_frame_ids": (
            "schala_battle_basic_attack_draw_f00_v0",
            "schala_battle_basic_attack_open_f01_v0",
            "schala_battle_basic_attack_pulse_f02_v0",
            "schala_battle_basic_attack_followthrough_f03_v0",
            "schala_battle_basic_attack_recoil_f04_v0",
            "schala_battle_basic_attack_recover_f05_v0",
        ),
        "coverage": "source-sequence-only-six-poses",
        "related_engine_role_ids": (),
    },
)


FORBIDDEN_REPORT_KEYS: Final = frozenset(
    {
        "allocation",
        "allocation_address",
        "assembly_bytes",
        "aux_bytes",
        "decoded_bytes",
        "destination",
        "graphics_bytes",
        "hook",
        "hook_address",
        "image",
        "palette_bytes",
        "patch",
        "payload",
        "pixels",
        "primary_bytes",
        "rom_bytes",
        "rows",
        "save_bytes",
        "state_bytes",
        "tile_bytes",
        "tile_words",
        "trace_bytes",
    }
)
EXPECTED_TOP_LEVEL_KEYS: Final = frozenset(
    {
        "schema_version",
        "auditor_version",
        "status",
        "scope",
        "inputs",
        "engine_contract",
        "canonical_profiles",
        "consumer_roles",
        "authoring_coverage",
        "open_gates",
        "evidence",
        "nonclaims",
    }
)


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_report_bytes(report: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _snes_label(file_offset: int) -> str:
    if not 0 <= file_offset < CANONICAL_ROM_SIZE:
        raise AnimationContractError("file offset outside canonical ROM")
    address = 0xC00000 | file_offset
    return f"${address >> 16:02X}:{address & 0xFFFF:04X}"


def _animation_label(offset: int) -> str:
    if not 0 <= offset <= 0xFFFF:
        raise AnimationContractError("animation-bank offset outside bank")
    return f"$E4:{offset:04X}"


def _read_u16_le(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise AnimationContractError("16-bit read exceeds input")
    return int.from_bytes(data[offset : offset + 2], "little")


def validate_canonical_rom(rom: bytes) -> dict[str, int | str]:
    identity: dict[str, int | str] = {
        "identity": "Chrono Trigger US Rev0 headerless",
        "size": len(rom),
        "sha1": sha1(rom),
        "sha256": sha256(rom),
    }
    if len(rom) != CANONICAL_ROM_SIZE:
        raise AnimationContractError("canonical ROM size mismatch")
    if identity["sha1"] != CANONICAL_ROM_SHA1:
        raise AnimationContractError("canonical ROM SHA-1 mismatch")
    if identity["sha256"] != CANONICAL_ROM_SHA256:
        raise AnimationContractError("canonical ROM SHA-256 mismatch")
    return identity


def verify_current_body_report() -> dict[str, Any]:
    path = ROOT.joinpath(*CURRENT_BODY_REPORT_REL.parts)
    raw = path.read_bytes()
    if len(raw) != CURRENT_BODY_REPORT_SIZE:
        raise AnimationContractError("current-body report size drifted")
    if sha256(raw) != CURRENT_BODY_REPORT_SHA256:
        raise AnimationContractError("current-body report SHA-256 drifted")
    try:
        pinned = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AnimationContractError("current-body report is invalid JSON") from exc

    body_audit = importlib.import_module("audit_schala_current_body_packet")
    rebuilt = body_audit.build_report()
    if body_audit.canonical_report_bytes(rebuilt) != raw:
        raise AnimationContractError(
            "current-body report does not equal a fresh source audit"
        )
    inventory = pinned.get("frame_inventory")
    if not isinstance(inventory, list) or len(inventory) != 16:
        raise AnimationContractError("current-body inventory is not exactly 16 frames")
    frame_ids = [row.get("frame_id") for row in inventory]
    ordinals = [row.get("source_ordinal") for row in inventory]
    if len(set(frame_ids)) != 16 or ordinals != list(range(16)):
        raise AnimationContractError("current-body frame identity/order drifted")
    if pinned.get("scope", {}).get("source_ordinals_are_native_animation_ids"):
        raise AnimationContractError("source ordinals became native animation IDs")
    return pinned


def verify_engine_spans(rom: bytes) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for span in ENGINE_SPANS:
        raw = rom[span.file_start : span.file_end]
        if len(raw) != span.file_end - span.file_start:
            raise AnimationContractError(f"{span.label}: span exceeds ROM")
        if sha256(raw) != span.sha256:
            raise AnimationContractError(f"{span.label}: canonical preimage drifted")
        results.append(
            {
                "label": span.label,
                "source_start": _snes_label(span.file_start),
                "source_end_exclusive": _snes_label(span.file_end),
                "size": len(raw),
                "sha256": span.sha256,
                "claim": span.claim,
                "evidence": "verified-static",
            }
        )
    return results


def verify_pointer_tables(rom: bytes) -> None:
    primary = tuple(
        _read_u16_le(rom, PRIMARY_POINTER_TABLE_FILE + index * 2)
        for index in range(8)
    )
    auxiliary = tuple(
        _read_u16_le(rom, AUX_POINTER_TABLE_FILE + index * 2)
        for index in range(8)
    )
    if primary != EXPECTED_PRIMARY_BOUNDARIES:
        raise AnimationContractError("primary animation boundary table drifted")
    if auxiliary != EXPECTED_AUX_POINTERS:
        raise AnimationContractError("auxiliary animation pointer table drifted")


def _first_value(stream: bytes, value: int, start: int) -> int:
    try:
        return stream.index(value, start)
    except ValueError as exc:
        raise AnimationContractError(
            f"stream has no {value:#04x} terminator at or after {start:#x}"
        ) from exc


def analyze_declared_anchor(
    primary_facing_blocks: Sequence[bytes],
    auxiliary: bytes,
    entrypoint: int,
) -> dict[str, Any]:
    if len(primary_facing_blocks) != FACING_COUNT:
        raise AnimationContractError("declared anchor requires four primary facings")
    if not isinstance(entrypoint, int) or not 0 <= entrypoint <= 0xFF:
        raise AnimationContractError("entrypoint is not one byte")
    start = entrypoint * ENTRYPOINT_STRIDE
    if start >= len(auxiliary):
        raise AnimationContractError("declared entrypoint exceeds auxiliary span")
    if any(len(block) != len(auxiliary) for block in primary_facing_blocks):
        raise AnimationContractError("primary/auxiliary facing span mismatch")

    aux_end = _first_value(auxiliary, AUX_TERMINATOR, start)
    primary_ends = tuple(
        _first_value(block, PRIMARY_TERMINATOR, start)
        for block in primary_facing_blocks
    )
    if len(set(primary_ends)) != 1:
        raise AnimationContractError("primary terminator differs by facing")
    if primary_ends[0] != aux_end:
        raise AnimationContractError(
            "declared anchor primary and auxiliary terminators do not align"
        )
    live_steps = aux_end - start
    if live_steps <= 0:
        raise AnimationContractError("declared anchor has no live step")
    for position in range(start, aux_end):
        if auxiliary[position] == AUX_TERMINATOR:
            raise AnimationContractError("early auxiliary terminator")
        if any(
            block[position] == PRIMARY_TERMINATOR
            for block in primary_facing_blocks
        ):
            raise AnimationContractError("primary FF encountered during live step")
    return {
        "entrypoint": entrypoint,
        "byte_offset": start,
        "live_step_count": live_steps,
        "primary_four_facing_terminators_aligned": True,
        "primary_auxiliary_terminators_aligned": True,
        "evidence": "verified-static",
    }


def validate_overlap_ledger(
    sequences: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    """Validate source-token overlap without compiling a byte stream.

    Each sequence has an integer ``entrypoint`` and equally long
    ``primary_tokens`` / ``auxiliary_tokens`` sequences.  Tokens are abstract
    authoring metadata, not ROM bytes.  Since entrypoint N begins at N*4,
    sequences may overlap; every shared token must agree exactly.
    """

    ledgers: dict[str, dict[int, Any]] = {"primary": {}, "auxiliary": {}}
    for sequence in sequences:
        if set(sequence) != {
            "entrypoint",
            "primary_tokens",
            "auxiliary_tokens",
        }:
            raise AnimationContractError("candidate sequence shape drifted")
        entrypoint = sequence["entrypoint"]
        if not isinstance(entrypoint, int) or not 0 <= entrypoint <= 0xFF:
            raise AnimationContractError("candidate entrypoint is invalid")
        primary_tokens = sequence["primary_tokens"]
        auxiliary_tokens = sequence["auxiliary_tokens"]
        if (
            not isinstance(primary_tokens, (list, tuple))
            or not isinstance(auxiliary_tokens, (list, tuple))
            or len(primary_tokens) != len(auxiliary_tokens)
            or not primary_tokens
        ):
            raise AnimationContractError("candidate token streams are invalid")
        start = entrypoint * ENTRYPOINT_STRIDE
        for stream_name, tokens in (
            ("primary", primary_tokens),
            ("auxiliary", auxiliary_tokens),
        ):
            ledger = ledgers[stream_name]
            for relative, token in enumerate(tokens):
                position = start + relative
                if position in ledger and ledger[position] != token:
                    raise AnimationContractError(
                        f"conflicting {stream_name} token at offset {position:#x}"
                    )
                ledger[position] = token
    return {
        "primary_token_count": len(ledgers["primary"]),
        "auxiliary_token_count": len(ledgers["auxiliary"]),
    }


def analyze_profile(rom: bytes, profile: PcAnimationProfile) -> dict[str, Any]:
    primary_start_file = ANIMATION_BANK_FILE_BASE + profile.primary_start
    primary_end_file = ANIMATION_BANK_FILE_BASE + profile.primary_end
    primary = rom[primary_start_file:primary_end_file]
    if len(primary) != profile.primary_end - profile.primary_start:
        raise AnimationContractError(f"{profile.name}: primary span exceeds ROM")
    if len(primary) % FACING_COUNT:
        raise AnimationContractError(f"{profile.name}: primary span not four-facing")
    if sha256(primary) != profile.primary_sha256:
        raise AnimationContractError(f"{profile.name}: primary hash drifted")
    facing_span = len(primary) // FACING_COUNT
    if facing_span != profile.facing_span or facing_span % ENTRYPOINT_STRIDE:
        raise AnimationContractError(f"{profile.name}: facing span drifted")
    blocks = tuple(
        primary[index * facing_span : (index + 1) * facing_span]
        for index in range(FACING_COUNT)
    )
    ff_masks = tuple(
        tuple(index for index, value in enumerate(block) if value == 0xFF)
        for block in blocks
    )
    if len(set(ff_masks)) != 1:
        raise AnimationContractError(
            f"{profile.name}: primary FF mask differs by facing"
        )

    aux_start_file = ANIMATION_BANK_FILE_BASE + profile.aux_start
    aux_end_file = ANIMATION_BANK_FILE_BASE + profile.aux_contract_end
    auxiliary = rom[aux_start_file:aux_end_file]
    if len(auxiliary) != facing_span:
        raise AnimationContractError(
            f"{profile.name}: auxiliary span is not one facing block"
        )
    if sha256(auxiliary) != profile.aux_sha256:
        raise AnimationContractError(f"{profile.name}: auxiliary hash drifted")
    if any(value & 0x80 for value in auxiliary):
        raise AnimationContractError(
            f"{profile.name}: canonical auxiliary high-bit observation drifted"
        )
    aux_zero_mask = tuple(
        index for index, value in enumerate(auxiliary) if value == AUX_TERMINATOR
    )
    if aux_zero_mask == ff_masks[0]:
        raise AnimationContractError(
            f"{profile.name}: full-block terminator masks unexpectedly equal"
        )

    next_table_pointer = EXPECTED_AUX_POINTERS[profile.pc_id + 1]
    if profile.pc_id < 6:
        if next_table_pointer != profile.aux_contract_end:
            raise AnimationContractError(
                f"{profile.name}: next auxiliary pointer no longer equals end"
            )
        next_pointer_is_end = True
        end_basis = "next playable-character auxiliary pointer"
    else:
        expected_derived_end = profile.aux_start + facing_span
        if profile.aux_contract_end != expected_derived_end:
            raise AnimationContractError("Magus auxiliary derived end drifted")
        if next_table_pointer == profile.aux_contract_end:
            raise AnimationContractError("occupied pointer 7 treated as Magus end")
        if next_table_pointer != 0xB600:
            raise AnimationContractError("occupied auxiliary pointer 7 drifted")
        next_pointer_is_end = False
        end_basis = "derived from primary facing span; tail remains unclassified"

    anchor_sequences = [
        analyze_declared_anchor(blocks, auxiliary, entrypoint)
        for entrypoint in DECLARED_ANCHORS
    ]
    return {
        "pc_id": profile.pc_id,
        "name": profile.name,
        "primary_start": _animation_label(profile.primary_start),
        "primary_end_exclusive": _animation_label(profile.primary_end),
        "primary_size": len(primary),
        "primary_sha256": profile.primary_sha256,
        "facing_span": facing_span,
        "entrypoint_count": facing_span // ENTRYPOINT_STRIDE,
        "primary_ff_mask_equal_across_four_facings": True,
        "auxiliary_start": _animation_label(profile.aux_start),
        "auxiliary_contract_end_exclusive": _animation_label(
            profile.aux_contract_end
        ),
        "auxiliary_size": len(auxiliary),
        "auxiliary_sha256": profile.aux_sha256,
        "auxiliary_high_bit_values_present": False,
        "next_table_pointer": _animation_label(next_table_pointer),
        "next_pointer_is_contract_end": next_pointer_is_end,
        "auxiliary_end_basis": end_basis,
        "full_block_aux_zero_mask_equals_primary_ff_mask": False,
        "declared_anchor_sequences": anchor_sequences,
        "evidence": "verified-static",
    }


def analyze_battle_state_table(rom: bytes) -> dict[str, Any]:
    raw = rom[BATTLE_STATE_TABLE_FILE_START:BATTLE_STATE_TABLE_FILE_END]
    if len(raw) != 0x41 or sha256(raw) != BATTLE_STATE_TABLE_SHA256:
        raise AnimationContractError("battle state animation table drifted")
    records = [raw[index : index + 4] for index in range(0, 0x40, 4)]
    if len(records) != 16 or any(len(record) != 4 for record in records):
        raise AnimationContractError("battle state table record geometry drifted")
    if any(record[0] & 0x80 for record in records):
        raise AnimationContractError("battle state table terminated before record 16")
    if raw[0x40] != 0xFF:
        raise AnimationContractError("battle state table terminator drifted")
    selector_values = tuple(sorted({record[3] for record in records}))
    if selector_values != BATTLE_STATE_SELECTOR_VALUES:
        raise AnimationContractError("battle state selector set drifted")
    return {
        "source_start": _snes_label(BATTLE_STATE_TABLE_FILE_START),
        "source_end_exclusive": _snes_label(BATTLE_STATE_TABLE_FILE_END),
        "size": len(raw),
        "sha256": BATTLE_STATE_TABLE_SHA256,
        "record_count": 16,
        "record_size": 4,
        "table_terminator": 0xFF,
        "selector_values": list(selector_values),
        "selector_ff_dispatches_literally": False,
        "selector_ff_resolution": {
            "when_$A0A7_nonzero": "skip matched record",
            "when_$A0A7_zero": "resolve selector to entrypoint $03",
            "$A0A7_semantic_meaning": "unresolved",
        },
        "evidence": "verified-static",
    }


def build_authoring_coverage(body_report: Mapping[str, Any]) -> list[dict[str, Any]]:
    inventory = body_report["frame_inventory"]
    body_ids = tuple(row["frame_id"] for row in inventory)
    role_ids = tuple(
        frame_id
        for role in AUTHORING_ROLES
        for frame_id in role["current_frame_ids"]
    )
    if len(role_ids) != 16 or len(set(role_ids)) != 16 or role_ids != body_ids:
        raise AnimationContractError("authoring roles do not cover exact body order")
    coverage: list[dict[str, Any]] = []
    for role in AUTHORING_ROLES:
        coverage.append(
            {
                "role_id": role["role_id"],
                "context": role["context"],
                "current_frame_ids": list(role["current_frame_ids"]),
                "coverage": role["coverage"],
                "related_engine_role_ids": list(
                    role["related_engine_role_ids"]
                ),
                "native_binding": None,
                "timing_binding": None,
                "binding_state": "source-role-only-unbound",
                "evidence": "hypothesis",
            }
        )
    return coverage


def validate_metadata_only_report(report: Mapping[str, Any]) -> None:
    if frozenset(report) != EXPECTED_TOP_LEVEL_KEYS:
        raise AnimationContractError("report top-level schema drifted")
    if report.get("status") != "pass-metadata-only-with-open-gates":
        raise AnimationContractError("report status drifted")
    scope = report.get("scope")
    if not isinstance(scope, Mapping):
        raise AnimationContractError("report scope is missing")
    required_false = (
        "rom_installable",
        "animation_blob_emitted",
        "production_hook_assigned",
        "production_allocation_assigned",
        "logical_pc07_runtime_proved",
        "focus_inserts_composited",
        "audio_bound",
    )
    if any(scope.get(key) is not False for key in required_false):
        raise AnimationContractError("report contains a production-facing claim")
    if scope.get("source_only") is not True:
        raise AnimationContractError("report is not source-only")

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in FORBIDDEN_REPORT_KEYS:
                    raise AnimationContractError(
                        f"forbidden metadata key present: {key}"
                    )
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, bytes):
            raise AnimationContractError("raw bytes present in report")

    visit(report)
    encoded = canonical_report_bytes(report).lower()
    for forbidden in (b".sfc", b".smc", b"private/", b"private\\"):
        if forbidden in encoded:
            raise AnimationContractError("private ROM path leaked into report")


def build_report(rom: bytes) -> dict[str, Any]:
    rom_identity = validate_canonical_rom(rom)
    body_report = verify_current_body_report()
    verify_pointer_tables(rom)
    engine_spans = verify_engine_spans(rom)
    profiles = [analyze_profile(rom, profile) for profile in PC_PROFILES]
    state_table = analyze_battle_state_table(rom)
    authoring_coverage = build_authoring_coverage(body_report)

    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "auditor_version": TOOL_VERSION,
        "status": "pass-metadata-only-with-open-gates",
        "scope": {
            "source_only": True,
            "rom_installable": False,
            "animation_blob_emitted": False,
            "production_hook_assigned": False,
            "production_allocation_assigned": False,
            "logical_pc07_runtime_proved": False,
            "source_ordinals_are_native_animation_ids": False,
            "focus_inserts_composited": False,
            "audio_bound": False,
        },
        "inputs": {
            "canonical_rom": rom_identity,
            "current_body_report": {
                "path": CURRENT_BODY_REPORT_REL.as_posix(),
                "size": CURRENT_BODY_REPORT_SIZE,
                "sha256": CURRENT_BODY_REPORT_SHA256,
                "fresh_source_audit_equal": True,
            },
            "disassembly": {
                "path": "references/ct_disassembly",
                "commit": DISASSEMBLY_COMMIT,
                "authority": "labels and commentary only; canonical preimages are authoritative",
            },
        },
        "engine_contract": {
            "facing_order": ["down", "up", "left", "right"],
            "facing_count": FACING_COUNT,
            "entrypoint_stride": ENTRYPOINT_STRIDE,
            "entrypoint_rule": "entrypoint N begins at byte offset N * 4; it is not a fixed four-byte record",
            "overlap_policy": "overlapping or suffix sequences are valid only when every shared source token agrees",
            "primary": {
                "unit": "assembly-frame ID",
                "facing_blocks": 4,
                "field_loop_end_marker": PRIMARY_TERMINATOR,
            },
            "auxiliary": {
                "unit": "delay/control value",
                "facing_blocks": 1,
                "span_equals_one_primary_facing_block": True,
                "field_nonzero_transform": "raw delay",
                "battle_nonzero_transform": "raw delay",
                "zero_behavior": "consumer stop, reset, or repeat branch",
                "prebattle_transform": "raw value shifted right once",
                "prebattle_window": 8,
            },
            "full_block_terminator_masks_are_globally_equivalent": False,
            "declared_anchor_terminators_are_aligned": True,
            "canonical_preimage_spans": engine_spans,
        },
        "canonical_profiles": profiles,
        "consumer_roles": {
            "field": {
                "automatic_entrypoints": [dict(role) for role in FIELD_CONSUMER_ROLES],
                "event_commands": [
                    {
                        "opcode": 0xAA,
                        "role": "play operand animation looped",
                        "namespace": "animation entrypoint",
                    },
                    {
                        "opcode": 0xAB,
                        "role": "play operand animation with count mode",
                        "namespace": "animation entrypoint",
                    },
                    {
                        "opcode": 0xAC,
                        "role": "set static frame directly",
                        "namespace": "assembly-frame ID, not animation entrypoint",
                    },
                    {
                        "opcode": 0xAE,
                        "role": "reset animation to entrypoint 00",
                        "namespace": "animation entrypoint",
                    },
                    {
                        "opcode": 0xB3,
                        "role": "play entrypoint 00 looped",
                        "namespace": "animation entrypoint",
                    },
                    {
                        "opcode": 0xB4,
                        "role": "play entrypoint 01 looped",
                        "namespace": "animation entrypoint",
                    },
                    {
                        "opcode": 0xB7,
                        "role": "play operand animation with count mode",
                        "namespace": "animation entrypoint",
                    },
                ],
                "complete_location_event_operand_census": "open",
            },
            "battle": {
                "play_command": 0x02,
                "fixed_entrypoints": [
                    {
                        "entrypoint": entrypoint,
                        "semantic_role": "unresolved",
                        "evidence": "verified-static",
                    }
                    for entrypoint in BATTLE_FIXED_ENTRYPOINTS
                ],
                "prebattle_fixed_offsets": [
                    {
                        "byte_offset": 0x28,
                        "entrypoint": 0x0A,
                        "semantic_role": "unresolved prebattle branch",
                        "evidence": "verified-static",
                    },
                    {
                        "byte_offset": 0x30,
                        "entrypoint": 0x0C,
                        "semantic_role": "unresolved prebattle branch",
                        "evidence": "verified-static",
                    },
                ],
                "state_selector_table": state_table,
                "critical_hp_override": {
                    "entrypoint": 0x12,
                    "condition": "PC1HPCriticalStatus bit 0 after state-table scan",
                    "evidence": "verified-static",
                },
                "action_package_semantic_census": "open",
            },
        },
        "authoring_coverage": authoring_coverage,
        "open_gates": [
            "Complete the location-event animation operand census with playable-PC object identity, including the AC static-frame namespace.",
            "Map normal attack, cast, item, hurt, KO, revive, victory, and all eight Schala-tech battle action packages to entrypoints without guessing visual semantics.",
            "Give each used Schala role complete facing coverage, an explicit source-frame sequence, a timing policy, and a conflict-free overlap ledger.",
            "Resolve every source frame to a packet record and pass paired primary/auxiliary bounds and terminator validation before emitting an animation blob.",
            "Keep production allocation and fixed-bank adapters closed until named expanded allocations, exact hook preimages, vanilla PC 00-06 equivalence, and the runtime matrix pass.",
        ],
        "evidence": {
            "canonical_engine_contract": "verified-static",
            "canonical_declared_anchor_sequences": "verified-static",
            "current_body_packet_identity": "verified-static",
            "current_frame_to_authoring_role_association": "hypothesis",
            "new_runtime_evidence": "not performed",
        },
        "nonclaims": [
            "This report does not assign a Schala ROM address, expanded allocation, pointer, hook, or production payload.",
            "The 16 source ordinals remain provisional authoring order and are not native animation IDs.",
            "The battle fixed entrypoints are engine anchors, not Schala pose or action bindings.",
            "The state-selector value FF is a proved control case, not a literal animation entrypoint dispatch.",
            "The meaning of $A0A7 remains unresolved even though its two selector-FF branches are statically proved.",
            "No complete animation inventory, auxiliary timing stream, battle sprite, logical PC $07 runtime, Focus insert composition, or audio binding is claimed.",
            "The Magus auxiliary contract ends at $E4:AFB4 by facing-span derivation; $E4:AFB4-$E4:B5FF remains unclassified and is not free space.",
        ],
    }
    validate_metadata_only_report(report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit the source-only Schala animation semantic contract and emit "
            "metadata JSON to stdout."
        )
    )
    parser.add_argument(
        "--rom",
        required=True,
        type=pathlib.Path,
        help="private headerless Chrono Trigger US Rev0 ROM; read-only",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rom = args.rom.read_bytes()
    sys.stdout.buffer.write(canonical_report_bytes(build_report(rom)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
