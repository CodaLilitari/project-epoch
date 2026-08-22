from __future__ import annotations

import binascii
import copy
import hashlib
import os
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
from unittest import mock
import zlib


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "run_mesen_lavos_battle_checkpoint.py"


def load_module(name: str, path: Path) -> types.ModuleType:
    source = path.read_bytes()
    code = compile(source, str(path), "exec", dont_inherit=True)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    module.__loader__ = None
    module.__spec__ = None
    prior = sys.modules.get(name)
    sys.modules[name] = module
    try:
        exec(code, module.__dict__)
    except Exception:
        if prior is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
        raise
    return module


TOOL = load_module(
    "run_mesen_lavos_battle_checkpoint_test",
    TOOL_PATH,
)


def make_command_state(
    *,
    menu_slot: int = 0,
    cursor: int = 0,
    active_ready_pc: int = 0,
    ready_count: int = 3,
    active_battler: int = 0,
    battler_busy: bool = False,
) -> str:
    fields = bytearray(
        (
            0,
            0,
            0,
            0,
            0,
            1,
            2,
            0,
            3,
            0,
            0,
            0,
            0,
        )
    )
    fields[0] = menu_slot
    if menu_slot <= 2:
        fields[1 + menu_slot] = cursor
    fields[7] = active_ready_pc
    fields[8] = ready_count
    if active_ready_pc <= 2:
        fields[4 + active_ready_pc] = active_battler
    if active_battler <= 2:
        fields[9 + active_battler] = 1 if battler_busy else 0
    return fields.hex()


def _trace_row(
    event: str,
    frame: int | str,
    stage: str,
    **overrides: str,
) -> dict[str, str]:
    row = {
        "event": event,
        "frame": str(frame),
        "stage": stage,
        "location": "01db",
        "storyline": "d6",
        "pending": "01",
        "explore": "00",
        "dialog": "00",
        "leader_x": "512",
        "leader_y": "224",
        "active": TOOL.EXPECTED_ACTIVE,
        "roster": TOOL.EXPECTED_ROSTER,
        "joined": "fe",
        "battle_ids": "000102cd0000cc000000cb00",
        "battle_current_hp": "100,200,300,400,500,600",
        "battle_max_hp": "100,200,300,400,500,600",
        "battle_ui": "000000",
        "command_state": make_command_state(),
        "battle_launch_seen": "true",
        "candidate_zero": "true",
        "front_guard_zero": "true",
        "rear_guard_zero": "true",
        "epoch_exact": "true",
        "sram_exact": "true",
    }
    row.update(overrides)
    return row


def canonical_trace_rows() -> list[dict[str, str]]:
    capture_frame = 60 + TOOL.EXPECTED_CAPTURE_OFFSET
    return [
        _trace_row(
            "start",
            0,
            "boot",
            battle_launch_seen="false",
        ),
        _trace_row(
            "stage",
            20,
            "lavos-tunnel-route",
            battle_launch_seen="false",
        ),
        _trace_row(
            "stage",
            40,
            "lavos-dialogue",
            battle_launch_seen="false",
        ),
        _trace_row("battle-launch", 60, "lavos-dialogue"),
        _trace_row("stage", 61, "battle-settle"),
        _trace_row("capture-queued", capture_frame, "battle-settle"),
        _trace_row("success", capture_frame, "battle-settle"),
    ]


def encode_trace(
    rows: list[dict[str, str]],
    *,
    columns: tuple[str, ...] | None = None,
    final_newline: bool = True,
) -> bytes:
    selected_columns = columns or TOOL.TRACE_COLUMNS
    lines = ["\t".join(selected_columns)]
    lines.extend(
        "\t".join(row[column] for column in selected_columns)
        for row in rows
    )
    text = "\n".join(lines)
    if final_newline:
        text += "\n"
    return text.encode("utf-8")


def _verification_row(
    event: str,
    mode: str,
    relative_frame: int,
    *,
    command_state: str,
    **overrides: str,
) -> dict[str, str]:
    row = {
        "event": event,
        "mode": mode,
        "relative_frame": str(relative_frame),
        "location": "01db",
        "storyline": "d6",
        "pending": "01",
        "explore": "00",
        "dialog": "00",
        "active": TOOL.EXPECTED_ACTIVE,
        "roster": TOOL.EXPECTED_ROSTER,
        "joined": "fe",
        "battle_ids": "000102cd0000cc000000cb00",
        "battle_current_hp": "100,200,300,400,500,600",
        "battle_max_hp": "100,200,300,400,500,600",
        "battle_ui": "000000",
        "command_state": command_state,
        "candidate_zero": "true",
        "front_guard_zero": "true",
        "rear_guard_zero": "true",
        "epoch_exact": "true",
        "sram_exact": "true",
    }
    row.update(overrides)
    return row


def verification_trace_rows(mode: str) -> list[dict[str, str]]:
    baseline_state = make_command_state(cursor=0)
    endpoint_state = (
        make_command_state(cursor=1) if mode == "down" else baseline_state
    )
    return [
        _verification_row(
            "baseline",
            mode,
            0,
            command_state=baseline_state,
        ),
        _verification_row(
            "success",
            mode,
            TOOL.EXPECTED_VERIFY_TERMINAL_FRAME,
            command_state=endpoint_state,
        ),
    ]


