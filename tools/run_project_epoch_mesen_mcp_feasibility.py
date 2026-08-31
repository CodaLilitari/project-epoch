#!/usr/bin/env python3
"""Exercise the Project Epoch Mesen adapter through real MCP stdio.

The runner starts the source-controlled MCP server as a child, negotiates MCP,
launches the one pinned disposable Mesen profile, performs bounded reads, and
captures `$7E2980-$7E2982` for exactly 600 zero-input frames.  It then compares
the complete normalized callback sequence with the already accepted field-idle
collector trace.  A private receipt is published only after the emulator stops,
all immutable/staged inputs pass rehashing, and the disposable root is deleted.

This verifies the adapter, not a new Chrono Trigger fact or production hook.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
from typing import Any


ROOT = Path(__file__).resolve(strict=True).parents[1]
PRIVATE_ROOT = (ROOT / "private").resolve(strict=False)
SERVER = ROOT / "tools" / "project_epoch_mesen_mcp_server.py"
BRIDGE = ROOT / "tools" / "project_epoch_mesen_mcp_bridge.lua"
ACCEPTED_TRACE = (
    PRIVATE_ROOT
    / "test_runs"
    / "mesen2"
    / "wram_ownership_accepted_v2"
    / "field-idle"
    / "zero"
    / "trace.json"
)
ACCEPTED_TRACE_SIZE = 50_208
ACCEPTED_TRACE_SHA256 = (
    "d6a5d0cbbd39708a7970108d1027a99b42e8b6ded2d7558d55998fa958dc1168"
)
EXPECTED_TOOLS = [
    "start_disposable_session",
    "session_status",
    "read_wram",
    "read_cpu_state",
    "capture_wram_accesses",
    "stop_disposable_session",
]


class FeasibilityError(RuntimeError):
    """Raised when MCP, emulator, or comparison evidence fails closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_json_object(data: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise FeasibilityError(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=reject_duplicates)
    except FeasibilityError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise FeasibilityError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise FeasibilityError(f"{label} must contain one JSON object")
    return value


def inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def prepare_output_dir(raw_path: Path) -> Path:
    private_root = PRIVATE_ROOT.resolve(strict=True)
    candidate = raw_path if raw_path.is_absolute() else ROOT / raw_path
    if os.path.lexists(candidate):
        raise FeasibilityError(f"output directory must be a new path: {candidate}")
    resolved = candidate.resolve(strict=False)
    if not inside(resolved, private_root):
        raise FeasibilityError("output directory must be under private/")
    resolved.mkdir(parents=True, exist_ok=False)
    resolved = resolved.resolve(strict=True)
    if not inside(resolved, private_root):
        raise FeasibilityError("created output directory escaped private/")
    return resolved


class McpStdioClient:
    def __init__(self, stderr_path: Path) -> None:
        self.stderr_handle = stderr_path.open("xb")
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.process = subprocess.Popen(
            [sys.executable, str(SERVER)],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr_handle,
            creationflags=creation_flags,
        )
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        self.stdin = self.process.stdin
        self.stdout = self.process.stdout
        self.responses: queue.Queue[bytes | None] = queue.Queue()
        self.reader = threading.Thread(target=self._reader, daemon=True)
        self.reader.start()
        self.next_id = 1

    def _reader(self) -> None:
        while True:
            line = self.stdout.readline()
            if not line:
                self.responses.put(None)
                return
            self.responses.put(line)

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self.stdin.write(
            json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"
        )
        self.stdin.flush()

    def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float = 60.0,
    ) -> Any:
        request_id = self.next_id
        self.next_id += 1
        message: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            message["params"] = params
        self.stdin.write(
            json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"
        )
        self.stdin.flush()
        try:
            raw = self.responses.get(timeout=timeout)
        except queue.Empty as exc:
            raise FeasibilityError(f"timed out waiting for MCP method {method}") from exc
        if raw is None:
            raise FeasibilityError(
                f"MCP server exited while waiting for {method}; code={self.process.poll()}"
            )
        response = decode_json_object(raw, f"MCP {method} response")
        if response.get("jsonrpc") != "2.0" or response.get("id") != request_id:
            raise FeasibilityError(f"MCP {method} response identity mismatch")
        if "error" in response:
            raise FeasibilityError(f"MCP {method} failed: {response['error']}")
        if "result" not in response:
            raise FeasibilityError(f"MCP {method} response has no result")
        return response["result"]

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        result = self.request(
            "tools/call",
            {"name": name, "arguments": arguments},
            timeout=timeout,
        )
        if not isinstance(result, dict):
            raise FeasibilityError(f"MCP tool {name} result is not an object")
        if result.get("isError") is True:
            raise FeasibilityError(f"MCP tool {name} returned an error: {result}")
        structured = result.get("structuredContent")
        if not isinstance(structured, dict):
            raise FeasibilityError(f"MCP tool {name} has no structured content")
        return structured

    def close(self) -> int:
        try:
            self.stdin.close()
        except OSError:
            pass
        try:
            return_code = self.process.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                return_code = self.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
                return_code = self.process.wait(timeout=5.0)
        self.stdout.close()
        self.stderr_handle.close()
        return return_code


