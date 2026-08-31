#!/usr/bin/env python3
"""Hardened, project-scoped MCP control plane for Project Epoch's Mesen 2.

The server intentionally implements only a closed set of named operations.
It never accepts Lua, a shell command, a filesystem path, a ROM byte write, or
an arbitrary controller sequence from an MCP client.  Every emulator process
uses pinned inputs copied into a unique ignored private session directory.

This is an exploratory runtime tool.  Its output is never acceptance evidence;
any useful observation must be promoted into a tracked deterministic collector
and independently replayed through Project Epoch's established harness.
"""

from __future__ import annotations

import argparse
import atexit
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
import threading
import time
from typing import Any, BinaryIO, Mapping


ROOT = Path(__file__).resolve(strict=True).parents[1]
PRIVATE_ROOT = (ROOT / "private").resolve(strict=False)
BRIDGE_SOURCE = ROOT / "tools" / "project_epoch_mesen_mcp_bridge.lua"
BRIDGE_SHA256 = (
    "7dc6212483e20f5725763ee9a649d445fa0518a4669a351456ddc22d98b036e0"
)

SERVER_NAME = "project-epoch-mesen"
SERVER_VERSION = "0.1.0"
MCP_PROTOCOL_VERSION = "2025-06-18"
BRIDGE_PROTOCOL = "project-epoch-mesen-mcp-bridge-v1"
PROFILE_ID = "event11c-checkpoint-v5-spekkio-talkable"
EXPECTED_MESEN_EXIT_CODE = 47

MAX_JSON_LINE_BYTES = 2 * 1024 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_READ_BYTES = 256
MAX_CAPTURE_SPAN = 256
MAX_CAPTURE_FRAMES = 1800
MAX_CAPTURE_RECORDS = 1024

SESSION_BASE = PRIVATE_ROOT / "test_runs" / "mesen_mcp"

SOURCE_SPECS: dict[str, tuple[Path, int, str]] = {
    "archive": (
        PRIVATE_ROOT / "tools" / "mesen2" / "Mesen_2.1.1_Windows.zip",
        34_058_170,
        "23ccc2bc060b663c68dad3a8c5d6da7d23a50f872d04f135bafa2b04ff7d5cbe",
    ),
    "mesen": (
        PRIVATE_ROOT / "tools" / "mesen2" / "app" / "Mesen.exe",
        70_470_144,
        "d2eb03c2590c648bf329f127ebcfefd70130e7690a9e2ccdba8616faea1fe96b",
    ),
    "mesen_core": (
        PRIVATE_ROOT / "tools" / "mesen2" / "app" / "MesenCore.dll",
        7_143_424,
        "65f69a7bdb25c35fdca77c9c73e71ef3e8ec233380204d94cfc0179933048c74",
    ),
    "harfbuzz": (
        PRIVATE_ROOT / "tools" / "mesen2" / "app" / "libHarfBuzzSharp.dll",
        1_804_872,
        "eb76238c9e8e41d44b5a5b18167c4c5b39ca5db4277af5dbe92d730f0fc14a7d",
    ),
    "skia": (
        PRIVATE_ROOT / "tools" / "mesen2" / "app" / "libSkiaSharp.dll",
        9_414_216,
        "9a0d95e8caaa852c70d085af6a40a744242172ad9ea3fd6bc7599875a8a1dbcd",
    ),
    "nesdb": (
        PRIVATE_ROOT / "tools" / "mesen2" / "app" / "MesenNesDB.txt",
        559_118,
        "cff835b8a3d5b07d9d111382da6c49ccae150cdbaa9a0e49e15aa381af471307",
    ),
    "settings": (
        PRIVATE_ROOT / "tools" / "mesen2" / "app" / "settings.json",
        3,
        "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356",
    ),
    "rom": (
        PRIVATE_ROOT
        / "test_runs"
        / "mesen2"
        / "event11c_checkpoint_v5"
        / "project_epoch_mesen_event11c_clean.sfc",
        4_194_304,
        "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9",
    ),
    "state": (
        PRIVATE_ROOT
        / "test_runs"
        / "mesen2"
        / "event11c_checkpoint_v5"
        / "spekkio_talkable.mss",
        133_993,
        "26788b52f63a32a7539d8acb18495df1a458064f700d5411916e2bfc34c4522e",
    ),
    "sram": (
        PRIVATE_ROOT
        / "tools"
        / "mesen2"
        / "app"
        / "Saves"
        / "project_epoch_mesen_event11c_clean.srm",
        8_192,
        "a94c9df27a6ff8200064a35f80531a4964de0334e361b7ba8b147a21c40b27d9",
    ),
}

RUNTIME_NAMES = {
    "mesen": "Mesen.exe",
    "mesen_core": "MesenCore.dll",
    "harfbuzz": "libHarfBuzzSharp.dll",
    "skia": "libSkiaSharp.dll",
    "nesdb": "MesenNesDB.txt",
    "settings": "settings.json",
}

