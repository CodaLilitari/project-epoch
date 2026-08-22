from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = (
    ROOT / "tools" / "build_mesen_wram_ownership_menu_collector_v2.py"
)


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
    "build_mesen_wram_ownership_menu_collector_v2_test",
    TOOL_PATH,
)


class BuildMesenWramOwnershipMenuCollectorV2Tests(unittest.TestCase):
    def test_build_is_deterministic_and_preserves_the_exact_base(self) -> None:
        base = TOOL.BASE_COLLECTOR.read_bytes()
        base_before = hashlib.sha256(base).hexdigest()

        first = TOOL.build_collector()
        second = TOOL.build_collector(base)

        self.assertEqual(first, second)
        self.assertEqual(
            hashlib.sha256(first).hexdigest(),
            TOOL.sha256_bytes(second),
        )
        self.assertEqual(
            hashlib.sha256(TOOL.BASE_COLLECTOR.read_bytes()).hexdigest(),
            base_before,
        )
        self.assertEqual(base_before, TOOL.BASE_COLLECTOR_SHA256)

        source = first.decode("utf-8")
        self.assertIn(
            f'"schema":"{TOOL.TRACE_SCHEMA}"',
            source,
        )
        self.assertIn(
            f'"collector_version":{TOOL.COLLECTOR_VERSION}',
            source,
        )
        self.assertNotIn(
            '"schema":"project-epoch-mesen-wram-ownership-trace-v1"',
            source,
        )
        self.assertNotIn('"collector_version":1', source)

    def test_rejects_any_base_preimage_drift(self) -> None:
        changed = bytearray(TOOL.BASE_COLLECTOR.read_bytes())
        changed[-1] ^= 1

        with self.assertRaisesRegex(
            TOOL.CollectorBuildError,
            "accepted base collector SHA-256 drifted",
        ):
            TOOL.build_collector(bytes(changed))

    def test_replacement_helpers_fail_closed_on_marker_drift(self) -> None:
        with self.assertRaisesRegex(
            TOOL.CollectorBuildError,
            "found 0",
        ):
            TOOL._replace_once("alpha", "missing", "new", "fixture")
        with self.assertRaisesRegex(
            TOOL.CollectorBuildError,
            "found 2",
        ):
            TOOL._replace_once(
                "marker marker",
                "marker",
                "new",
                "fixture",
            )

    def test_scenarios_have_the_exact_bounded_menu_timelines(self) -> None:
        expected = (
            (
                "equipment-owner-switch",
                600,
                (
                    ("x", "X", 60, 61),
                    ("a", "A", 180, 181),
                    ("down", "DOWN", 300, 303),
                    ("b", "B", 420, 421),
                ),
            ),
            (
                "tech-owner-switch",
                600,
                (
                    ("x", "X", 60, 61),
                    ("right", "RIGHT", 120, 123),
                    ("right", "RIGHT", 160, 163),
                    ("a", "A", 220, 221),
                    ("down", "DOWN", 300, 303),
                    ("b", "B", 420, 421),
                ),
            ),
            (
                "item-list-cancel",
                600,
                (
                    ("x", "X", 60, 61),
                    ("right", "RIGHT", 120, 123),
                    ("a", "A", 180, 181),
                    ("b", "B", 420, 421),
                ),
            ),
            (
                "party-page-cancel",
                600,
                (
                    ("x", "X", 60, 61),
                    ("right", "RIGHT", 120, 123),
                    ("right", "RIGHT", 160, 163),
                    ("right", "RIGHT", 200, 203),
                    ("right", "RIGHT", 240, 243),
                    ("a", "A", 300, 301),
                    ("right", "RIGHT", 380, 383),
                    ("b", "B", 500, 501),
                ),
            ),
        )
        actual = tuple(
            (
                scenario.name,
                scenario.terminal_frame,
                tuple(
                    (
                        pulse.button,
                        pulse.json_button,
                        pulse.start_frame,
                        pulse.end_frame,
                    )
                    for pulse in scenario.pulses
                ),
            )
            for scenario in TOOL.SCENARIOS
        )
        self.assertEqual(actual, expected)
        self.assertEqual(
            TOOL.SCENARIO_NAMES,
            tuple(row[0] for row in expected),
        )

        generated = TOOL.build_collector().decode("utf-8")
        rendered_contract = TOOL._scenario_lua()
        self.assertEqual(generated.count(rendered_contract), 1)
        self.assertEqual(generated.count("local INPUT_TIMELINES = {"), 1)
        self.assertIn(
            "for _, scheduled in ipairs(INPUT_TIMELINES[scenario_name]) do",
            generated,
        )


if __name__ == "__main__":
    unittest.main()