def accepted_normalized_records(trace: dict[str, Any]) -> list[dict[str, Any]]:
    if trace.get("scenario") != "field-idle" or trace.get("variant") != "zero":
        raise FeasibilityError("accepted trace scenario/variant drifted")
    callbacks = trace.get("callbacks")
    if not isinstance(callbacks, list) or len(callbacks) != 450:
        raise FeasibilityError("accepted callback count drifted")
    result: list[dict[str, Any]] = []
    for index, row in enumerate(callbacks):
        if not isinstance(row, dict) or row.get("seq") != index:
            raise FeasibilityError("accepted callback sequence drifted")
        result.append(
            {
                "sequence": index,
                "frame": row.get("frame"),
                "access": row.get("access"),
                "address": row.get("address"),
                "value": row.get("value"),
                "pc24": row.get("pc24"),
            }
        )
    return result


def observed_normalized_records(capture: dict[str, Any]) -> list[dict[str, Any]]:
    rows = capture.get("records")
    if not isinstance(rows, list):
        raise FeasibilityError("MCP capture has no record list")
    return [
        {
            "sequence": row.get("sequence"),
            "frame": row.get("frame"),
            "access": row.get("access"),
            "address": row.get("address"),
            "value": row.get("value"),
            "pc24": row.get("pc24"),
        }
        for row in rows
        if isinstance(row, dict)
    ]


