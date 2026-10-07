"""Stage/run the private native-loop diagnostic only after exact-source review.

Default is a read-only plan. A future, independently acquired pre-JSL checkpoint
and exact entry contract are mandatory. No Spekkio/default checkpoint is assumed.
The load chain may be coldboot validation -> pre-JSL acquisition -> fresh resume;
this runner never labels a resumed savestate as direct coldboot execution.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

import build_schala_save_layout_native_v1 as builder
import schala_save_layout_native_v1 as c
import validate_mesen_save_layout_native_v1 as validator

RUNTIME = {
    "Mesen.exe": (70470144,"d2eb03c2590c648bf329f127ebcfefd70130e7690a9e2ccdba8616faea1fe96b"),
    "MesenCore.dll": (7143424,"65f69a7bdb25c35fdca77c9c73e71ef3e8ec233380204d94cfc0179933048c74"),
    "libHarfBuzzSharp.dll": (1804872,"eb76238c9e8e41d44b5a5b18167c4c5b39ca5db4277af5dbe92d730f0fc14a7d"),
    "libSkiaSharp.dll": (None,"9a0d95e8caaa852c70d085af6a40a744242172ad9ea3fd6bc7599875a8a1dbcd"),
    "MesenNesDB.txt": (559118,"cff835b8a3d5b07d9d111382da6c49ccae150cdbaa9a0e49e15aa381af471307"),
    "settings.json": (3,"ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356"),
}


def read_regular(path: Path, *, size: int | None = None, digest: str | None = None) -> bytes:
    c.require(path.is_file() and not path.is_symlink(), f"regular nonsymlink file required: {path}")
    data = path.read_bytes()
    if size is not None:
        c.require(len(data) == size, f"input size mismatch: {path.name}")
    if digest is not None:
        c.require(c.sha256(data) == digest, f"input hash mismatch: {path.name}")
    return data


def capture_inputs(args) -> tuple[dict, dict]:
    entry_bytes = read_regular(c.private_path(args.entry_contract))
    entry = validator.strict_json(entry_bytes)
    c.entry_contract(entry, args.mode)
    inputs = {
        "entry_contract": (args.entry_contract.resolve(), entry_bytes),
        "state": (args.state.resolve(), read_regular(c.private_path(args.state), size=entry["checkpoint_size"], digest=entry["checkpoint_sha256"])),
        "sram": (args.sram.resolve(), read_regular(c.private_path(args.sram), size=8192, digest=entry["sram_sha256"])),
        "rom": (args.rom.resolve(), read_regular(c.private_path(args.rom), size=c.ROM_SIZE, digest=c.ROM_SHA256)),
    }
    for name,(size,digest) in RUNTIME.items():
        path = c.private_path(args.runtime / name)
        inputs[name] = (path, read_regular(path,size=size,digest=digest))
    return entry, inputs


def check_inputs(inputs: dict) -> None:
    for name,(path,original) in inputs.items():
        c.require(read_regular(path) == original, f"original input changed: {name}")


def run(args) -> dict:
    bundle = c.bundle_identity()
    entry, inputs = capture_inputs(args)
    output = c.private_path(args.output)
    for path,_data in inputs.values():
        c.require(not path.is_relative_to(output), "output contains an input")
    image, build_report = builder.build_image(inputs["rom"][1], output / "diagnostic.sfc")
    plan = {"schema":c.SCHEMA+"-run", "source_bundle":bundle,
            "entry_contract":entry,"build":build_report,
            "entry_contract_sha256":c.sha256(inputs["entry_contract"][1]),
            "launch_executed":False,"rom_emitted":False,
            "acquisition_then_fresh_resume":True,"direct_coldboot_load":False}
    if not args.run_reviewed_bundle:
        check_inputs(inputs)
        c.require(c.bundle_identity() == bundle, "source drift during plan")
        return plan
    c.require(args.run_reviewed_bundle == bundle["sha256"], "exact reviewed source-bundle hash required")
    c.require(not output.exists(), "run output must be a fresh private directory")
    c.require(c.bundle_identity() == bundle, "source drift before launch")
    check_inputs(inputs)
    output.mkdir(parents=True,exist_ok=False)
    app = output / "app"
    (app / "Saves").mkdir(parents=True)
    for name in RUNTIME:
        (app/name).write_bytes(inputs[name][1])
    # The complete write audit above precedes the first ROM image emission.
    rom = output / "diagnostic.sfc"
    rom.write_bytes(image)
    sram = app / "Saves" / "diagnostic.srm"
    sram.write_bytes(inputs["sram"][1])
    state = output / "entry.mss"
    state.write_bytes(inputs["state"][1])
    collector = output / "collector.lua"
    collector_bytes = (c.ROOT / "tools/mesen_save_layout_native_v1.lua").read_bytes()
    c.require(c.sha256(collector_bytes) == next(r["sha256"] for r in bundle["sources"] if r["path"].endswith(".lua")),
              "collector changed before staging")
    collector.write_bytes(collector_bytes)
    table = output / "translated_table.bin"
    table.write_bytes(c.TABLE)
    (output/"entry_contract.json").write_bytes(inputs["entry_contract"][1])
    prefix = output / "trace"
    environment = os.environ.copy()
    environment.update({"PE_SAVE_LAYOUT_PROTOCOL":c.SCHEMA,"PE_SAVE_LAYOUT_MODE":args.mode,
        "PE_SAVE_LAYOUT_SLOT":str(entry["slot"]),"PE_SAVE_LAYOUT_PREFIX":str(prefix),
        "PE_SAVE_LAYOUT_STATE":str(state),"PE_SAVE_LAYOUT_TABLE":str(table),
        "PE_SAVE_LAYOUT_ENTRY_PIN":plan["entry_contract_sha256"],"PE_SAVE_LAYOUT_BUNDLE_PIN":bundle["sha256"]})
    command = [str(app/"Mesen.exe"),"--testRunner",f"--timeout={args.timeout}",
               "--doNotSaveSettings","--debug.scriptWindow.allowIoOsAccess=true",
               "--snes.port1.type=SnesController",str(collector),str(rom)]
    (output/"build_receipt.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    process = None
    failure = None
    try:
        process = subprocess.run(command,cwd=app,env=environment,capture_output=True,text=True,
                                 timeout=args.timeout+15,check=False,
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
        c.require(process.returncode == c.SUCCESS_EXIT, f"native collector did not succeed: {process.returncode}")
        c.require(not Path(str(prefix)+".error.txt").exists(), "collector error file")
        plan["validation"] = validator.validate_run(prefix,inputs["entry_contract"][1],bundle["sha256"])
    except Exception as exc:
        failure = exc
    finally:
        # Originals are checked even when the emulator/validator fails. Staged
        # battery data may change after deferred stop; it is not our evidence.
        try:
            check_inputs(inputs)
            c.require(c.bundle_identity() == bundle, "source changed during native run")
            c.require(rom.read_bytes() == image and state.read_bytes() == inputs["state"][1]
                      and collector.read_bytes() == collector_bytes and table.read_bytes() == c.TABLE,
                      "immutable staged input changed")
        except Exception as exc:
            failure = exc
        plan["launch_executed"] = True
        plan["rom_emitted"] = True
        plan["status"] = "quarantined-failure" if failure else "accepted-instrumented-interval"
        plan["failure"] = str(failure) if failure else None
        plan["returncode"] = process.returncode if process else None
        plan["shutdown_sram_is_authoritative"] = False
        (output/"run_receipt.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    if failure:
        raise failure
    return plan


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode",choices=("save","load"),required=True)
    parser.add_argument("--entry-contract",type=Path,required=True)
    parser.add_argument("--state",type=Path,required=True)
    parser.add_argument("--sram",type=Path,required=True)
    parser.add_argument("--rom",type=Path,default=c.DEFAULT_ROM)
    parser.add_argument("--runtime",type=Path,default=c.ROOT/"private/tools/mesen2/app")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--timeout",type=int,default=30)
    parser.add_argument("--run-reviewed-bundle")
    args=parser.parse_args()
    c.require(1 <= args.timeout <= 60, "timeout must be 1..60 seconds")
    print(json.dumps(run(args),indent=2,sort_keys=True))


if __name__ == "__main__":
    main()
