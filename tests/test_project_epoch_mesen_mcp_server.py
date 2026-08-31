from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "tools" / "project_epoch_mesen_mcp_server.py"
BRIDGE_PATH = ROOT / "tools" / "project_epoch_mesen_mcp_bridge.lua"
CONFIG_PATH = ROOT / ".codex" / "config.toml"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SERVER = load_module("project_epoch_mesen_mcp_server", SERVER_PATH)


class ProjectEpochMesenMcpTests(unittest.TestCase):
    def test_bridge_is_exact_and_has_no_dynamic_execution_or_memory_write(self) -> None:
        receipt = SERVER._bridge_security_audit()
        self.assertEqual(receipt["sha256"], SERVER.BRIDGE_SHA256)
        self.assertFalse(receipt["arbitrary_lua"])
        self.assertFalse(receipt["emulator_memory_write_api"])
        self.assertFalse(receipt["client_supplied_paths"])
        source = BRIDGE_PATH.read_text(encoding="utf-8")
        forbidden = (
            r"(?<![A-Za-z0-9_])load\s*\(",
            r"(?<![A-Za-z0-9_])dofile\s*\(",
            r"(?<![A-Za-z0-9_])require\s*\(",
            r"\bpackage\s*\.",
            r"\bdebug\s*\.",
            r"\bos\s*\.\s*execute\b",
            r"\bio\s*\.\s*popen\b",
            r"\bemu\s*\.\s*write(?:8|16|32)?\s*\(",
        )
        for pattern in forbidden:
            self.assertIsNone(re.search(pattern, source), pattern)

    def test_tool_allowlist_has_no_lua_path_or_write_operation(self) -> None:
        names = [tool["name"] for tool in SERVER.TOOL_DEFINITIONS]
        self.assertEqual(
            names,
            [
                "start_disposable_session",
                "session_status",
                "read_wram",
                "read_cpu_state",
                "capture_wram_accesses",
                "stop_disposable_session",
            ],
        )
        self.assertNotIn("execute_lua", names)
        for tool in SERVER.TOOL_DEFINITIONS:
            schema_text = json.dumps(tool["inputSchema"], sort_keys=True).lower()
            self.assertNotIn("path", schema_text)
            self.assertNotIn("code", schema_text)
            self.assertIs(tool["inputSchema"]["additionalProperties"], False)
            self.assertIs(tool["annotations"]["openWorldHint"], False)

    def test_range_validation_fails_before_requiring_a_session(self) -> None:
        controller = SERVER.ProjectEpochMesenController()
        with self.assertRaisesRegex(SERVER.ProjectEpochMcpError, "offset"):
            controller.read_wram(-1, 1)
        with self.assertRaisesRegex(SERVER.ProjectEpochMcpError, "length"):
            controller.read_wram(0, 257)
        with self.assertRaisesRegex(SERVER.ProjectEpochMcpError, "span"):
            controller.capture_wram_accesses(0, 256, "read", 1, 1)
        with self.assertRaisesRegex(SERVER.ProjectEpochMcpError, "access"):
            controller.capture_wram_accesses(0, 1, "execute", 1, 1)
        with self.assertRaisesRegex(SERVER.ProjectEpochMcpError, "frames"):
            controller.capture_wram_accesses(0, 1, "read", 1801, 1)

    def test_bridge_response_requires_exact_identity_and_length(self) -> None:
        token = "a" * 64
        payload = json.dumps({"schema": SERVER.BRIDGE_PROTOCOL}).encode("ascii")
        raw = (
            b"PEMCP1\nSEQ:7\nTOKEN:"
            + token.encode("ascii")
            + b"\nSTATUS:OK\nLEN:"
            + str(len(payload)).encode("ascii")
            + b"\n"
            + payload
        )
        status, document = SERVER._parse_bridge_response(
            raw,
            expected_sequence=7,
            expected_token=token,
        )
        self.assertEqual(status, "OK")
        self.assertEqual(document["schema"], SERVER.BRIDGE_PROTOCOL)
        with self.assertRaisesRegex(SERVER.ProjectEpochMcpError, "identity"):
            SERVER._parse_bridge_response(
                raw,
                expected_sequence=8,
                expected_token=token,
            )
        with self.assertRaisesRegex(SERVER.ProjectEpochMcpError, "length"):
            SERVER._parse_bridge_response(
                raw.replace(b"LEN:", b"LEN:1", 1),
                expected_sequence=7,
                expected_token=token,
            )

    def test_stdio_initialize_and_tool_listing(self) -> None:
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}},
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]
        source = b"".join(
            json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"
            for message in messages
        )
        completed = subprocess.run(
            [sys.executable, str(SERVER_PATH)],
            cwd=ROOT,
            input=source,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())
        responses = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual(len(responses), 2)
        self.assertEqual(
            responses[0]["result"]["protocolVersion"],
            SERVER.MCP_PROTOCOL_VERSION,
        )
        self.assertIn("Never treat", responses[0]["result"]["instructions"])
        self.assertEqual(
            [tool["name"] for tool in responses[1]["result"]["tools"]],
            [tool["name"] for tool in SERVER.TOOL_DEFINITIONS],
        )

    def test_self_test_does_not_launch_or_require_private_emulation(self) -> None:
        result = SERVER.self_test()
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["arbitrary_lua"])
        self.assertEqual(result["write_tools"], [])

    def test_project_config_is_project_scoped_and_allowlisted(self) -> None:
        import tomllib

        config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        row = config["mcp_servers"]["project_epoch_mesen"]
        self.assertEqual(row["command"], "py")
        self.assertEqual(
            row["args"],
            ["-3", "tools/project_epoch_mesen_mcp_server.py"],
        )
        self.assertEqual(row["cwd"], ".")
        self.assertEqual(row["enabled_tools"], [tool["name"] for tool in SERVER.TOOL_DEFINITIONS])
        self.assertTrue(row["enabled"])
        self.assertFalse(row["required"])


if __name__ == "__main__":
    unittest.main()