def run(output_dir: Path) -> dict[str, Any]:
    output = prepare_output_dir(output_dir)
    receipt_path = output / "receipt.json"
    stderr_path = output / "mcp_server.stderr.txt"

    accepted_size = ACCEPTED_TRACE.stat().st_size
    accepted_hash = sha256_file(ACCEPTED_TRACE)
    if accepted_size != ACCEPTED_TRACE_SIZE or accepted_hash != ACCEPTED_TRACE_SHA256:
        raise FeasibilityError("accepted field-idle trace identity drifted")
    accepted_source = ACCEPTED_TRACE.read_bytes()
    if hashlib.sha256(accepted_source).hexdigest() != accepted_hash:
        raise FeasibilityError("accepted trace changed while being captured")
    accepted = decode_json_object(accepted_source, "accepted field-idle trace")
    expected_records = accepted_normalized_records(accepted)

    source_before = {
        "server": {
            "size": SERVER.stat().st_size,
            "sha256": sha256_file(SERVER),
        },
        "bridge": {
            "size": BRIDGE.stat().st_size,
            "sha256": sha256_file(BRIDGE),
        },
        "accepted_trace": {
            "size": accepted_size,
            "sha256": accepted_hash,
        },
    }

    client = McpStdioClient(stderr_path)
    session_started = False
    session_stopped = False
    start_result: dict[str, Any] | None = None
    status_result: dict[str, Any] | None = None
    roster_result: dict[str, Any] | None = None
    protected_result: dict[str, Any] | None = None
    cpu_result: dict[str, Any] | None = None
    capture_result: dict[str, Any] | None = None
    stop_result: dict[str, Any] | None = None
    close_code: int | None = None
    primary_error: Exception | None = None
    try:
        initialized = client.request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {
                    "name": "project-epoch-mesen-feasibility",
                    "version": "1",
                },
            },
        )
        if (
            not isinstance(initialized, dict)
            or initialized.get("protocolVersion") != "2025-06-18"
            or initialized.get("serverInfo", {}).get("name") != "project-epoch-mesen"
            or "Never treat" not in str(initialized.get("instructions"))
        ):
            raise FeasibilityError("MCP initialization contract drifted")
        client.notify("notifications/initialized")
        tools = client.request("tools/list", {})
        tool_rows = tools.get("tools") if isinstance(tools, dict) else None
        if not isinstance(tool_rows, list):
            raise FeasibilityError("MCP tools/list result is malformed")
        tool_names = [row.get("name") for row in tool_rows if isinstance(row, dict)]
        if tool_names != EXPECTED_TOOLS or "execute_lua" in tool_names:
            raise FeasibilityError("MCP tool allowlist drifted")

        start_result = client.call_tool(
            "start_disposable_session",
            {"profile": "event11c-checkpoint-v5-spekkio-talkable"},
        )
        session_started = True
        if (
            start_result.get("acceptance_evidence") is not False
            or start_result.get("writes_available") is not False
            or start_result.get("arbitrary_lua_available") is not False
            or start_result.get("client_paths_accepted") is not False
        ):
            raise FeasibilityError("start result weakened the safety boundary")

        status_result = client.call_tool("session_status", {})
        if status_result.get("active") is not True:
            raise FeasibilityError("MCP session did not report active")
        roster_result = client.call_tool(
            "read_wram",
            {"offset": 0x2980, "length": 3},
        )
        if roster_result.get("hex") != "060403":
            raise FeasibilityError("checkpoint roster preimage drifted")
        protected_result = client.call_tool(
            "read_wram",
            {"offset": 0x2C9C, "length": 0x64},
        )
        if protected_result.get("hex") != "00" * 0x64:
            raise FeasibilityError("candidate/guard preimage drifted")
        cpu_result = client.call_tool("read_cpu_state", {})
        if not isinstance(cpu_result.get("cpu"), dict):
            raise FeasibilityError("CPU-state tool returned no CPU object")
        capture_result = client.call_tool(
            "capture_wram_accesses",
            {
                "start_offset": 0x2980,
                "end_offset": 0x2982,
                "access": "read",
                "frames": 600,
                "record_limit": 512,
            },
        )
        observed_records = observed_normalized_records(capture_result)
        if len(observed_records) != len(expected_records) or not observed_records:
            raise FeasibilityError("MCP capture callback count drifted")
        relative_frame_alignment_delta = (
            expected_records[0]["frame"] - observed_records[0]["frame"]
        )
        if relative_frame_alignment_delta not in {-1, 0, 1, 2}:
            raise FeasibilityError("MCP capture phase translation exceeded one cadence")
        aligned_observed_records = [
            {
                **row,
                "frame": row["frame"] + relative_frame_alignment_delta,
            }
            for row in observed_records
        ]
        if aligned_observed_records != expected_records:
            raise FeasibilityError(
                "MCP capture did not reproduce the accepted phase-normalized callbacks"
            )
        if (
            capture_result.get("record_count") != 450
            or capture_result.get("overflow") is not False
            or capture_result.get("dropped_records") != 0
            or capture_result.get("observer_error") is not None
            or capture_result.get("pre_hex") != "060403"
            or capture_result.get("post_hex") != "060403"
        ):
            raise FeasibilityError("MCP capture summary drifted")

        stop_result = client.call_tool("stop_disposable_session", {})
        session_stopped = True
        required_true = (
            "immutable_sources_preserved",
            "shared_mesen_saves_preserved",
            "disposable_rom_preserved",
            "disposable_sram_preserved",
            "disposable_checkpoint_preserved",
            "bridge_source_preserved",
            "disposable_staging_deleted",
        )
        if any(stop_result.get(key) is not True for key in required_true):
            raise FeasibilityError("MCP stop/integrity receipt drifted")
    except Exception as exc:
        primary_error = exc
        if session_started and not session_stopped:
            try:
                client.call_tool("stop_disposable_session", {}, timeout=20.0)
                session_stopped = True
            except Exception:
                pass
    finally:
        close_code = client.close()

    if primary_error is not None:
        raise primary_error
    if close_code != 0:
        raise FeasibilityError(f"MCP server returned {close_code}, expected 0")
    assert capture_result is not None
    assert stop_result is not None

    source_after = {
        "server": {"size": SERVER.stat().st_size, "sha256": sha256_file(SERVER)},
        "bridge": {"size": BRIDGE.stat().st_size, "sha256": sha256_file(BRIDGE)},
        "accepted_trace": {
            "size": ACCEPTED_TRACE.stat().st_size,
            "sha256": sha256_file(ACCEPTED_TRACE),
        },
    }
    if source_after != source_before:
        raise FeasibilityError("tracked source or accepted trace changed during replay")

    callback_bytes = json.dumps(
        aligned_observed_records,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    receipt = {
        "schema": "project-epoch-mesen-mcp-feasibility-receipt-v1",
        "status": "verified-runtime-bounded-known-scenario-phase-normalized-reproduction",
        "evidence_label": "verified-runtime",
        "mcp_output_classification": "exploratory-only",
        "production_authority": False,
        "new_chrono_trigger_fact_claimed": False,
        "profile": "event11c-checkpoint-v5-spekkio-talkable",
        "mcp_protocol": "2025-06-18",
        "tool_allowlist": EXPECTED_TOOLS,
        "security": {
            "arbitrary_lua": False,
            "client_supplied_paths": False,
            "emulator_memory_write_api": False,
            "controller_input": "fixed-empty-player-1",
            "network_listener": False,
        },
        "source_artifacts": source_before,
        "comparison": {
            "accepted_trace_scenario": "field-idle/zero",
            "phase_normalized_exact_callback_sequence_match": True,
            "byte_exact_trace_match_claimed": False,
            "frames": 600,
            "record_count": 450,
            "normalized_callbacks_sha256": hashlib.sha256(callback_bytes).hexdigest(),
            "raw_first_frame": observed_records[0]["frame"],
            "raw_last_frame": observed_records[-1]["frame"],
            "relative_frame_alignment_delta": relative_frame_alignment_delta,
            "aligned_first_frame": expected_records[0]["frame"],
            "aligned_last_frame": expected_records[-1]["frame"],
            "reader_pc24": expected_records[0]["pc24"],
            "address_value_counts": [
                {"address": 0x7E2980, "value": 0x06, "count": 150},
                {"address": 0x7E2981, "value": 0x04, "count": 150},
                {"address": 0x7E2982, "value": 0x03, "count": 150},
            ],
            "pre_hex": capture_result["pre_hex"],
            "post_hex": capture_result["post_hex"],
            "overflow": capture_result["overflow"],
            "dropped_records": capture_result["dropped_records"],
            "observer_error": capture_result["observer_error"],
        },
        "integrity": {
            key: stop_result[key]
            for key in (
                "immutable_sources_preserved",
                "shared_mesen_saves_preserved",
                "disposable_rom_preserved",
                "disposable_sram_preserved",
                "disposable_checkpoint_preserved",
                "bridge_source_preserved",
                "disposable_staging_deleted",
            )
        },
        "nonclaims": [
            "not a production PC $07 hook or allocation",
            "not a save, New Game+, erase, menu, or battle integration proof",
            "not evidence that arbitrary MCP observations are accepted",
            "not permission to expose arbitrary Lua or emulator write operations",
        ],
    }
    with receipt_path.open("xb") as handle:
        encoded = json.dumps(receipt, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    receipt["receipt"] = {
        "size": receipt_path.stat().st_size,
        "sha256": sha256_file(receipt_path),
    }
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run(args.output_dir)
    except (FeasibilityError, OSError, subprocess.SubprocessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
