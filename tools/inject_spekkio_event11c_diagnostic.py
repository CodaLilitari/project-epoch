#!/usr/bin/env python3
"""Prepare a private current-bsnes event-$11C diagnostic checkpoint.

The input is a raw-state BSV2 checkpoint captured while the player is
controllable and facing Spekkio in location $01D1. The tool changes only the
explicit volatile WRAM fields needed to enter the canonical magic-grant call.
It never writes a ROM or SRAM and refuses outputs outside private/.

This is diagnostic state preparation, not a valid gameplay save, an installed
compatibility relocation, or evidence that the candidate WRAM range is free.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import pathlib

import edit_retroarch_bsv2_inputs as bsv2
import inject_bsv2_wram_canary as current_state


WRAM_BASE = current_state.PINNED_CURRENT_WRAM_STATE_OFFSET
STATE_LENGTH = current_state.PINNED_CURRENT_STATE_LENGTH
STATE_PREFIX = current_state.PINNED_CURRENT_CORE_PREFIX

LOCATION_OFFSET = 0x0100
EXPLORE_MODE_OFFSET = 0x011F
DIALOG_STATE_OFFSET = 0x0162
STORYLINE_OFFSET = 0x10000
MAGIC_FLAGS_OFFSET = 0x101E0
ROBO_FLAGS_OFFSET = 0x101E2
LAP_SCRATCH_OFFSET = 0x1021C
ACTIVE_PARTY_OFFSET = 0x2980

CANDIDATE_START = 0x2CA0
CANDIDATE_END = 0x2CF0
FRONT_GUARD_START = 0x2C9C
REAR_GUARD_END = 0x2D00
EPOCH_NAME_START = 0x2C4D
EPOCH_NAME_END = 0x2C53


class DiagnosticError(RuntimeError):
    """Raised when a checkpoint is unsafe or outside the pinned contract."""


@dataclasses.dataclass(frozen=True)
class Profile:
    name: str
    active_party: bytes
    clear_magic_bits: int
    clear_robo_bits: int
    tech_count_offsets: tuple[int, ...]
    learned_mask_offsets: tuple[int, ...]
    remaining_tp_offsets: tuple[int, ...]


PROFILES = {
    "crono-marle-lucca": Profile(
        name="crono-marle-lucca",
        active_party=bytes((0x00, 0x01, 0x02)),
        clear_magic_bits=0x47,
        clear_robo_bits=0,
        tech_count_offsets=(0x2830, 0x2831, 0x2832),
        learned_mask_offsets=(0x2837, 0x2838, 0x2839),
        remaining_tp_offsets=(0x262D, 0x267D, 0x26CD),
    ),
    "frog-robo": Profile(
        name="frog-robo",
        active_party=bytes((0x06, 0x04, 0x03)),
        clear_magic_bits=0x18,
        clear_robo_bits=0x01,
        tech_count_offsets=(0x2834,),
        learned_mask_offsets=(0x283B,),
        remaining_tp_offsets=(0x276D,),
    ),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_zero(core_state: bytes, start: int, end: int, label: str) -> None:
    if any(core_state[WRAM_BASE + start:WRAM_BASE + end]):
        raise DiagnosticError(f"{label} is not all zero")


def _set_byte(
    changed: bytearray,
    allowed: set[int],
    wram_offset: int,
    value: int,
) -> None:
    state_offset = WRAM_BASE + wram_offset
    changed[state_offset] = value & 0xFF
    allowed.add(state_offset)


def _set_word_zero(
    changed: bytearray,
    allowed: set[int],
    wram_offset: int,
) -> None:
    _set_byte(changed, allowed, wram_offset, 0)
    _set_byte(changed, allowed, wram_offset + 1, 0)


def inject_diagnostic(
    movie: bytes,
    *,
    profile_name: str,
    expected_core_sha256: str,
) -> tuple[bytes, dict[str, object]]:
    if profile_name not in PROFILES:
        raise DiagnosticError(f"unknown diagnostic profile: {profile_name}")
    if (
        len(expected_core_sha256) != 64
        or any(character not in "0123456789abcdef"
               for character in expected_core_sha256.lower())
    ):
        raise DiagnosticError("expected core SHA-256 is malformed")

    info = bsv2.parse_movie(movie)
    core_state = current_state.extract_raw_initial_core_state(movie)
    if len(core_state) != STATE_LENGTH or not core_state.startswith(
        STATE_PREFIX
    ):
        raise DiagnosticError("checkpoint is not pinned current-bsnes 115.1")
    source_core_sha256 = sha256(core_state)
    if source_core_sha256 != expected_core_sha256.lower():
        raise DiagnosticError("checkpoint core SHA-256 does not match pin")

    location = int.from_bytes(
        core_state[
            WRAM_BASE + LOCATION_OFFSET:WRAM_BASE + LOCATION_OFFSET + 2
        ],
        "little",
    )
    if location != 0x01D1:
        raise DiagnosticError("checkpoint is not in Spekkio location $01D1")
    if core_state[WRAM_BASE + EXPLORE_MODE_OFFSET] != 1:
        raise DiagnosticError("checkpoint is not in controllable field mode")
    if core_state[WRAM_BASE + DIALOG_STATE_OFFSET] != 0:
        raise DiagnosticError("checkpoint already has an active dialogue")

    source_party = core_state[
        WRAM_BASE + ACTIVE_PARTY_OFFSET:
        WRAM_BASE + ACTIVE_PARTY_OFFSET + 3
    ]
    if (
        len(set(source_party)) != 3
        or any(pc_id > 6 for pc_id in source_party)
    ):
        raise DiagnosticError("source active party is invalid or contains PC $07")

    _require_zero(
        core_state,
        FRONT_GUARD_START,
        CANDIDATE_START,
        "candidate front guard",
    )
    _require_zero(
        core_state,
        CANDIDATE_START,
        CANDIDATE_END,
        "candidate range",
    )
    _require_zero(
        core_state,
        CANDIDATE_END,
        REAR_GUARD_END,
        "candidate rear guard",
    )
    epoch_before = core_state[
        WRAM_BASE + EPOCH_NAME_START:WRAM_BASE + EPOCH_NAME_END
    ]

    profile = PROFILES[profile_name]
    changed = bytearray(core_state)
    allowed: set[int] = set()
    _set_byte(changed, allowed, STORYLINE_OFFSET, 0x4C)
    _set_byte(changed, allowed, LAP_SCRATCH_OFFSET, 0x03)
    _set_byte(
        changed,
        allowed,
        MAGIC_FLAGS_OFFSET,
        core_state[WRAM_BASE + MAGIC_FLAGS_OFFSET]
        & (~profile.clear_magic_bits & 0xFF),
    )
    if profile.clear_robo_bits:
        _set_byte(
            changed,
            allowed,
            ROBO_FLAGS_OFFSET,
            core_state[WRAM_BASE + ROBO_FLAGS_OFFSET]
            & (~profile.clear_robo_bits & 0xFF),
        )
    for index, pc_id in enumerate(profile.active_party):
        _set_byte(
            changed,
            allowed,
            ACTIVE_PARTY_OFFSET + index,
            pc_id,
        )
    for offset in profile.tech_count_offsets:
        _set_byte(changed, allowed, offset, 0)
    for offset in profile.learned_mask_offsets:
        _set_byte(
            changed,
            allowed,
            offset,
            core_state[WRAM_BASE + offset] & 0x1F,
        )
    for offset in profile.remaining_tp_offsets:
        _set_word_zero(changed, allowed, offset)

    differences = {
        index
        for index, (before, after) in enumerate(
            zip(core_state, changed, strict=True)
        )
        if before != after
    }
    if not differences:
        raise DiagnosticError("diagnostic preparation made no changes")
    if differences - allowed:
        raise AssertionError("diagnostic write escaped the explicit allowlist")
    if not {
        WRAM_BASE + STORYLINE_OFFSET,
        WRAM_BASE + LAP_SCRATCH_OFFSET,
    } <= differences:
        raise DiagnosticError("storyline/lap setup was already synthetic")

    result = bsv2.replace_initial_core_state(movie, bytes(changed))
    result_info = bsv2.parse_movie(result)
    source_frames = movie[
        bsv2.HEADER_SIZE + info.initial_state.size:
    ]
    result_frames = result[
        bsv2.HEADER_SIZE + result_info.initial_state.size:
    ]
    if result_frames != source_frames:
        raise AssertionError("diagnostic preparation changed replay frames")
    final_core_state = current_state.extract_raw_initial_core_state(result)
    if (
        final_core_state[
            WRAM_BASE + EPOCH_NAME_START:WRAM_BASE + EPOCH_NAME_END
        ]
        != epoch_before
    ):
        raise AssertionError("diagnostic preparation changed the Epoch name")
    _require_zero(
        final_core_state,
        FRONT_GUARD_START,
        REAR_GUARD_END,
        "candidate plus guards",
    )

    manifest = {
        "profile": profile.name,
        "source_movie_sha256": sha256(movie),
        "source_core_sha256": source_core_sha256,
        "output_movie_sha256": sha256(result),
        "output_core_sha256": sha256(final_core_state),
        "location": location,
        "source_active_party_hex": source_party.hex(),
        "prepared_active_party_hex": profile.active_party.hex(),
        "changed_state_offsets": sorted(differences),
        "changed_wram_offsets": sorted(
            offset - WRAM_BASE for offset in differences
        ),
        "replay_frames_preserved": True,
        "candidate_and_guards_zero": True,
        "epoch_name_preserved": True,
        "classification": "private-volatile-diagnostic-only",
    }
    return result, manifest


def validate_private_output(path: pathlib.Path) -> pathlib.Path:
    workspace = pathlib.Path(__file__).resolve().parents[1]
    private_root = (workspace / "private").resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise DiagnosticError("output must remain under private/") from exc
    if resolved.suffix.lower() != ".bsv":
        raise DiagnosticError("output must use the .bsv replay suffix")
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("movie", type=pathlib.Path)
    parser.add_argument("--profile", required=True, choices=sorted(PROFILES))
    parser.add_argument("--expected-core-sha256", required=True)
    parser.add_argument("-o", "--out", required=True, type=pathlib.Path)
    args = parser.parse_args()

    source = args.movie.read_bytes()
    result, manifest = inject_diagnostic(
        source,
        profile_name=args.profile,
        expected_core_sha256=args.expected_core_sha256,
    )
    output = validate_private_output(args.out)
    if output.exists() and output.read_bytes() != result:
        raise DiagnosticError(f"refusing to overwrite changed output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(result)
    for key, value in manifest.items():
        print(f"{key}={value}")
    print(f"wrote={output}")


if __name__ == "__main__":
    main()
