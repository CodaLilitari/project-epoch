"""Revalidate two original private cartridge builds and emit metadata only."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path

import build_original_snes_package_cartridge_v1 as builder
import original_snes_diagnostic_write_contract_v1 as contract
import original_snes_package_fixtures_v1 as fixtures

ROOT=Path(__file__).resolve().parents[1]
IMAGE_SHA="1e0788500ad4181fea0ed767eed48c9d8da0f52ce86fec27cc8107d29033621b"
BOOT_SHA="785fbd007bcfe71e802a32ac69fce5dfc169c7c7045812b3a2b54fc5e5eed1e5"
HELPER_SHA="7242ff96f07e8d5ed9f0a994e474dbf3b49e7c2e576bd07d6536b6dfe3004f3b"


def read(path, maximum):
    if path.resolve(strict=True)!=path or not path.is_file():
        raise ValueError("unaliased regular evidence file required")
    with path.open("rb") as stream: data=stream.read(maximum+1)
    if len(data)>maximum: raise ValueError("evidence file exceeds bound")
    return data


def identity(path,maximum=0x100000):
    data=read(path,maximum)
    return {"path":path.relative_to(ROOT).as_posix(),"size":len(data),"sha256":hashlib.sha256(data).hexdigest()}


def collect():
    sources=builder.original_sources()
    expected_sources={
        "tools/build_original_snes_package_cartridge_v1.py":"45d85af48c8126be6c79caee681e22764740bdcc28cfc70b2220d758c313903a",
        "tools/original_snes_package_fixtures_v1.py":"b7911e1bea10bf9294e3ca4a896e203bd1d12aec03a33da137aa7caabcb10a60",
        "tools/original_snes_diagnostic_write_contract_v1.py":"f6dcf065fbc71b3ff9b8f7a43367873b90284484b501af06f1e6eb99f92e0318",
        "asm/schala_package_helper_v2_stack.asm":"7ee849f04444567ae6a67f5642edc0ec0b7ef09f41c7ea5f2b1773e6373fdb5f"}
    for source in sources:
        if source["path"] in expected_sources and source["sha256"]!=expected_sources[source["path"]]:
            raise ValueError("reviewed original source identity drift")
    builder.verify_asar()
    packages,registry,certificate=fixtures.build()
    certificate=json.loads(json.dumps(certificate))
    runs=[]
    images=[]
    for suffix in ("build1","build2"):
        directory=ROOT/f"private/test_runs/original_package_20260908_{suffix}"
        receipt=json.loads(read(directory/"audited-build.json",0x100000).decode("utf-8"))
        completion=json.loads(read(directory/"completion.json",0x10000).decode("utf-8"))
        if receipt["status"]!="audited-before-exclusive-image-write" or completion["status"]!="written-and-rehashed":
            raise ValueError("completed guarded build receipts required")
        if receipt["intent_manifest"]["sources"]!=sources or receipt["package_certificate"]!=certificate:
            raise ValueError("build source/certification drift")
        for source in sources:
            archive=directory/(source["path"].replace("/","__")+".source.txt")
            if read(archive,source["size"])!=read(ROOT/source["path"],source["size"]):
                raise ValueError("exact archived original source mismatch")
        boot=read(directory/"original-boot.bin",0x1000)
        helper=read(directory/"original-helper.bin",0x4000)
        if len(boot)!=290 or contract.sha(boot)!=BOOT_SHA or len(helper)!=577 or contract.sha(helper)!=HELPER_SHA:
            raise ValueError("original assembled component identity drift")
        image=read(directory/builder.ROM_NAME,contract.SIZE)
        sram=read(directory/"original_package_test.srm",0x2000)
        if len(image)!=contract.SIZE or contract.sha(image)!=IMAGE_SHA or len(sram)!=0x2000 or contract.sha(sram)!=builder.ZERO_SRAM_SHA256:
            raise ValueError("written original image or zero SRAM identity drift")
        # Existing-output refusal is intentionally retained in the write-time
        # contract. Reaudit the same bytes using a declared, never-created replay
        # output identity; this does not bypass or invoke any filesystem writer.
        replay_output=f"private/test_runs/original_package_readonly_replay_{suffix}/unwritten.sfc"
        rebuilt,intents,audit=builder.build_image(boot,helper,packages,registry,sources,replay_output)
        expected_intents=copy.deepcopy(receipt["intent_manifest"])
        expected_intents["output"]=replay_output
        if rebuilt!=image or intents!=expected_intents:
            raise ValueError("in-memory component reconstruction failed")
        historical_audit=copy.deepcopy(receipt["complete_diff_audit"])
        historical_audit["manifest_sha256"]=audit["manifest_sha256"]
        if audit!=historical_audit:
            raise ValueError("complete-diff audit changed beyond explicit replay output identity")
        if completion["rom"]!=builder.identity(image) or completion["sram"]!=builder.identity(sram):
            raise ValueError("completion does not match observed written artifacts")
        if completion["audited_build_sha256"]!=contract.sha(read(directory/"audited-build.json",0x100000)):
            raise ValueError("completion lost its exact pre-write receipt")
        images.append(image)
        runs.append({"directory":directory.relative_to(ROOT).as_posix(),
            "artifacts":[identity(directory/name,contract.SIZE if name.endswith('.sfc') else 0x100000) for name in
                (builder.ROM_NAME,"original_package_test.srm","original-boot.bin","original-helper.bin","audited-build.json","completion.json","source-identities.json")],
            "original_source_archives_verified":len(sources),"sections":receipt["intent_manifest"]["sections"],
            "original_output":receipt["intent_manifest"]["output"],
            "read_only_replay_output_never_created":replay_output,
            "reaudit":audit,"reproduce":receipt["reproduce"]})
    if images[0]!=images[1]: raise ValueError("independent guarded builds differ")
    history=[]
    for suffix in ("prepare1","prepare2","review_prepare3"):
        directory=ROOT/f"private/test_runs/original_package_20260908_{suffix}"
        old=json.loads(read(directory/"audited-build.json",0x100000).decode("utf-8"))
        if list(directory.glob("*.sfc")) or list(directory.glob("*.srm")) or (directory/"completion.json").exists():
            raise ValueError("preparation-only history unexpectedly contains written cartridge/SRAM")
        history.append({"directory":directory.relative_to(ROOT).as_posix(),
            "receipt":identity(directory/"audited-build.json"),
            "status":"historical preparation only; no cartridge or SRAM written",
            "source_revision":old["intent_manifest"]["sources"],
            "current_source_alignment_claimed":suffix=="review_prepare3",
            "known_receipt_limitation":"prepare1/prepare2 predate final certification pins; prepare1 reproduction omitted prepare-only" if suffix!="review_prepare3" else None})
    return {"schema":"project-epoch-original-package-cartridge-evidence-v1","date":"2026-09-08",
        "evidence_level":"verified-static","status":"two-identical-guarded-original-private-builds",
        "image_size":contract.SIZE,"identical_image_sha256":IMAGE_SHA,
        "sources":sources,"certification":certificate,"runs":runs,"preparation_history":history,
        "tests":{"builder_and_fixtures":8,"original_diagnostic_guard":19,"legacy_guard_regression":16},
        "legacy_contract":"legacy module AST unchanged apart from the two explicitly named new original-diagnostic wrappers; production catalogs remain empty",
        "independent_review":"guard, raw builder, fixtures and preparation-only full reconstruction reviewed before first image write",
        "collector":identity(Path(__file__).resolve()),
        "reproduce_metadata":"python -B tools/collect_original_snes_package_cartridge_evidence_v1.py",
        "serialization":"json.dumps(value, indent=2), UTF-8, LF, one trailing newline",
        "scope":{"contains_game_source_or_extracted_game_bytes":False,"production_approval":False,
            "native_execution_proved":False,"interrupt_safety_proved":False,"logical_pc07_runtime":False}}


if __name__=="__main__":
    print(json.dumps(collect(),indent=2))
