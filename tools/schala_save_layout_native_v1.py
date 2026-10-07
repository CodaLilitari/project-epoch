"""Source contract for a private, instrumented ten-region native-loop experiment.

No gameplay record, sidecar, installed table, or production allocation is defined.
The collector injects a descriptor table only after the vanilla 40-byte MVN.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import schala_save_layout as layout

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "project-epoch-save-layout-native-v1"
ROM_SIZE = 0x400000
ROM_SHA256 = "06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9"
DEFAULT_ROM = ROOT / "private/input/rom_archive/Chrono Trigger (USA).sfc"
ASM_PATH = ROOT / "references/ct_disassembly/bank_FF.asm"
ASM_SHA256 = "18f30c2a4f547722f30934bde43eb6a638d9467aa064e21340aa2065ab71829e"
LAYOUT_SHA256 = "14128e7475761a68023f3e741197115dae0db31a001ebe6d9aa299df6ce04046"
# Minimal instruction witnesses; larger source regions are hash-only.
PATCHES = ((0x3FFA4F, bytes.fromhex("c92800"), bytes.fromhex("c93200")),
           (0x3FFAE6, bytes.fromhex("c92800"), bytes.fromhex("c93200")))
SOURCE_SPANS = (
    (0x3FF9FB, 128, "4c1ea6135ca6b7374f21b63bfc2a40d2332acbe1179389e8a04ecc38e76caf1f"),
    (0x3FFAA3, 74, "6d858b191571969684156b0149c49fc2a48b616d906c8f5061fed9d58296c8a3"),
    (0x3FFBD3, 49, "28fd568960c5d04708764e55a67c06db04edcbcd0078262fa423d498a0c05bbd"),
    (0x3FFA7B, 40, "30dfb2fbcf65bb8a21f09a2f1048d0615cf9b5127b02db9e1a94ee66f453d12a"),
    (0x02CF51, 4, "2baa16ebdecc826e751ed8e06cb754e40548d3cc8dab619ddbdeaf9125106a21"),
    (0x02E657, 4, "0154f31aa25eaf9f512a25b83f5311ed69cde5ee687ee22a2d85c05e6513126d"),
)
MODES = {
    "save": {"entry": 0xFFF9FB, "table": 0xFFFA26, "loop": 0xFFFA2D,
             "cmp": 0xFFFA4F, "copy_complete": 0xFFFA54, "terminal": 0xFFFA7A, "caller": 0xC2CF54},
    "load": {"entry": 0xFFFAA3, "table": 0xFFFABE, "loop": 0xFFFAC4,
             "cmp": 0xFFFAE6, "copy_complete": 0xFFFAEB, "terminal": 0xFFFAEC, "caller": 0xC2E65A},
}
TABLE_START = 0x9890
TABLE = layout.encode_region_table(layout.PROJECT_EPOCH_REGIONS)
VANILLA_TABLE = layout.encode_region_table(layout.VANILLA_REGIONS)
MARKER = bytes((19 + 73 * i) & 255 for i in range(80))
LOAD_POISON = bytes((167 + 91 * i) & 255 for i in range(80))
MAX_RECORDS = 250000
SUCCESS_EXIT = 62
BUNDLE_FILES = (
    "tools/schala_save_layout_native_v1.py",
    "tools/build_schala_save_layout_native_v1.py",
    "tools/run_mesen_save_layout_native_v1.py",
    "tools/mesen_save_layout_native_v1.lua",
    "tools/validate_mesen_save_layout_native_v1.py",
    "tools/schala_save_layout.py", "tools/validate_rom_write_intents.py",
    "tools/schala_rom_scaffold.py", "tools/inspect_ct_srm.py",
    "references/ct_disassembly/bank_FF.asm",
)


class ContractError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def source_contract(rom: bytes) -> dict:
    require(len(rom) == ROM_SIZE and sha256(rom) == ROM_SHA256, "canonical ROM identity mismatch")
    require(sha256(ASM_PATH.read_bytes()) == ASM_SHA256, "bank FF source drift")
    require(sha256((ROOT / "tools/schala_save_layout.py").read_bytes()) == LAYOUT_SHA256,
            "save-layout source drift")
    for start, size, digest in SOURCE_SPANS:
        require(sha256(rom[start:start + size]) == digest, "native source span drift")
    require(rom[0x3FFA7B:0x3FFAA3] == VANILLA_TABLE, "vanilla descriptor interpretation drift")
    for start, old, _new in PATCHES:
        require(rom[start:start + len(old)] == old, "CMP immediate preimage drift")
        require(_new[0] == 0xC9 and int.from_bytes(_new[1:], "little") == layout.TABLE_LOOP_STOP,
                "patched CMP does not match layout loop stop")
    for start in (0x3FFA20, 0x3FFAB8):
        require(rom[start:start + 9] == bytes.fromhex("a92700547eff20d3fb"),
                "MVN/post-copy JSR boundary drift")
    require(len(TABLE) == 50 == layout.TABLE_LOOP_STOP and sum(r.length for r in layout.PROJECT_EPOCH_REGIONS) == 0x834,
            "translated layout shape drift")
    return {"schema": SCHEMA, "source_sha256": ROM_SHA256,
            "source_spans": [{"file_start": a, "size": n, "sha256": h} for a, n, h in SOURCE_SPANS],
            "modes": MODES, "translated_table_sha256": sha256(TABLE),
            "marker_sha256": sha256(MARKER), "load_poison_sha256": sha256(LOAD_POISON),
            "evidence": "verified-static", "instrumented_only": True,
            "sidecar_installed": False, "playable_pc07": False,
            "terminal_before_rtl": True, "header_checksum_unchanged": True}


def private_path(path: Path, *, must_not_exist: bool = False) -> Path:
    resolved = path.resolve()
    private = (ROOT / "private").resolve()
    require(resolved.is_relative_to(private) and resolved != private, "output must stay below private/")
    require(not path.is_symlink(), "symlink output refused")
    if must_not_exist:
        require(not resolved.exists(), "existing output refused")
    return resolved


def bundle_identity() -> dict:
    rows = [{"path": p, "sha256": sha256((ROOT / p).read_bytes())} for p in BUNDLE_FILES]
    payload = "".join(row["path"] + "\0" + row["sha256"] + "\n" for row in rows).encode()
    return {"sha256": sha256(payload), "sources": rows}


def entry_contract(value: dict, mode: str) -> dict:
    """Require an explicitly pinned, future acquisition; never assume Spekkio."""
    require(type(value) is dict and set(value) == {
        "schema", "mode", "checkpoint_sha256", "checkpoint_size", "sram_sha256",
        "slot", "checkpoint_pc", "entry_pc", "caller_return", "evidence", "acquisition_reference"},
        "entry checkpoint contract fields mismatch")
    require(value["schema"] == SCHEMA + "-entry" and value["mode"] == mode, "entry contract mode/schema")
    require(mode in MODES and value["entry_pc"] == MODES[mode]["entry"] and
            value["caller_return"] == MODES[mode]["caller"], "entry/caller contract mismatch")
    require(value["checkpoint_pc"] == (0xC2CF51 if mode == "save" else 0xC2E657),
            "checkpoint must precede the actual JSL; entry-exec snapshots skip that callback on resume")
    require(type(value["slot"]) is int and value["slot"] in (0, 1, 2), "physical slot must be 0..2")
    require(type(value["checkpoint_size"]) is int and value["checkpoint_size"] > 0, "checkpoint size")
    for key in ("checkpoint_sha256", "sram_sha256"):
        v = value[key]
        require(type(v) is str and len(v) == 64 and all(c in "0123456789abcdef" for c in v), key)
    require(value["evidence"] == "verified-runtime" and type(value["acquisition_reference"]) is str
            and bool(value["acquisition_reference"].strip()), "acquisition evidence/reference required")
    return value