def encode_verification_trace(rows: list[dict[str, str]]) -> bytes:
    lines = ["\t".join(TOOL.VERIFY_COLUMNS)]
    lines.extend(
        "\t".join(row[column] for column in TOOL.VERIFY_COLUMNS)
        for row in rows
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def deterministic_noise(size: int) -> bytes:
    result = bytearray()
    counter = 0
    while len(result) < size:
        result.extend(
            hashlib.sha256(counter.to_bytes(8, "little")).digest()
        )
        counter += 1
    return bytes(result[:size])


STATE_BYTES = deterministic_noise(70_000)


def build_mesen_state(
    *,
    framebuffer: bytes | None = None,
    state: bytes = STATE_BYTES,
    rom_name_bytes: bytes | None = None,
    compressed_flag: int = 1,
    frame_payload: bytes | None = None,
    state_payload: bytes | None = None,
    declared_state_size: int | None = None,
    stored_state_size: int | None = None,
) -> bytes:
    framebuffer_source = (
        b"\x00" * 122_368 if framebuffer is None else framebuffer
    )
    compressed_frame = (
        zlib.compress(framebuffer_source)
        if frame_payload is None
        else frame_payload
    )
    compressed_state = (
        zlib.compress(state)
        if state_payload is None
        else state_payload
    )
    rom_name = (
        TOOL.FIXED_ROM_NAME.encode("utf-8")
        if rom_name_bytes is None
        else rom_name_bytes
    )
    header = b"MSS" + struct.pack(
        "<8I",
        131_329,
        4,
        0,
        122_368,
        256,
        239,
        100,
        len(compressed_frame),
    )
    state_size = (
        len(state)
        if declared_state_size is None
        else declared_state_size
    )
    stored_size = (
        len(compressed_state)
        if stored_state_size is None
        else stored_state_size
    )
    return b"".join(
        (
            header,
            compressed_frame,
            struct.pack("<I", len(rom_name)),
            rom_name,
            bytes((compressed_flag,)),
            struct.pack("<II", state_size, stored_size),
            compressed_state,
        )
    )


def _test_png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = binascii.crc32(chunk_type)
    checksum = binascii.crc32(data, checksum) & 0xFFFFFFFF
    return b"".join(
        (
            struct.pack(">I", len(data)),
            chunk_type,
            data,
            struct.pack(">I", checksum),
        )
    )


def _test_paeth(left: int, up: int, upper_left: int) -> int:
    predictor = left + up - upper_left
    left_distance = abs(predictor - left)
    up_distance = abs(predictor - up)
    upper_left_distance = abs(predictor - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left


def png_pixel_rows() -> list[bytes]:
    return [
        bytes(
            (
                row_index * 13
                + byte_index * 7
                + (byte_index // 3) * 3
            )
            & 0xFF
            for byte_index in range(256 * 3)
        )
        for row_index in range(224)
    ]


def encode_png_scanlines(
    rows: list[bytes],
    filter_types: list[int],
) -> bytes:
    if len(rows) != len(filter_types):
        raise AssertionError("one filter type is required for every row")
    result = bytearray()
    prior = bytes(256 * 3)
    for row, filter_type in zip(rows, filter_types, strict=True):
        if len(row) != 256 * 3:
            raise AssertionError("synthetic RGB row has the wrong length")
        result.append(filter_type)
        for index, value in enumerate(row):
            left = row[index - 3] if index >= 3 else 0
            up = prior[index]
            upper_left = prior[index - 3] if index >= 3 else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                predictor = _test_paeth(left, up, upper_left)
            else:
                raise AssertionError("cannot encode an unknown PNG filter")
            result.append((value - predictor) & 0xFF)
        prior = row
    return bytes(result)


def build_rgb_png_from_filtered(
    filtered: bytes,
    *,
    compression_level: int,
    idat_count: int,
) -> bytes:
    ihdr = struct.pack(
        ">IIBBBBB",
        256,
        224,
        8,
        2,
        0,
        0,
        0,
    )
    compressed = zlib.compress(filtered, compression_level)
    boundaries = [
        index * len(compressed) // idat_count
        for index in range(idat_count + 1)
    ]
    idat_chunks = b"".join(
        _test_png_chunk(
            b"IDAT",
            compressed[boundaries[index] : boundaries[index + 1]],
        )
        for index in range(idat_count)
    )
    return b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _test_png_chunk(b"IHDR", ihdr),
            idat_chunks,
            _test_png_chunk(b"IEND", b""),
        )
    )


def build_rgb_png(
    rows: list[bytes],
    filter_types: list[int],
    *,
    compression_level: int,
    idat_count: int,
) -> bytes:
    return build_rgb_png_from_filtered(
        encode_png_scanlines(rows, filter_types),
        compression_level=compression_level,
        idat_count=idat_count,
    )


class RunMesenLavosBattleCheckpointTests(unittest.TestCase):
    def test_source_and_base_launcher_pins_are_current(self) -> None:
        base_source = TOOL.BASE_LAUNCHER_PATH.read_bytes()
        self.assertEqual(
            hashlib.sha256(base_source).hexdigest(),
            TOOL.BASE_LAUNCHER_SHA256,
        )
        collector_source = TOOL.COLLECTOR_PATH.read_bytes()
        self.assertEqual(len(collector_source), TOOL.COLLECTOR_SIZE)
        self.assertEqual(
            hashlib.sha256(collector_source).hexdigest(),
            TOOL.COLLECTOR_SHA256,
        )
        self.assertEqual(
            TOOL._require_collector_source(),
            collector_source,
        )
        verifier_source = TOOL.VERIFIER_PATH.read_bytes()
        self.assertEqual(len(verifier_source), TOOL.VERIFIER_SIZE)
        self.assertEqual(
            hashlib.sha256(verifier_source).hexdigest(),
            TOOL.VERIFIER_SHA256,
        )
        self.assertEqual(
            TOOL._require_verifier_source(),
            verifier_source,
        )
        acceptance_source = TOOL.ACCEPTANCE_CONTRACT_PATH.read_bytes()
        self.assertEqual(
            len(acceptance_source),
            TOOL.ACCEPTANCE_CONTRACT_SIZE,
        )
        self.assertEqual(
            hashlib.sha256(acceptance_source).hexdigest(),
            TOOL.ACCEPTANCE_CONTRACT_SHA256,
        )
        (
            loaded_acceptance_source,
            acceptance_contract,
            accepted_artifacts,
        ) = TOOL._load_acceptance_contract()
        self.assertEqual(loaded_acceptance_source, acceptance_source)
        self.assertEqual(
            acceptance_contract["schema"],
            TOOL.ACCEPTANCE_CONTRACT_SCHEMA,
        )
        self.assertEqual(
            accepted_artifacts,
            {
                "battle_ready.mss": (
                    261_614,
                    (
                        "d5825ffff2f2a3b7edbe3c37e7118155"
                        "d67727dc02ed672d13257f3824482b8b"
                    ),
                ),
                "checkpoint.tsv": (
                    3_528,
                    (
                        "96c382cfb4d8bae0c30b3236d1fe2b6e"
                        "ed50972b2fccc5713f76e645cf8e89ef"
                    ),
                ),
                "fresh_load_control.tsv": (
                    641,
                    (
                        "e591c2e06780a8fef987eed869e70fdc"
                        "2d1744cfba179a4f9283ad3ec303881e"
                    ),
                ),
                "fresh_load_down.tsv": (
                    635,
                    (
                        "d8540c90e28a43c64307ace78cef746b"
                        "97a6715aa8ac76dc8132e2fcd9ecc52b"
                    ),
                ),
            },
        )
        self.assertIsNone(TOOL.BASE.__loader__)
        self.assertIsNone(TOOL.BASE.__spec__)
        self.assertEqual(
            set(TOOL.RUNTIME_HASHES),
            set(TOOL.PINNED_SIZES),
        )
        for digest in TOOL.RUNTIME_HASHES.values():
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
        launcher_source = TOOL_PATH.read_text(encoding="utf-8")
        self.assertNotIn("SourceFileLoader", launcher_source)
        self.assertNotIn("spec_from_file_location", launcher_source)

    def test_exact_deterministic_artifact_acceptance_fails_closed(
        self,
    ) -> None:
        outputs = {
            name: f"synthetic exact {name}\n".encode("ascii")
            for name in TOOL.DETERMINISTIC_ARTIFACT_NAMES
        }
        expected = {
            name: (len(source), hashlib.sha256(source).hexdigest())
            for name, source in outputs.items()
        }
        self.assertEqual(
            TOOL._verify_accepted_deterministic_artifacts(
                outputs,
                expected,
            ),
            {
                name: {
                    "size": len(source),
                    "sha256": hashlib.sha256(source).hexdigest(),
                }
                for name, source in outputs.items()
            },
        )

        changed = dict(outputs)
        changed["fresh_load_down.tsv"] += b"drift"
        with self.assertRaisesRegex(
            TOOL.TraceLaunchError,
            "does not match accepted deterministic artifact",
        ):
            TOOL._verify_accepted_deterministic_artifacts(
                changed,
                expected,
            )

        missing = dict(outputs)
        del missing["checkpoint.tsv"]
        with self.assertRaisesRegex(
            TOOL.TraceLaunchError,
            "artifact set is incomplete or unexpected",
        ):
            TOOL._verify_accepted_deterministic_artifacts(
                missing,
                expected,
            )

        unexpected = dict(outputs)
        unexpected["endpoint.png"] = b"not accepted"
        with self.assertRaisesRegex(
            TOOL.TraceLaunchError,
            "artifact set is incomplete or unexpected",
        ):
            TOOL._verify_accepted_deterministic_artifacts(
                unexpected,
                expected,
            )

    def test_presentation_policy_is_explicit_and_fails_closed(
        self,
    ) -> None:
        _, contract, _ = TOOL._load_acceptance_contract()
        for key, value in (
            ("accepted_deterministic_artifact", True),
            ("hash_gated_for_acceptance", True),
            ("may_vary_between_equivalent_runs", False),
            ("artifacts", ["endpoint.png"]),
            ("per_run_manifest", "checkpoint.json"),
        ):
            with self.subTest(key=key):
                drifted = copy.deepcopy(contract)
                drifted["presentation_policy"][key] = value
                with self.assertRaisesRegex(
                    TOOL.TraceLaunchError,
                    "presentation policy",
                ):
                    TOOL._validate_acceptance_contract(drifted)

        deterministic_outputs = {
            name: f"synthetic {name}\n".encode("ascii")
            for name in TOOL.DETERMINISTIC_ARTIFACT_NAMES
        }
        checkpoint_sections = TOOL._checkpoint_artifact_sections(
            deterministic_outputs
        )
        self.assertEqual(
            set(checkpoint_sections["artifacts"]),
            set(TOOL.DETERMINISTIC_ARTIFACT_NAMES),
        )
        for name in TOOL.PRESENTATION_ARTIFACT_NAMES:
            self.assertNotIn(name, checkpoint_sections["artifacts"])
        policy = checkpoint_sections["artifact_policy"]
        self.assertFalse(policy["presentation_artifacts_accepted"])
        self.assertFalse(
            policy["presentation_hash_gated_for_acceptance"]
        )
        self.assertEqual(
            policy["presentation_metadata"],
            "presentation_manifest.json",
        )

        rows = png_pixel_rows()
        endpoint = build_rgb_png(
            rows,
            [0] * len(rows),
            compression_level=6,
            idat_count=1,
        )
        changed_rows = list(rows)
        changed_first = bytearray(changed_rows[0])
        changed_first[0] ^= 0x01
        changed_rows[0] = bytes(changed_first)
        command_down = build_rgb_png(
            changed_rows,
            [0] * len(changed_rows),
            compression_level=6,
            idat_count=1,
        )
        presentation = TOOL._build_presentation_manifest(
            {
                "endpoint.png": endpoint,
                "command_down.png": command_down,
            }
        )
        self.assertFalse(presentation["accepted_deterministic_artifact"])
        self.assertFalse(presentation["hash_gated_for_acceptance"])
        self.assertNotEqual(
            presentation["artifacts"]["endpoint.png"]["sha256"],
            presentation["artifacts"]["command_down.png"]["sha256"],
        )
        for record in presentation["artifacts"].values():
            self.assertEqual(record["evidence_level"], "verified-runtime")
            self.assertEqual(
                record["acceptance_role"],
                "supporting-presentation-only",
            )

    def test_canonical_checkpoint_trace_parses(self) -> None:
        document = TOOL.parse_checkpoint_trace(
            encode_trace(canonical_trace_rows())
        )
        self.assertEqual(document["schema"], TOOL.TRACE_SCHEMA)
        self.assertEqual(document["version"], 1)
        self.assertEqual(
            document["status"],
            "exploratory-native-checkpoint",
        )
        self.assertEqual(
            document["capture_queued_frames_after_battle_launch"],
            TOOL.EXPECTED_CAPTURE_OFFSET,
        )
        self.assertEqual(
            document["_absolute_endpoint_frame"],
            60 + TOOL.EXPECTED_CAPTURE_OFFSET,
        )
        endpoint = document["endpoint"]
        self.assertNotIn("frame", endpoint)
        self.assertEqual(endpoint["leader_x"], 512)
        self.assertEqual(
            endpoint["battle_current_hp"],
            [100, 200, 300, 400, 500, 600],
        )
        self.assertEqual(
            endpoint["battle_max_hp"],
            [100, 200, 300, 400, 500, 600],
        )
        self.assertEqual(
            endpoint["command_state"],
            make_command_state(),
        )
        self.assertEqual(
            TOOL._command_cursor(
                endpoint["command_state"],
                "synthetic checkpoint command state",
            ),
            (0, 0),
        )
        self.assertTrue(endpoint["sram_exact"])

    def test_fresh_load_control_and_down_verification_traces_parse(
        self,
    ) -> None:
        control = TOOL.parse_verification_trace(
            encode_verification_trace(verification_trace_rows("control")),
            "control",
        )
        down = TOOL.parse_verification_trace(
            encode_verification_trace(verification_trace_rows("down")),
            "down",
        )
        self.assertEqual(control["mode"], "control")
        self.assertEqual(down["mode"], "down")
        self.assertEqual(control["baseline"]["relative_frame"], 0)
        self.assertEqual(
            control["endpoint"]["relative_frame"],
            TOOL.EXPECTED_VERIFY_TERMINAL_FRAME,
        )
        self.assertEqual(
            down["baseline"]["command_state"],
            control["baseline"]["command_state"],
        )

        control_slot, control_cursor = TOOL._command_cursor(
            control["endpoint"]["command_state"],
            "synthetic control endpoint",
        )
        down_slot, down_cursor = TOOL._command_cursor(
            down["endpoint"]["command_state"],
            "synthetic Down endpoint",
        )
        self.assertEqual(control_slot, down_slot)
        self.assertEqual(down_cursor, (control_cursor + 1) % 3)

        comparable_control = {
            key: value
            for key, value in control["endpoint"].items()
            if key not in {"mode", "battle_ui", "command_state"}
        }
        comparable_down = {
            key: value
            for key, value in down["endpoint"].items()
            if key not in {"mode", "battle_ui", "command_state"}
        }
        self.assertEqual(comparable_control, comparable_down)

    def test_control_verification_restores_baseline_cursor(self) -> None:
        control = TOOL.parse_verification_trace(
            encode_verification_trace(verification_trace_rows("control")),
            "control",
        )
        baseline_state = control["baseline"]["command_state"]
        endpoint_state = control["endpoint"]["command_state"]
        self.assertEqual(endpoint_state, baseline_state)
        self.assertEqual(
            TOOL._command_cursor(
                endpoint_state,
                "synthetic control endpoint",
            ),
            TOOL._command_cursor(
                baseline_state,
                "synthetic control baseline",
            ),
        )

    def test_verification_trace_rejects_non_ready_command_state(
        self,
    ) -> None:
        rows = verification_trace_rows("control")
        rows[-1]["command_state"] = make_command_state(
            battler_busy=True,
        )
        with self.assertRaisesRegex(
            TOOL.TraceLaunchError,
            "active battler is not menu-ready",
        ):
            TOOL.parse_verification_trace(
                encode_verification_trace(rows),
                "control",
            )

    def test_command_cursor_validates_state_and_supports_wraparound(
        self,
    ) -> None:
        for before, after in ((0, 1), (1, 2), (2, 0)):
            with self.subTest(before=before, after=after):
                before_slot, before_cursor = TOOL._command_cursor(
                    make_command_state(cursor=before),
                    "synthetic before command state",
                )
                after_slot, after_cursor = TOOL._command_cursor(
                    make_command_state(cursor=after),
                    "synthetic after command state",
                )
                self.assertEqual(before_slot, after_slot)
                self.assertEqual(after_cursor, (before_cursor + 1) % 3)

        invalid_states = (
            (
                "menu slot",
                make_command_state(menu_slot=3),
                "active menu slot is invalid",
            ),
            (
                "cursor",
                make_command_state(cursor=3),
                "cursor row is invalid",
            ),
            (
                "ready count",
                make_command_state(ready_count=0),
                "ready-PC state is invalid",
            ),
            (
                "busy battler",
                make_command_state(battler_busy=True),
                "active battler is not menu-ready",
            ),
        )
        for label, state, message in invalid_states:
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    TOOL.TraceLaunchError,
                    message,
                ):
                    TOOL._command_cursor(state, f"synthetic {label}")

    def test_checkpoint_trace_rejects_noncanonical_and_unsafe_variants(
        self,
    ) -> None:
        cases: list[tuple[str, bytes, str]] = []

        rows = canonical_trace_rows()
        rows[3]["event"] = "unknown"
        cases.append(("unknown event", encode_trace(rows), "unknown event"))

        rows = canonical_trace_rows()
        rows[4]["frame"] = "59"
        cases.append(("frame reversal", encode_trace(rows), "not monotonic"))

        rows = canonical_trace_rows()
        rows[-1]["leader_x"] = "0512"
        cases.append(("leading zero", encode_trace(rows), "leading zero"))

        rows = canonical_trace_rows()
        rows[-1]["location"] = "01DB"
        cases.append(
            ("uppercase hex", encode_trace(rows), "canonical lowercase hex")
        )

        rows = canonical_trace_rows()
        rows[-1]["epoch_exact"] = "yes"
        cases.append(("invalid boolean", encode_trace(rows), "invalid epoch_exact"))

        rows = [
            row
            for row in canonical_trace_rows()
            if row["event"] != "battle-launch"
        ]
        cases.append(
            (
                "missing launch",
                encode_trace(rows),
                "milestone order or cardinality drifted",
            )
        )

        rows = [
            row
            for row in canonical_trace_rows()
            if row["event"] != "capture-queued"
        ]
        cases.append(
            (
                "missing capture",
                encode_trace(rows),
                "milestone order or cardinality drifted",
            )
        )

        rows = [
            row
            for row in canonical_trace_rows()
            if row["stage"] != "lavos-dialogue"
        ]
        cases.append(
            (
                "missing stage",
                encode_trace(rows),
                "milestone order or cardinality drifted",
            )
        )

        rows = canonical_trace_rows()
        rows[-1]["pending"] = "21"
        cases.append(
            (
                "pending 21",
                encode_trace(rows),
                "gameplay anchor drifted",
            )
        )

        rows = canonical_trace_rows()
        rows[-1]["battle_current_hp"] = "100,200,0,400,500,600"
        cases.append(
            (
                "zero current HP",
                encode_trace(rows),
                "not alive at full HP",
            )
        )

        rows = canonical_trace_rows()
        rows[-1]["battle_current_hp"] = "99,200,300,400,500,600"
        cases.append(
            (
                "non-full current HP",
                encode_trace(rows),
                "not alive at full HP",
            )
        )

        rows = canonical_trace_rows()
        rows.insert(2, dict(rows[1]))
        cases.append(
            (
                "duplicate milestone",
                encode_trace(rows),
                "milestone order or cardinality drifted",
            )
        )

        rows = canonical_trace_rows()
        rows[1], rows[2] = rows[2], rows[1]
        rows[1]["frame"] = "20"
        rows[2]["frame"] = "40"
        cases.append(
            (
                "reordered milestones",
                encode_trace(rows),
                "milestone order or cardinality drifted",
            )
        )

        rows = canonical_trace_rows()
        rows[-1]["event"] = "failure"
        cases.append(
            (
                "failure milestone",
                encode_trace(rows),
                "milestone order or cardinality drifted",
            )
        )

        rows = canonical_trace_rows()
        bad_capture_frame = 60 + TOOL.EXPECTED_CAPTURE_OFFSET - 1
        rows[-2]["frame"] = str(bad_capture_frame)
        rows[-1]["frame"] = str(bad_capture_frame)
        cases.append(
            (
                "capture offset",
                encode_trace(rows),
                "fixed battle offset",
            )
        )

        rows = canonical_trace_rows()
        rows[-1]["active"] = "000103"
        cases.append(
            ("terminal anchor", encode_trace(rows), "gameplay anchor drifted")
        )

        rows = canonical_trace_rows()
        rows[-1]["battle_ids"] = "00" * 12
        cases.append(
            ("battle identity", encode_trace(rows), "identity drifted in slot 1")
        )

        rows = canonical_trace_rows()
        rows[-1]["battle_max_hp"] = "100,200,0,400,500,600"
        cases.append(
            ("zero max HP", encode_trace(rows), "not alive at full HP")
        )

        rows = canonical_trace_rows()
        rows[-1]["candidate_zero"] = "false"
        cases.append(
            (
                "protected invariant",
                encode_trace(rows),
                "protected invariant failed: candidate_zero",
            )
        )

        rows = canonical_trace_rows()
        cases.append(
            (
                "header drift",
                encode_trace(rows, columns=TOOL.TRACE_COLUMNS[:-1]),
                "header drifted",
            )
        )
        cases.append(
            (
                "missing final newline",
                encode_trace(rows, final_newline=False),
                "canonical LF lines",
            )
        )
        cases.append(
            (
                "CRLF",
                encode_trace(rows).replace(b"\n", b"\r\n"),
                "canonical LF lines",
            )
        )
        cases.append(("invalid UTF-8", b"\xff" * 100, "not UTF-8"))

        for label, source, message in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    TOOL.TraceLaunchError,
                    message,
                ):
                    TOOL.parse_checkpoint_trace(source)

    def test_valid_synthetic_mesen_state_envelope_parses(self) -> None:
        source = build_mesen_state()
        self.assertGreaterEqual(len(source), 64 * 1024)
        document = TOOL.parse_mesen_state(source)
        self.assertEqual(document["emulator_version"], 131_329)
        self.assertEqual(document["format_version"], 4)
        self.assertEqual(document["console_type"], 0)
        self.assertEqual(document["framebuffer_size"], 122_368)
        self.assertEqual(document["width"], 256)
        self.assertEqual(document["height"], 239)
        self.assertEqual(document["scale"], 100)
        self.assertEqual(document["rom_name"], TOOL.FIXED_ROM_NAME)
        self.assertEqual(document["decoded_state_size"], len(STATE_BYTES))

    def test_mesen_state_rejects_malformed_envelopes_and_payloads(
        self,
    ) -> None:
        valid = build_mesen_state()
        bad_magic = b"BAD" + valid[3:]

        header_drift = bytearray(valid)
        struct.pack_into("<I", header_drift, 3, 131_330)

        screenshot_truncated = bytearray(valid)
        struct.pack_into("<I", screenshot_truncated, 3 + 7 * 4, len(valid))

        invalid_frame_zlib = build_mesen_state(
            frame_payload=b"x" * 100,
        )
        short_framebuffer = build_mesen_state(
            framebuffer=b"\x00" * 122_367,
        )
        invalid_rom_utf8 = build_mesen_state(rom_name_bytes=b"\xff")
        wrong_rom = build_mesen_state(rom_name_bytes=b"other.sfc")
        uncompressed = build_mesen_state(compressed_flag=0)
        bad_stored_size = build_mesen_state(
            stored_state_size=len(zlib.compress(STATE_BYTES)) + 1,
        )
        invalid_state_zlib = build_mesen_state(
            state_payload=b"x" * 66_000,
        )
        wrong_decoded_size = build_mesen_state(
            declared_state_size=len(STATE_BYTES) + 1,
        )

        cases = (
            ("too small", b"MSS", "state size is invalid"),
            ("bad magic", bad_magic, "state magic is invalid"),
            (
                "header drift",
                bytes(header_drift),
                "header fields drifted",
            ),
            (
                "screenshot truncated",
                bytes(screenshot_truncated),
                "screenshot payload is truncated",
            ),
            (
                "invalid frame zlib",
                invalid_frame_zlib,
                "screenshot payload is not valid zlib",
            ),
            (
                "framebuffer length",
                short_framebuffer,
                "screenshot payload zlib envelope or length drifted",
            ),
            (
                "invalid ROM UTF-8",
                invalid_rom_utf8,
                "ROM name is not UTF-8",
            ),
            ("wrong ROM", wrong_rom, "ROM name drifted"),
            (
                "uncompressed state",
                uncompressed,
                "state payload is not compressed",
            ),
            (
                "stored size drift",
                bad_stored_size,
                "payload lengths drifted",
            ),
            (
                "invalid state zlib",
                invalid_state_zlib,
                "state payload is not valid zlib",
            ),
            (
                "decoded state length",
                wrong_decoded_size,
                "state payload zlib envelope or length drifted",
            ),
        )
        for label, source, message in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    TOOL.TraceLaunchError,
                    message,
                ):
                    TOOL.parse_mesen_state(source)

    def test_zlib_stored_round_trips_empty_and_multiblock_inputs(
        self,
    ) -> None:
        sources = (
            b"",
            b"canonical",
            deterministic_noise(65_535),
            deterministic_noise(65_536),
            deterministic_noise(131_071),
        )
        for source in sources:
            with self.subTest(size=len(source)):
                encoded = TOOL._zlib_stored(source)
                self.assertEqual(encoded[:2], b"\x78\x01")
                self.assertEqual(zlib.decompress(encoded), source)
                self.assertEqual(TOOL._zlib_stored(source), encoded)

    def test_exact_zlib_decoder_rejects_trailing_overlong_and_incomplete(
        self,
    ) -> None:
        trailing = zlib.compress(b"abc") + b"trailing"
        overlong = zlib.compress(b"abcd")
        incomplete = zlib.compress(b"abc")[:-2]
        cases = (
            (
                "trailing",
                trailing,
                3,
                "zlib envelope or length drifted",
            ),
            (
                "overlong",
                overlong,
                3,
                "exceeds its decoded length",
            ),
            (
                "incomplete",
                incomplete,
                3,
                "zlib envelope or length drifted",
            ),
        )
        for label, source, expected, message in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    TOOL.TraceLaunchError,
                    message,
                ):
                    TOOL._decompress_exact(
                        source,
                        expected,
                        f"synthetic {label} stream",
                    )

    def test_equivalent_png_encodings_canonicalize_identically(self) -> None:
        rows = png_pixel_rows()
        zero_filter_png = build_rgb_png(
            rows,
            [0] * len(rows),
            compression_level=1,
            idat_count=1,
        )
        mixed_filter_png = build_rgb_png(
            rows,
            [index % 5 for index in range(len(rows))],
            compression_level=9,
            idat_count=3,
        )
        self.assertNotEqual(zero_filter_png, mixed_filter_png)

        canonical_zero = TOOL.canonicalize_png(zero_filter_png)
        canonical_mixed = TOOL.canonicalize_png(mixed_filter_png)
        self.assertEqual(canonical_zero, canonical_mixed)
        self.assertEqual(
            TOOL.canonicalize_png(canonical_zero),
            canonical_zero,
        )

        ihdr = struct.pack(">IIBBBBB", 256, 224, 8, 2, 0, 0, 0)
        unfiltered = b"".join(b"\x00" + row for row in rows)
        expected = b"".join(
            (
                b"\x89PNG\r\n\x1a\n",
                _test_png_chunk(b"IHDR", ihdr),
                _test_png_chunk(b"IDAT", TOOL._zlib_stored(unfiltered)),
                _test_png_chunk(b"IEND", b""),
            )
        )
        self.assertEqual(canonical_zero, expected)

    def test_png_canonicalization_rejects_bad_crc_and_filter(self) -> None:
        rows = png_pixel_rows()
        valid = build_rgb_png(
            rows,
            [0] * len(rows),
            compression_level=6,
            idat_count=1,
        )
        bad_crc = bytearray(valid)
        bad_crc[-1] ^= 0x01
        with self.assertRaisesRegex(
            TOOL.TraceLaunchError,
            "chunk CRC is invalid",
        ):
            TOOL.canonicalize_png(bytes(bad_crc))

        filtered = bytearray(encode_png_scanlines(rows, [0] * len(rows)))
        filtered[0] = 5
        unknown_filter = build_rgb_png_from_filtered(
            bytes(filtered),
            compression_level=6,
            idat_count=1,
        )
        with self.assertRaisesRegex(
            TOOL.TraceLaunchError,
            "uses an unknown filter",
        ):
            TOOL.canonicalize_png(unknown_filter)

    def test_mesen_preview_normalization_preserves_serialized_core_hash(
        self,
    ) -> None:
        first = build_mesen_state(
            framebuffer=b"\x00" * 122_368,
        )
        second_frame = bytes(
            (index * 29 + 17) & 0xFF
            for index in range(122_368)
        )
        second = build_mesen_state(framebuffer=second_frame)
        self.assertNotEqual(first, second)

        first_before = TOOL.parse_mesen_state(first)
        second_before = TOOL.parse_mesen_state(second)
        expected_core_hash = hashlib.sha256(STATE_BYTES).hexdigest()
        self.assertEqual(
            first_before["decoded_state_sha256"],
            expected_core_hash,
        )
        self.assertEqual(
            second_before["decoded_state_sha256"],
            expected_core_hash,
        )
        self.assertNotEqual(
            first_before["framebuffer_sha256"],
            second_before["framebuffer_sha256"],
        )

        canonical_first = TOOL.canonicalize_mesen_state(first)
        canonical_second = TOOL.canonicalize_mesen_state(second)
        self.assertEqual(canonical_first, canonical_second)
        self.assertEqual(
            TOOL.canonicalize_mesen_state(canonical_first),
            canonical_first,
        )

        after = TOOL.parse_mesen_state(canonical_first)
        self.assertEqual(after["decoded_state_sha256"], expected_core_hash)
        self.assertEqual(
            after["framebuffer_sha256"],
            hashlib.sha256(bytes(122_368)).hexdigest(),
        )

    def test_accepted_contract_gate_precedes_source_or_private_resolution(
        self,
    ) -> None:
        args = TOOL.build_parser().parse_args(
            [
                "--output-dir",
                "private/test_runs/never-created",
            ]
        )
        self.assertFalse(args.exploratory)
        with mock.patch.object(
            TOOL,
            "_load_acceptance_contract",
            side_effect=TOOL.TraceLaunchError(
                "synthetic acceptance contract mismatch"
            ),
        ) as acceptance:
            with mock.patch.object(
                TOOL,
                "_require_collector_source",
                side_effect=AssertionError("collector must not be read"),
            ) as collector:
                with mock.patch.object(
                    TOOL.BASE,
                    "resolve_private_file",
                    side_effect=AssertionError(
                        "private paths must not resolve"
                    ),
                ) as resolve:
                    with self.assertRaisesRegex(
                        TOOL.TraceLaunchError,
                        "acceptance contract mismatch",
                    ):
                        TOOL.run(args)
        acceptance.assert_called_once_with()
        collector.assert_not_called()
        resolve.assert_not_called()

    def test_exploratory_bypasses_only_the_acceptance_claim_gate(
        self,
    ) -> None:
        args = TOOL.build_parser().parse_args(
            [
                "--output-dir",
                "private/test_runs/never-created",
                "--exploratory",
            ]
        )
        self.assertTrue(args.exploratory)
        with mock.patch.object(
            TOOL,
            "_load_acceptance_contract",
            side_effect=AssertionError(
                "exploratory run must not load accepted outputs"
            ),
        ) as acceptance:
            with mock.patch.object(
                TOOL,
                "_require_collector_source",
                side_effect=TOOL.TraceLaunchError(
                    "synthetic collector reached"
                ),
            ) as collector:
                with self.assertRaisesRegex(
                    TOOL.TraceLaunchError,
                    "collector reached",
                ):
                    TOOL.run(args)
        acceptance.assert_not_called()
        collector.assert_called_once_with()

    def test_private_output_guards_reject_escape_overlap_and_existing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory).resolve(strict=True)
            workspace = temporary_root / "workspace"
            private_root = workspace / "private"
            private_root.mkdir(parents=True)
            shared_saves = private_root / "tools" / "mesen2" / "Saves"
            shared_saves.mkdir(parents=True)
            existing = private_root / "existing"
            existing.mkdir()

            with mock.patch.object(TOOL.BASE, "ROOT", workspace):
                with self.assertRaisesRegex(
                    TOOL.TraceLaunchError,
                    "resolves outside",
                ):
                    TOOL.BASE.prepare_private_output_dir(
                        temporary_root / "outside"
                    )
                with self.assertRaisesRegex(
                    TOOL.TraceLaunchError,
                    "overlaps protected tree",
                ):
                    TOOL.BASE.prepare_private_output_dir(
                        shared_saves / "output",
                        forbidden_roots=(shared_saves,),
                    )
                with self.assertRaisesRegex(
                    TOOL.TraceLaunchError,
                    "must be a new path",
                ):
                    TOOL.BASE.prepare_private_output_dir(existing)

                created = TOOL.BASE.prepare_private_output_dir(
                    private_root / "new-output"
                )
                self.assertTrue(created.is_dir())
                created.relative_to(private_root)

    def test_output_publication_is_exclusive_and_preserves_existing_file(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory).resolve(strict=True)
            victim = output_dir / "checkpoint.tsv"
            victim.write_bytes(b"preexisting")
            with self.assertRaisesRegex(
                TOOL.TraceLaunchError,
                "refusing to overwrite",
            ):
                TOOL._publish_outputs(
                    output_dir,
                    {"checkpoint.tsv": b"replacement"},
                )
            self.assertEqual(victim.read_bytes(), b"preexisting")

            records = TOOL._publish_outputs(
                output_dir,
                {
                    "battle_ready.mss": b"state",
                    "endpoint.png": b"png",
                },
            )
            self.assertEqual(
                set(records),
                {"battle_ready.mss", "endpoint.png"},
            )
            self.assertEqual(
                (output_dir / "battle_ready.mss").read_bytes(),
                b"state",
            )
            for filename, row in records.items():
                source = (output_dir / filename).read_bytes()
                self.assertEqual(row["size"], len(source))
                self.assertEqual(
                    row["sha256"],
                    hashlib.sha256(source).hexdigest(),
                )

    def test_later_publication_failure_rolls_back_only_new_artifacts(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory).resolve(strict=True)
            preexisting = output_dir / "endpoint.png"
            preexisting.write_bytes(b"preexisting endpoint")
            with self.assertRaisesRegex(
                TOOL.TraceLaunchError,
                "refusing to overwrite",
            ):
                TOOL._publish_outputs(
                    output_dir,
                    {
                        "battle_ready.mss": b"new state",
                        "checkpoint.tsv": b"new trace",
                        "endpoint.png": b"replacement endpoint",
                        "checkpoint.json": b"never reached",
                    },
                )
            self.assertFalse(
                os.path.lexists(output_dir / "battle_ready.mss")
            )
            self.assertFalse(os.path.lexists(output_dir / "checkpoint.tsv"))
            self.assertFalse(
                os.path.lexists(output_dir / "checkpoint.json")
            )
            self.assertEqual(
                preexisting.read_bytes(),
                b"preexisting endpoint",
            )


if __name__ == "__main__":
    unittest.main()