INSTRUCTIONS = (
    "Project Epoch exploratory emulator only. Never treat this server's output "
    "as acceptance or production evidence. It launches only a pinned disposable "
    "Mesen checkpoint; it exposes no Lua, paths, ROM/WRAM/SRAM writes, shell, or "
    "arbitrary input. Stop the disposable session when finished. Promote any "
    "useful finding into a tracked deterministic collector and independently "
    "replay it before changing architecture, mappings, hooks, or allocations."
)


class ProjectEpochMcpError(RuntimeError):
    """Raised when a safety, protocol, or emulator invariant fails."""


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular_private_file(path: Path, label: str) -> Path:
    try:
        private_root = PRIVATE_ROOT.resolve(strict=True)
    except OSError as exc:
        raise ProjectEpochMcpError("workspace private directory is missing") from exc
    if private_root != PRIVATE_ROOT or not private_root.is_dir():
        raise ProjectEpochMcpError("workspace private directory is redirected")
    try:
        metadata = path.stat(follow_symlinks=False)
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ProjectEpochMcpError(f"{label} is missing") from exc
    if not stat.S_ISREG(metadata.st_mode) or not resolved.is_file():
        raise ProjectEpochMcpError(f"{label} is not a regular file")
    if resolved != path or not _inside(resolved, private_root):
        raise ProjectEpochMcpError(f"{label} is redirected or outside private/")
    return resolved


def _verify_source_specs() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for label, (path, expected_size, expected_hash) in SOURCE_SPECS.items():
        resolved = _regular_private_file(path, label)
        actual_size = resolved.stat().st_size
        if actual_size != expected_size:
            raise ProjectEpochMcpError(
                f"{label} size mismatch: expected {expected_size}, got {actual_size}"
            )
        actual_hash = _sha256_file(resolved)
        if actual_hash != expected_hash:
            raise ProjectEpochMcpError(
                f"{label} SHA-256 mismatch: expected {expected_hash}, got {actual_hash}"
            )
        result[label] = {"size": actual_size, "sha256": actual_hash}
    return result


def _bridge_security_audit() -> dict[str, Any]:
    source = BRIDGE_SOURCE.read_bytes()
    actual_hash = hashlib.sha256(source).hexdigest()
    if actual_hash != BRIDGE_SHA256:
        raise ProjectEpochMcpError(
            f"bridge SHA-256 mismatch: expected {BRIDGE_SHA256}, got {actual_hash}"
        )
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProjectEpochMcpError("bridge source is not UTF-8") from exc

    forbidden = {
        "dynamic load": r"(?<![A-Za-z0-9_])load\s*\(",
        "dofile": r"(?<![A-Za-z0-9_])dofile\s*\(",
        "require": r"(?<![A-Za-z0-9_])require\s*\(",
        "package access": r"\bpackage\s*\.",
        "debug access": r"\bdebug\s*\.",
        "host command": r"\bos\s*\.\s*execute\b",
        "host pipe": r"\bio\s*\.\s*popen\b",
        "emulator memory write": r"\bemu\s*\.\s*write(?:8|16|32)?\s*\(",
    }
    for label, pattern in forbidden.items():
        if re.search(pattern, text):
            raise ProjectEpochMcpError(f"bridge contains forbidden {label}")

    required = (
        "project-epoch-mesen-mcp-bridge-v1",
        "emu.loadSavestate(serialized_state)",
        "emu.addMemoryCallback",
        "emu.removeMemoryCallback",
        "emu.setInput(empty_input(), 0)",
        "MAX_CAPTURE_RECORDS = 1024",
    )
    for token in required:
        if token not in text:
            raise ProjectEpochMcpError(f"bridge required invariant is missing: {token}")
    return {
        "path": "tools/project_epoch_mesen_mcp_bridge.lua",
        "size": len(source),
        "sha256": actual_hash,
        "arbitrary_lua": False,
        "emulator_memory_write_api": False,
        "client_supplied_paths": False,
    }


def _snapshot_regular_files(root: Path) -> dict[str, tuple[int, str]]:
    resolved_root = root.resolve(strict=True)
    if not resolved_root.is_dir() or not _inside(resolved_root, PRIVATE_ROOT):
        raise ProjectEpochMcpError("snapshot root is not a private directory")
    result: dict[str, tuple[int, str]] = {}
    for candidate in sorted(resolved_root.rglob("*")):
        metadata = candidate.stat(follow_symlinks=False)
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise ProjectEpochMcpError("private snapshot contains a non-regular entry")
        resolved = candidate.resolve(strict=True)
        if not _inside(resolved, resolved_root):
            raise ProjectEpochMcpError("private snapshot entry escaped its root")
        relative = resolved.relative_to(resolved_root).as_posix()
        result[relative] = (metadata.st_size, _sha256_file(resolved))
    return result


