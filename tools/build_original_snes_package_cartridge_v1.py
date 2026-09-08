"""Build an original private test cartridge after intent and complete-diff audits.

No source ROM argument exists. Asar assembles raw original components only;
the cartridge is constructed in memory from a literal eight-MiB FF image.
All outputs are exclusive, below a new ignored private/test_runs directory.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

import original_snes_diagnostic_write_contract_v1 as contract
import original_snes_package_fixtures_v1 as fixtures
import validate_rom_write_intents as guard

ROOT = Path(__file__).resolve().parents[1]
ASAR = ROOT / "private/tools/asar-1.91/asar.exe"
ASAR_SIZE = 501248
ASAR_SHA256 = "ecb04bce4a9a5a3b4dab4c9fafdc7875f30763fec15dec640b9cac11e11496e8"
ROM_NAME = "original_package_test.sfc"
HELPER_SOURCE = "asm/schala_package_helper_v2_stack.asm"
BOOT_SOURCE = "asm/original_snes_package_cartridge_v1.asm"
ZERO_SRAM_SHA256 = "9f1dcbc35c350d6027f98be0f5c8b43b42ca52b7604459c0c42be3aa88913d47"


def identity(data):
    return {"size":len(data),"sha256":hashlib.sha256(data).hexdigest()}


def verify_asar():
    with ASAR.open("rb") as stream: data=stream.read(ASAR_SIZE+1)
    if identity(data)!={"size":ASAR_SIZE,"sha256":ASAR_SHA256}:
        raise ValueError("pinned Asar executable identity mismatch")


def exclusive(path, data):
    # The validated directory belongs to this one build. Recheck it immediately
    # before every creation and never truncate or replace an existing artifact.
    relative = path.relative_to(ROOT).as_posix()
    contract.relative_path(relative, "private artifact")
    probe = relative if path.suffix == ".sfc" else relative + ".sfc"
    contract.output_path(probe, ROOT)
    if path.is_symlink() or (hasattr(path,"is_junction") and path.is_junction()) or path.exists():
        raise ValueError("refusing existing or aliased artifact")
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def original_sources():
    result=[]
    for relative in sorted(contract.SOURCE_PATHS):
        path=ROOT/relative
        if path.resolve(strict=True)!=path or not path.is_file():
            raise ValueError("original source must be an unaliased regular file")
        with path.open("rb") as stream:
            data=stream.read(0x100001)
        if not 0<len(data)<=0x100000:
            raise ValueError("original source exceeds bounds")
        result.append({"path":relative,**identity(data),"provenance":"reviewed-original-project-source"})
    return result


def assemble_raw(directory, name, source_text, *, maximum):
    source=directory/(name+".asm")
    target=directory/(name+".bin")
    exclusive(source,source_text.encode("utf-8"))
    exclusive(target,b"")
    command=[str(ASAR),"--no-title-check","--fix-checksum=off",str(source),str(target)]
    result=subprocess.run(command,cwd=directory,capture_output=True,timeout=30,
                          creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    exclusive(directory/(name+".asar.stdout.txt"),result.stdout)
    exclusive(directory/(name+".asar.stderr.txt"),result.stderr)
    if result.returncode:
        raise ValueError(f"Asar raw component {name} failed; private output retained")
    with target.open("rb") as stream:
        data=stream.read(maximum+1)
    if not 0<len(data)<=maximum:
        raise ValueError("raw component extent outside fixed diagnostic capacity")
    return data,{"command":command,"returncode":result.returncode,
                 "wrapper":identity(source_text.encode("utf-8")),"component":identity(data),
                 "stdout":identity(result.stdout),"stderr":identity(result.stderr)}


def make_header():
    header=bytearray(64)
    header[:21]=contract.TITLE
    header[21:28]=bytes([0x35,2,13,3,1,0x33,0])
    header[28:32]=b"\xff\xff\x00\x00"
    vectors=[0x80A0]*16
    for index in (5,13): vectors[index]=0x8080
    for index in (7,15): vectors[index]=0x8090
    for index in (6,14): vectors[index]=0x8000
    header[32:64]=b"".join(v.to_bytes(2,"little") for v in vectors)
    if len(header)!=64: raise ValueError("original header extent mismatch")
    return bytes(header)


def build_image(boot, helper, packages, registry, sources, output):
    """Pure in-memory construction; guard both intent and complete image."""
    image=bytearray(b"\xff"*contract.SIZE)
    header=make_header()
    payloads={"original-boot":boot,"boot-mirror":boot,
              "original-header":header,"header-mirror":header,
              "original-helper":helper,"authored-packages":packages,"immutable-registry":registry}
    role_sources={
        "original-boot":[BOOT_SOURCE],"boot-mirror":[BOOT_SOURCE],
        "original-header":["tools/build_original_snes_package_cartridge_v1.py"],
        "header-mirror":["tools/build_original_snes_package_cartridge_v1.py"],
        "original-helper":[HELPER_SOURCE,"tools/build_original_snes_package_cartridge_v1.py"],
        "authored-packages":["tools/original_snes_package_fixtures_v1.py"],
        "immutable-registry":["tools/original_snes_package_fixtures_v1.py"]}
    sections=[]
    for section_id,(start,capacity,kind) in contract.SECTIONS.items():
        payload=payloads[section_id]
        if type(payload) is not bytes or not 0<len(payload)<=capacity:
            raise ValueError("original component type or capacity mismatch")
        image[start:start+len(payload)]=payload
        sections.append({"id":section_id,"file_start":start,"size":len(payload),
            "owner":contract.OWNER,"payload_kind":kind,"evidence_level":"verified-static",
            "source_paths":sorted(role_sources[section_id]),
            "preimage_sha256":contract.sha(b"\xff"*len(payload)),"replacement_sha256":contract.sha(payload)})
    checksum=sum(image)&0xffff
    for start in (0xffc0,0x40ffc0):
        image[start+28:start+32]=(checksum^0xffff).to_bytes(2,"little")+checksum.to_bytes(2,"little")
    for section in sections:
        start=section["file_start"]
        section["replacement_sha256"]=contract.sha(image[start:start+section["size"]])
    target=bytes(image)
    manifest={"schema":contract.SCHEMA,"build_mode":contract.MODE,
        "source":{"kind":"literal-all-ff-8mib","size":contract.SIZE,"sha256":contract.BLANK_SHA256},
        "target":identity(target),"sources":sources,"sections":sections,"output":output}
    intent=guard.validate_original_diagnostic_manifest(manifest)
    audit=guard.audit_original_diagnostic_images(manifest,b"\xff"*contract.SIZE,target)
    if intent["status"]!="metadata-valid" or audit["status"]!="images-valid" or not audit["complete_diff_coverage"]:
        raise ValueError("original cartridge guard did not explicitly pass")
    return target,manifest,audit


def build(output_dir:Path, *, prepare_only=False):
    output_dir=output_dir if output_dir.is_absolute() else ROOT/output_dir
    lexical=output_dir/ROM_NAME
    try: relative=lexical.relative_to(ROOT).as_posix()
    except ValueError as exc: raise ValueError("output is outside this workspace") from exc
    output=contract.output_path(relative)
    output_dir=output.parent
    if output_dir.exists(): raise ValueError("a fresh private run directory is required")
    sources=original_sources()
    verify_asar()
    packages,registry,certificate=fixtures.build()
    output_dir.mkdir(parents=True,exist_ok=False)
    # Retain exact original inputs and all failures under this private run.
    exclusive(output_dir/"source-identities.json",(json.dumps(sources,indent=2)+"\n").encode("utf-8"))
    for source in sources:
        with (ROOT/source["path"]).open("rb") as stream:
            data=stream.read(source["size"]+1)
        if identity(data)!={"size":source["size"],"sha256":source["sha256"]}:
            raise ValueError("source changed before private snapshot")
        exclusive(output_dir/(source["path"].replace("/","__")+".source.txt"),data)
    boot_text=(ROOT/BOOT_SOURCE).read_text(encoding="utf-8")
    helper_path=(ROOT/HELPER_SOURCE).as_posix()
    wrapper=("norom\norg $000000\nbase $410000\n"
             "!PE_PH2_BINDINGS = $430000\n!PE_PH2_TARGETS = $430100\n"
             "!PE_PH2_CANONICAL_TAIL = $008100\n!PE_PH2_SUCCESS_TAIL = $008110\n"
             "!PE_PH2_REFUSAL_TAIL = $008120\n"
             f'incsrc "{helper_path}"\n')
    boot,boot_receipt=assemble_raw(output_dir,"original-boot",boot_text,maximum=0x1000)
    helper,helper_receipt=assemble_raw(output_dir,"original-helper",wrapper,maximum=0x4000)
    verify_asar()
    if original_sources()!=sources:
        raise ValueError("original source drift during component assembly")
    image,intents,audit=build_image(boot,helper,packages,registry,sources,relative)
    sram=bytes(0x2000)
    if contract.sha(sram)!=ZERO_SRAM_SHA256: raise ValueError("zero SRAM invariant failed")
    receipt={"schema":"project-epoch-original-package-cartridge-build-v1",
        "status":"audited-in-memory-no-image-written" if prepare_only else "audited-before-exclusive-image-write",
        "evidence_level":"verified-static","intent_manifest":intents,"complete_diff_audit":audit,
        "assembler":{"path":"private/tools/asar-1.91/asar.exe","size":ASAR_SIZE,"sha256":ASAR_SHA256},
        "components":{"boot":boot_receipt,"helper":helper_receipt},"package_certificate":certificate,
        "sram":identity(sram),"production_approval":False,"runtime_executed":False,
        "reproduce":"python -B tools/build_original_snes_package_cartridge_v1.py --output-dir private/test_runs/original_package_NEW_UNIQUE"+(" --prepare-only" if prepare_only else "")}
    exclusive(output_dir/"audited-build.json",(json.dumps(receipt,indent=2)+"\n").encode("utf-8"))
    if prepare_only:
        return receipt
    # Revalidate all sources, paths and bytes at the write boundary. There is no
    # ROM writer before this second complete audit; Asar only saw .bin files.
    verify_asar()
    if fixtures.build()!=(packages,registry,certificate):
        raise ValueError("package certification changed before image writing")
    guard.audit_original_diagnostic_images(intents,b"\xff"*contract.SIZE,image)
    if contract.output_path(relative)!=output: raise ValueError("output path changed before write")
    exclusive(output,image)
    exclusive(output.with_suffix(".srm"),sram)
    with output.open("rb") as stream: written=stream.read(contract.SIZE+1)
    if identity(written)!=intents["target"]:
        raise ValueError("exclusive written image identity mismatch")
    with output.with_suffix(".srm").open("rb") as stream: written_sram=stream.read(0x2001)
    if identity(written_sram)!=identity(sram):
        raise ValueError("exclusive written SRAM identity mismatch")
    completion={"schema":"project-epoch-original-package-cartridge-completion-v1",
        "status":"written-and-rehashed","rom":identity(written),"sram":identity(written_sram),
        "audited_build_sha256":contract.sha((output_dir/"audited-build.json").read_bytes()),
        "evidence_level":"verified-static","runtime_executed":False,"production_approval":False}
    exclusive(output_dir/"completion.json",(json.dumps(completion,indent=2)+"\n").encode("utf-8"))
    return completion


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument("--prepare-only",action="store_true",help="assemble and audit only in memory; write no cartridge or SRAM")
    args=parser.parse_args()
    result=build(args.output_dir,prepare_only=args.prepare_only)
    print(json.dumps({"status":result["status"],"output_directory":str(args.output_dir),
                     "evidence_level":result["evidence_level"],"production_approval":False},indent=2))