def _atomic_write(path: Path, data: bytes) -> None:
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        temporary.unlink()
    with temporary.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _decode_json_object(data: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ProjectEpochMcpError(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=reject_duplicates)
    except ProjectEpochMcpError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ProjectEpochMcpError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ProjectEpochMcpError(f"{label} must be one JSON object")
    return value


def _parse_bridge_response(
    raw: bytes,
    *,
    expected_sequence: int,
    expected_token: str,
) -> tuple[str, dict[str, Any]]:
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ProjectEpochMcpError("bridge response exceeds maximum size")
    parts = raw.split(b"\n", 5)
    if len(parts) != 6 or parts[0] != b"PEMCP1":
        raise ProjectEpochMcpError("bridge response framing is malformed")
    try:
        sequence = int(parts[1].removeprefix(b"SEQ:"), 10)
        token = parts[2].removeprefix(b"TOKEN:").decode("ascii")
        status = parts[3].removeprefix(b"STATUS:").decode("ascii")
        length = int(parts[4].removeprefix(b"LEN:"), 10)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ProjectEpochMcpError("bridge response header is malformed") from exc
    if not parts[1].startswith(b"SEQ:") or not parts[2].startswith(b"TOKEN:"):
        raise ProjectEpochMcpError("bridge response identity header is malformed")
    if not parts[3].startswith(b"STATUS:") or not parts[4].startswith(b"LEN:"):
        raise ProjectEpochMcpError("bridge response status header is malformed")
    if sequence != expected_sequence or token != expected_token:
        raise ProjectEpochMcpError("bridge response identity mismatch")
    if status not in {"OK", "ERR"}:
        raise ProjectEpochMcpError("bridge response status is invalid")
    payload = parts[5]
    if length != len(payload):
        raise ProjectEpochMcpError("bridge response length mismatch")
    document = _decode_json_object(payload, "bridge response payload")
    if document.get("schema") != BRIDGE_PROTOCOL:
        raise ProjectEpochMcpError("bridge response schema mismatch")
    return status, document


@dataclass
class EmulatorSession:
    session_id: str
    token: str
    root: Path
    bridge_dir: Path
    process: subprocess.Popen[bytes]
    stdout_handle: BinaryIO
    stderr_handle: BinaryIO
    source_receipt: dict[str, dict[str, Any]]
    shared_saves_before: dict[str, tuple[int, str]]
    staged_hashes: dict[str, str]
    staged_paths: dict[str, Path]
    started_monotonic: float
    next_sequence: int = 1
    lock: threading.Lock = field(default_factory=threading.Lock)


class ProjectEpochMesenController:
    """Owns at most one pinned disposable Mesen process."""

    def __init__(self) -> None:
        self.session: EmulatorSession | None = None
        self.bridge_receipt = _bridge_security_audit()

    def _require_session(self) -> EmulatorSession:
        session = self.session
        if session is None:
            raise ProjectEpochMcpError("no disposable emulator session is active")
        if session.process.poll() is not None:
            raise ProjectEpochMcpError(
                f"disposable emulator exited unexpectedly with code {session.process.returncode}"
            )
        return session

    def _validate_new_session_root(self, root: Path) -> Path:
        base = SESSION_BASE.resolve(strict=True)
        resolved = root.resolve(strict=True)
        if (
            resolved.parent != base
            or not resolved.name.startswith("session_")
            or not _inside(resolved, PRIVATE_ROOT)
        ):
            raise ProjectEpochMcpError("disposable session root failed containment check")
        return resolved

    def _remove_successful_session_root(self, root: Path) -> None:
        resolved = self._validate_new_session_root(root)
        base = SESSION_BASE.resolve(strict=True)
        if resolved == base or len(resolved.name) < len("session_") + 16:
            raise ProjectEpochMcpError("refusing broad disposable-session removal")
        shutil.rmtree(resolved)
        if os.path.lexists(resolved):
            raise ProjectEpochMcpError("disposable session directory was not removed")

    def start(self, profile: str = PROFILE_ID) -> dict[str, Any]:
        if profile != PROFILE_ID:
            raise ProjectEpochMcpError("only the pinned v1 checkpoint profile is supported")
        if self.session is not None:
            if self.session.process.poll() is None:
                raise ProjectEpochMcpError("a disposable emulator session is already active")
            raise ProjectEpochMcpError(
                "a prior emulator session ended without validated cleanup; stop it first"
            )

        source_receipt = _verify_source_specs()
        bridge_receipt = _bridge_security_audit()
        shared_saves = SOURCE_SPECS["sram"][0].parent.resolve(strict=True)
        shared_saves_before = _snapshot_regular_files(shared_saves)

        SESSION_BASE.mkdir(parents=True, exist_ok=True)
        base = SESSION_BASE.resolve(strict=True)
        if not _inside(base, PRIVATE_ROOT) or base != SESSION_BASE:
            raise ProjectEpochMcpError("session base is redirected or outside private/")

        session_id = secrets.token_hex(12)
        root = base / f"session_{session_id}"
        root.mkdir(exist_ok=False)
        root = self._validate_new_session_root(root)
        app = root / "app"
        saves = app / "Saves"
        bridge_dir = root / "bridge"
        saves.mkdir(parents=True)
        bridge_dir.mkdir()

        staged_paths: dict[str, Path] = {}
        staged_hashes: dict[str, str] = {}
        for label, filename in RUNTIME_NAMES.items():
            destination = app / filename
            shutil.copyfile(SOURCE_SPECS[label][0], destination)
            staged_paths[label] = destination.resolve(strict=True)
            staged_hashes[label] = SOURCE_SPECS[label][2]

        unique_stem = f"pe_mcp_{session_id}"
        staged_rom = root / f"{unique_stem}.sfc"
        staged_state = root / f"{unique_stem}.mss"
        staged_sram = saves / f"{unique_stem}.srm"
        staged_bridge = root / "project_epoch_mesen_mcp_bridge.lua"
        for label, source, destination in (
            ("rom", SOURCE_SPECS["rom"][0], staged_rom),
            ("state", SOURCE_SPECS["state"][0], staged_state),
            ("sram", SOURCE_SPECS["sram"][0], staged_sram),
            ("bridge", BRIDGE_SOURCE, staged_bridge),
        ):
            shutil.copyfile(source, destination)
            staged_paths[label] = destination.resolve(strict=True)
            staged_hashes[label] = (
                BRIDGE_SHA256 if label == "bridge" else SOURCE_SPECS[label][2]
            )

        for label, path in staged_paths.items():
            if not _inside(path, root):
                raise ProjectEpochMcpError(f"staged {label} escaped its session root")
            actual = _sha256_file(path)
            if actual != staged_hashes[label]:
                raise ProjectEpochMcpError(f"staged {label} failed prelaunch hash check")

        token = secrets.token_hex(32)
        environment = os.environ.copy()
        environment.update(
            {
                "PE_MCP_BRIDGE_DIR": str(bridge_dir),
                "PE_MCP_SESSION_TOKEN": token,
                "PE_MCP_STATE_PATH": str(staged_state),
            }
        )
        command = [
            str(staged_paths["mesen"]),
            "--testRunner",
            "--timeout=300",
            "--doNotSaveSettings",
            "--debug.scriptWindow.allowIoOsAccess=true",
            "--snes.port1.type=SnesController",
            str(staged_bridge),
            str(staged_rom),
        ]
        stdout_handle = (root / "mesen.stdout.txt").open("xb")
        stderr_handle = (root / "mesen.stderr.txt").open("xb")
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            process = subprocess.Popen(
                command,
                cwd=app,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                creationflags=creation_flags,
            )
        except Exception:
            stdout_handle.close()
            stderr_handle.close()
            raise

        session = EmulatorSession(
            session_id=session_id,
            token=token,
            root=root,
            bridge_dir=bridge_dir,
            process=process,
            stdout_handle=stdout_handle,
            stderr_handle=stderr_handle,
            source_receipt=source_receipt,
            shared_saves_before=shared_saves_before,
            staged_hashes=staged_hashes,
            staged_paths=staged_paths,
            started_monotonic=time.monotonic(),
        )
        self.session = session

        ready_path = bridge_dir / "ready.json"
        fatal_path = bridge_dir / "fatal.txt"
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            return_code = process.poll()
            if fatal_path.exists():
                detail = fatal_path.read_text(encoding="utf-8", errors="replace")[:2000]
                raise ProjectEpochMcpError(f"Mesen bridge startup failed: {detail.strip()}")
            if return_code is not None:
                raise ProjectEpochMcpError(
                    f"Mesen exited before bridge readiness with code {return_code}"
                )
            if ready_path.exists():
                ready_data = ready_path.read_bytes()
                ready = _decode_json_object(ready_data, "bridge readiness receipt")
                if (
                    ready.get("schema") != BRIDGE_PROTOCOL
                    or ready.get("token") != token
                    or ready.get("profile") != PROFILE_ID
                    or ready.get("state_size") != SOURCE_SPECS["state"][1]
                    or ready.get("location") != 0x01D1
                    or ready.get("direct_page") != 0x0100
                    or ready.get("explore_mode") != 1
                    or ready.get("dialog_state") != 0
                    or ready.get("active_party_hex") != "060403"
                    or ready.get("candidate_and_guards_zero") is not True
                ):
                    raise ProjectEpochMcpError("bridge readiness invariants drifted")
                return {
                    "schema": "project-epoch-mesen-mcp-tool-result-v1",
                    "status": "active-disposable-exploratory-session",
                    "evidence_level": "exploratory-runtime",
                    "acceptance_evidence": False,
                    "session_id": session_id,
                    "profile": PROFILE_ID,
                    "ready": {
                        key: value for key, value in ready.items() if key != "token"
                    },
                    "inputs": source_receipt,
                    "bridge": bridge_receipt,
                    "writes_available": False,
                    "arbitrary_lua_available": False,
                    "client_paths_accepted": False,
                }
            time.sleep(0.02)
        raise ProjectEpochMcpError("timed out waiting for Mesen bridge readiness")

    def _request(
        self,
        operation: str,
        fields: Mapping[str, str | int] | None = None,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        session = self._require_session()
        if not re.fullmatch(r"[A-Z_]+", operation):
            raise ProjectEpochMcpError("internal bridge operation name is invalid")
        with session.lock:
            sequence = session.next_sequence
            lines = [
                "PEMCP1",
                f"SEQ:{sequence}",
                f"TOKEN:{session.token}",
                f"OP:{operation}",
            ]
            for key, raw_value in (fields or {}).items():
                if not re.fullmatch(r"[A-Z_]+", key):
                    raise ProjectEpochMcpError("internal bridge field name is invalid")
                value = str(raw_value)
                if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
                    raise ProjectEpochMcpError("internal bridge field value is invalid")
                lines.append(f"{key}:{value}")
            request = ("\n".join(lines) + "\n").encode("ascii")
            if len(request) > 4096:
                raise ProjectEpochMcpError("internal bridge request exceeds limit")

            request_path = session.bridge_dir / "request.txt"
            response_path = session.bridge_dir / "response.txt"
            for stale in (request_path, response_path):
                if os.path.lexists(stale):
                    metadata = stale.stat(follow_symlinks=False)
                    if not stat.S_ISREG(metadata.st_mode):
                        raise ProjectEpochMcpError("bridge transport contains non-file entry")
                    stale.unlink()
            _atomic_write(request_path, request)

            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                return_code = session.process.poll()
                if return_code is not None:
                    raise ProjectEpochMcpError(
                        f"Mesen exited during bridge request with code {return_code}"
                    )
                if response_path.exists():
                    raw = response_path.read_bytes()
                    response_path.unlink()
                    status, document = _parse_bridge_response(
                        raw,
                        expected_sequence=sequence,
                        expected_token=session.token,
                    )
                    session.next_sequence += 1
                    if status == "ERR":
                        raise ProjectEpochMcpError(
                            f"Mesen bridge rejected request: {document.get('error', 'unknown error')}"
                        )
                    return document
                time.sleep(0.01)
            if request_path.exists():
                request_path.unlink()
            raise ProjectEpochMcpError(
                f"timed out waiting for Mesen operation {operation}"
            )

    def status(self) -> dict[str, Any]:
        session = self.session
        if session is None:
            return {
                "schema": "project-epoch-mesen-mcp-tool-result-v1",
                "active": False,
                "evidence_level": "exploratory-runtime",
                "acceptance_evidence": False,
                "bridge": self.bridge_receipt,
            }
        return_code = session.process.poll()
        if return_code is not None:
            return {
                "schema": "project-epoch-mesen-mcp-tool-result-v1",
                "active": False,
                "unclean_session_pending_validation": True,
                "session_id": session.session_id,
                "process_exit_code": return_code,
                "evidence_level": "exploratory-runtime",
                "acceptance_evidence": False,
            }
        bridge = self._request("PING")
        return {
            "schema": "project-epoch-mesen-mcp-tool-result-v1",
            "active": True,
            "session_id": session.session_id,
            "profile": PROFILE_ID,
            "uptime_seconds": round(time.monotonic() - session.started_monotonic, 3),
            "bridge": bridge,
            "evidence_level": "exploratory-runtime",
            "acceptance_evidence": False,
        }

    def read_wram(self, offset: int, length: int) -> dict[str, Any]:
        if isinstance(offset, bool) or not isinstance(offset, int):
            raise ProjectEpochMcpError("offset must be an integer")
        if isinstance(length, bool) or not isinstance(length, int):
            raise ProjectEpochMcpError("length must be an integer")
        if offset < 0 or offset > 0x1FFFF:
            raise ProjectEpochMcpError("offset must be within direct SNES WRAM")
        if length < 1 or length > MAX_READ_BYTES:
            raise ProjectEpochMcpError(f"length must be 1..{MAX_READ_BYTES}")
        if offset + length - 1 > 0x1FFFF:
            raise ProjectEpochMcpError("WRAM read crosses the direct WRAM boundary")
        result = self._request(
            "READ_WRAM",
            {"START": offset, "LENGTH": length},
        )
        expected_hex_length = length * 2
        if (
            result.get("start_offset") != offset
            or result.get("length") != length
            or not isinstance(result.get("hex"), str)
            or len(result["hex"]) != expected_hex_length
            or re.fullmatch(r"[0-9a-f]+", result["hex"]) is None
        ):
            raise ProjectEpochMcpError("bounded WRAM result failed host validation")
        result.update(
            {
                "evidence_level": "exploratory-runtime",
                "acceptance_evidence": False,
                "write_performed": False,
            }
        )
        return result

    def read_cpu_state(self) -> dict[str, Any]:
        result = self._request("CPU_STATE")
        cpu = result.get("cpu")
        expected = {"pc", "k", "pc24", "a", "x", "y", "d", "ps", "sp", "db"}
        if not isinstance(cpu, dict) or set(cpu) != expected:
            raise ProjectEpochMcpError("CPU-state result schema drifted")
        result.update(
            {
                "evidence_level": "exploratory-runtime",
                "acceptance_evidence": False,
                "write_performed": False,
            }
        )
        return result

    def capture_wram_accesses(
        self,
        start_offset: int,
        end_offset: int,
        access: str,
        frames: int,
        record_limit: int,
    ) -> dict[str, Any]:
        for name, value in (
            ("start_offset", start_offset),
            ("end_offset", end_offset),
            ("frames", frames),
            ("record_limit", record_limit),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ProjectEpochMcpError(f"{name} must be an integer")
        if start_offset < 0 or start_offset > 0x1FFFF:
            raise ProjectEpochMcpError("start_offset is outside direct SNES WRAM")
        if end_offset < start_offset or end_offset > 0x1FFFF:
            raise ProjectEpochMcpError("end_offset is outside the bounded range")
        if end_offset - start_offset + 1 > MAX_CAPTURE_SPAN:
            raise ProjectEpochMcpError(
                f"capture span must be at most {MAX_CAPTURE_SPAN} bytes"
            )
        if access not in {"read", "write", "both"}:
            raise ProjectEpochMcpError("access must be read, write, or both")
        if frames < 1 or frames > MAX_CAPTURE_FRAMES:
            raise ProjectEpochMcpError(f"frames must be 1..{MAX_CAPTURE_FRAMES}")
        if record_limit < 1 or record_limit > MAX_CAPTURE_RECORDS:
            raise ProjectEpochMcpError(
                f"record_limit must be 1..{MAX_CAPTURE_RECORDS}"
            )
        result = self._request(
            "CAPTURE_WRAM",
            {
                "START": start_offset,
                "END": end_offset,
                "ACCESS": access,
                "FRAMES": frames,
                "LIMIT": record_limit,
            },
            timeout=30.0,
        )
        records = result.get("records")
        if (
            result.get("start_offset") != start_offset
            or result.get("end_offset") != end_offset
            or result.get("access") != access
            or result.get("requested_frames") != frames
            or result.get("completed_frames") != frames
            or result.get("record_limit") != record_limit
            or not isinstance(records, list)
            or result.get("record_count") != len(records)
            or len(records) > record_limit
            or result.get("observer_error") is not None
            or not isinstance(result.get("start_field_counter_mod16"), int)
            or not 0 <= result["start_field_counter_mod16"] <= 15
        ):
            raise ProjectEpochMcpError("capture result contract drifted")
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                raise ProjectEpochMcpError("capture record is not an object")
            if record.get("sequence") != index:
                raise ProjectEpochMcpError("capture record sequence drifted")
            if record.get("access") not in {"read", "write"}:
                raise ProjectEpochMcpError("capture record access is invalid")
            offset = record.get("offset")
            address = record.get("address")
            if (
                isinstance(offset, bool)
                or not isinstance(offset, int)
                or offset < start_offset
                or offset > end_offset
                or address != 0x7E0000 + offset
            ):
                raise ProjectEpochMcpError("capture record address escaped range")
        result.update(
            {
                "evidence_level": "exploratory-runtime",
                "acceptance_evidence": False,
                "explicit_memory_write_performed": False,
                "checkpoint_advanced": True,
            }
        )
        return result

    def _post_session_integrity(self, session: EmulatorSession) -> dict[str, Any]:
        source_after = _verify_source_specs()
        if source_after != session.source_receipt:
            raise ProjectEpochMcpError("immutable source inputs changed during session")
        shared_saves = SOURCE_SPECS["sram"][0].parent.resolve(strict=True)
        if _snapshot_regular_files(shared_saves) != session.shared_saves_before:
            raise ProjectEpochMcpError("shared Mesen Saves directory changed")
        staged_changes: list[str] = []
        for label, path in session.staged_paths.items():
            try:
                actual = _sha256_file(path)
            except OSError:
                staged_changes.append(f"{label}:missing")
                continue
            if actual != session.staged_hashes[label]:
                staged_changes.append(f"{label}:changed")
        if staged_changes:
            raise ProjectEpochMcpError(
                "disposable emulator inputs changed: " + ", ".join(staged_changes)
            )
        return {
            "immutable_sources_preserved": True,
            "shared_mesen_saves_preserved": True,
            "disposable_rom_preserved": True,
            "disposable_sram_preserved": True,
            "disposable_checkpoint_preserved": True,
            "bridge_source_preserved": True,
        }

    def stop(self) -> dict[str, Any]:
        session = self._require_session()
        stop_receipt = self._request("STOP")
        try:
            return_code = session.process.wait(timeout=10.0)
        except subprocess.TimeoutExpired as exc:
            raise ProjectEpochMcpError("Mesen did not stop after bounded STOP request") from exc
        finally:
            session.stdout_handle.close()
            session.stderr_handle.close()
        if return_code != EXPECTED_MESEN_EXIT_CODE:
            raise ProjectEpochMcpError(
                f"Mesen returned {return_code}, expected {EXPECTED_MESEN_EXIT_CODE}"
            )
        integrity = self._post_session_integrity(session)
        root = session.root
        session_id = session.session_id
        self._remove_successful_session_root(root)
        self.session = None
        return {
            "schema": "project-epoch-mesen-mcp-tool-result-v1",
            "status": "stopped-and-validated",
            "session_id": session_id,
            "process_exit_code": return_code,
            "stop_receipt": stop_receipt,
            **integrity,
            "disposable_staging_deleted": True,
            "evidence_level": "exploratory-runtime",
            "acceptance_evidence": False,
        }

    def best_effort_cleanup(self) -> None:
        session = self.session
        if session is None:
            return
        try:
            if session.process.poll() is None:
                try:
                    self._request("STOP", timeout=2.0)
                    session.process.wait(timeout=3.0)
                except Exception:
                    session.process.terminate()
                    try:
                        session.process.wait(timeout=3.0)
                    except Exception:
                        session.process.kill()
                        session.process.wait(timeout=3.0)
        finally:
            try:
                session.stdout_handle.close()
            except Exception:
                pass
            try:
                session.stderr_handle.close()
            except Exception:
                pass
            try:
                self._post_session_integrity(session)
                self._remove_successful_session_root(session.root)
            except Exception:
                # Preserve a failed private staging directory for diagnosis.
                pass
            self.session = None


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "start_disposable_session",
        "title": "Start pinned disposable Mesen session",
        "description": (
            "Start the single source-controlled Project Epoch v1 profile in an "
            "isolated, hash-pinned Mesen 2.1.1 process. No client path is accepted."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile": {"type": "string", "enum": [PROFILE_ID]},
            },
            "additionalProperties": False,
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    },
    {
        "name": "session_status",
        "title": "Read disposable Mesen session status",
        "description": "Return bounded status and bridge readiness without exposing paths.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "read_wram",
        "title": "Read bounded direct SNES WRAM",
        "description": (
            "Read 1-256 bytes from direct SNES WRAM offset 0..131071. "
            "This tool has no write path."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "offset": {"type": "integer", "minimum": 0, "maximum": 131071},
                "length": {"type": "integer", "minimum": 1, "maximum": 256},
            },
            "required": ["offset", "length"],
            "additionalProperties": False,
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "read_cpu_state",
        "title": "Read 65C816 CPU state",
        "description": "Read the current bounded 65C816 register snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    },
    {
        "name": "capture_wram_accesses",
        "title": "Capture bounded WRAM accesses",
        "description": (
            "Observe reads, writes, or both for a 1-256 byte direct-WRAM span "
            "during exactly 1-1800 zero-input frames. Observation advances only "
            "the disposable checkpoint and never calls a memory-write API."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_offset": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 131071,
                },
                "end_offset": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 131071,
                },
                "access": {"type": "string", "enum": ["read", "write", "both"]},
                "frames": {"type": "integer", "minimum": 1, "maximum": 1800},
                "record_limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 1024,
                },
            },
            "required": [
                "start_offset",
                "end_offset",
                "access",
                "frames",
                "record_limit",
            ],
            "additionalProperties": False,
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    },
    {
        "name": "stop_disposable_session",
        "title": "Stop and validate disposable Mesen session",
        "description": (
            "Stop the active process, rehash immutable and disposable inputs, "
            "verify the shared Saves tree, and delete only the validated session root."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    },
]


def _validate_argument_object(arguments: Any) -> dict[str, Any]:
    if arguments is None:
        return {}
    if not isinstance(arguments, dict):
        raise ProjectEpochMcpError("tool arguments must be one object")
    return arguments


def _reject_extra(arguments: Mapping[str, Any], allowed: set[str]) -> None:
    extras = set(arguments) - allowed
    if extras:
        raise ProjectEpochMcpError(
            "unsupported tool argument(s): " + ", ".join(sorted(extras))
        )


def _required(arguments: Mapping[str, Any], key: str) -> Any:
    if key not in arguments:
        raise ProjectEpochMcpError(f"missing required tool argument: {key}")
    return arguments[key]


def _call_tool(
    controller: ProjectEpochMesenController,
    name: str,
    raw_arguments: Any,
) -> dict[str, Any]:
    arguments = _validate_argument_object(raw_arguments)
    if name == "start_disposable_session":
        _reject_extra(arguments, {"profile"})
        profile = arguments.get("profile", PROFILE_ID)
        if not isinstance(profile, str):
            raise ProjectEpochMcpError("profile must be a string")
        return controller.start(profile)
    if name == "session_status":
        _reject_extra(arguments, set())
        return controller.status()
    if name == "read_wram":
        _reject_extra(arguments, {"offset", "length"})
        return controller.read_wram(
            _required(arguments, "offset"),
            _required(arguments, "length"),
        )
    if name == "read_cpu_state":
        _reject_extra(arguments, set())
        return controller.read_cpu_state()
    if name == "capture_wram_accesses":
        allowed = {"start_offset", "end_offset", "access", "frames", "record_limit"}
        _reject_extra(arguments, allowed)
        return controller.capture_wram_accesses(
            _required(arguments, "start_offset"),
            _required(arguments, "end_offset"),
            _required(arguments, "access"),
            _required(arguments, "frames"),
            _required(arguments, "record_limit"),
        )
    if name == "stop_disposable_session":
        _reject_extra(arguments, set())
        return controller.stop()
    raise ProjectEpochMcpError(f"unknown MCP tool: {name}")


def _tool_result(document: Mapping[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    text = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True)
    result: dict[str, Any] = {
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }
    if not is_error:
        result["structuredContent"] = dict(document)
    return result


def _jsonrpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def _jsonrpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _handle_rpc(
    controller: ProjectEpochMesenController,
    message: dict[str, Any],
) -> dict[str, Any] | None:
    if message.get("jsonrpc") != "2.0":
        return _jsonrpc_error(message.get("id"), -32600, "invalid JSON-RPC version")
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params", {})
    if method == "notifications/initialized":
        return None
    if method == "notifications/cancelled":
        return None
    if method == "initialize":
        if not isinstance(params, dict):
            return _jsonrpc_error(request_id, -32602, "initialize params must be an object")
        return _jsonrpc_result(
            request_id,
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": INSTRUCTIONS,
            },
        )
    if method == "ping":
        return _jsonrpc_result(request_id, {})
    if method == "tools/list":
        return _jsonrpc_result(request_id, {"tools": TOOL_DEFINITIONS})
    if method == "tools/call":
        if not isinstance(params, dict) or not isinstance(params.get("name"), str):
            return _jsonrpc_error(request_id, -32602, "tools/call params are invalid")
        try:
            document = _call_tool(controller, params["name"], params.get("arguments"))
            return _jsonrpc_result(request_id, _tool_result(document))
        except ProjectEpochMcpError as exc:
            return _jsonrpc_result(
                request_id,
                _tool_result(
                    {
                        "schema": "project-epoch-mesen-mcp-tool-error-v1",
                        "error": str(exc),
                        "acceptance_evidence": False,
                    },
                    is_error=True,
                ),
            )
    return _jsonrpc_error(request_id, -32601, f"method not found: {method}")


def serve_stdio() -> int:
    controller = ProjectEpochMesenController()
    atexit.register(controller.best_effort_cleanup)
    input_stream = sys.stdin.buffer
    output_stream = sys.stdout.buffer
    while True:
        line = input_stream.readline(MAX_JSON_LINE_BYTES + 1)
        if not line:
            break
        if len(line) > MAX_JSON_LINE_BYTES:
            response = _jsonrpc_error(None, -32700, "JSON-RPC line exceeds maximum size")
        else:
            try:
                message = _decode_json_object(line, "JSON-RPC request")
                response = _handle_rpc(controller, message)
            except ProjectEpochMcpError as exc:
                response = _jsonrpc_error(None, -32700, str(exc))
            except Exception as exc:  # last-resort containment; no traceback on stdout
                response = _jsonrpc_error(None, -32603, f"internal server error: {exc}")
        if response is not None:
            encoded = json.dumps(
                response,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8") + b"\n"
            output_stream.write(encoded)
            output_stream.flush()
    controller.best_effort_cleanup()
    return 0


def self_test() -> dict[str, Any]:
    bridge = _bridge_security_audit()
    tool_names = [tool["name"] for tool in TOOL_DEFINITIONS]
    if len(tool_names) != len(set(tool_names)):
        raise ProjectEpochMcpError("duplicate MCP tool name")
    if "execute_lua" in tool_names:
        raise ProjectEpochMcpError("arbitrary Lua tool unexpectedly exposed")
    if any("path" in json.dumps(tool["inputSchema"]).lower() for tool in TOOL_DEFINITIONS):
        raise ProjectEpochMcpError("an MCP tool unexpectedly accepts a path")
    initialize = _handle_rpc(
        ProjectEpochMesenController(),
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": MCP_PROTOCOL_VERSION},
        },
    )
    if not isinstance(initialize, dict) or initialize.get("result", {}).get(
        "protocolVersion"
    ) != MCP_PROTOCOL_VERSION:
        raise ProjectEpochMcpError("MCP initialize self-test failed")
    return {
        "schema": "project-epoch-mesen-mcp-self-test-v1",
        "status": "ok",
        "server": {"name": SERVER_NAME, "version": SERVER_VERSION},
        "bridge": bridge,
        "tools": tool_names,
        "arbitrary_lua": False,
        "write_tools": [],
        "client_supplied_paths": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="validate the closed tool/bridge contract without launching Mesen",
    )
    parser.add_argument(
        "--describe-tools",
        action="store_true",
        help="print the source-controlled MCP tool definitions and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.self_test:
            print(json.dumps(self_test(), indent=2, sort_keys=True))
            return 0
        if args.describe_tools:
            print(json.dumps({"tools": TOOL_DEFINITIONS}, indent=2, sort_keys=True))
            return 0
        return serve_stdio()
    except ProjectEpochMcpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
