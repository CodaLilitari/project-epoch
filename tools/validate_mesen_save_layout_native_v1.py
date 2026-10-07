"""Independently replay a private native-loop ledger and reject incomplete evidence.

Raw snapshots/trace remain private. Returned metadata contains no game arrays.
The accepted interval ends before RTL; deferred-stop execution is excluded.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

import inspect_ct_srm
import schala_save_layout as layout
import schala_save_layout_native_v1 as c

SNAPSHOTS = ("entry", "prepared", "table", "copy_complete", "restored", "terminal")


def strict_json(raw: bytes):
    def pairs(items):
        obj = {}
        for key, value in items:
            c.require(key not in obj, "duplicate JSON key")
            obj[key] = value
        return obj
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _v: (_ for _ in ()).throw(c.ContractError("nonfinite JSON")))


def integer(value, low: int, high: int, label: str) -> int:
    c.require(type(value) is int and low <= value <= high, label)
    return value


def physical_offset(bus: int, space: str) -> int:
    """Independent accepted-address normalization, including low WRAM mirrors.

    SRAM aliases beyond bank $30 are deliberately unmodeled and fail closed.
    The collector itself records all physical SRAM events, including aliases.
    """
    bank, word = bus >> 16, bus & 0xFFFF
    if space == "wram":
        if bank in (0x7E, 0x7F):
            return bus - 0x7E0000
        if (bank <= 0x3F or 0x80 <= bank <= 0xBF) and word < 0x2000:
            return word
    elif space == "sram" and bank == 0x30 and 0x6000 <= word <= 0x7FFF:
        return word - 0x6000
    elif space == "table_rom" and 0xFFFA7B <= bus <= 0xFFFAA2:
        return bus - 0xFFFA7B
    raise c.ContractError("unmodeled physical bus alias")


def validate_records(records: list[dict], snapshots: dict[str, tuple[bytes, bytes]],
                     entry: dict, entry_pin: str, bundle_pin: str) -> dict:
    c.entry_contract(entry, entry["mode"])
    mode, slot = entry["mode"], entry["slot"]
    sites = c.MODES[mode]
    c.require(1 < len(records) <= c.MAX_RECORDS, "record count")
    c.require(set(snapshots) == set(SNAPSHOTS), "snapshot inventory mismatch")
    for wram, sram in snapshots.values():
        c.require(type(wram) is bytes and len(wram) == 0x20000 and
                  type(sram) is bytes and len(sram) == 0x2000, "snapshot shape")
    header = records[0]
    c.require(header == {"kind": "header", "schema": c.SCHEMA, "mode": mode, "slot": slot,
                        "entry_pin": entry_pin, "bundle_pin": bundle_pin,
                        "stop_is_deferred": True}, "trace provenance/header mismatch")
    initial_wram, initial_sram = snapshots["entry"]
    c.require(c.sha256(initial_sram) == entry["sram_sha256"], "loaded SRAM differs from pinned entry source")
    c.require(initial_wram[0x2C9C:0x2D00] == bytes(100), "candidate/guards preimage")
    c.require(initial_wram[0x500:0x508] == bytes.fromhex("5c0e84c25c7284c2") and
              initial_wram[0xD01] >= 128, "menu interrupt premises")
    c.require(initial_wram[0x79] == slot and initial_wram[0x51:0x53] == b"\0\0", "entry slot/zero word")
    natural = initial_wram[0x2830:0x2880]
    candidate = initial_wram[0x2CA0:0x2CF0]
    c.require(natural != c.MARKER, "marker must distinguish compatibility")
    base = slot * 0xA00
    if mode == "load":
        checksum = inspect_ct_srm.slot_checksum(initial_sram[base:base + 0xA00])
        c.require(initial_sram[0x1FF8 + slot * 2:0x1FFA + slot * 2] == b"\x1b\xe4" and
                  int.from_bytes(initial_sram[0x1FF0 + slot * 2:0x1FF2 + slot * 2], "little") == checksum,
                  "load requires host-validated native magic/checksum")
        c.require(initial_sram[base+0x430:base+0x480] != c.LOAD_POISON, "load poison indistinguishable")
    state = {"wram": bytearray(initial_wram), "sram": bytearray(initial_sram),
             "table_rom": bytearray(c.VANILLA_TABLE)}
    seen, purposes, loop_indices, comparisons = [], [], [], []
    bus_counts = collections.Counter()
    native_copy_reads, native_copy_writes = [], []
    transfer_events, table_events = [], []
    checksum_reads, checksum_writes, magic_writes = [], [], []
    moved_wram = {region.address + (0x10000 if region.bank == 0x7F else 0) + i
                  for region in layout.PROJECT_EPOCH_REGIONS for i in range(region.length)}
    allowed_sram_writes = set(range(base, base+0x834)) | {
        0x1FE0,0x1FE1,0x1FF0+slot*2,0x1FF1+slot*2,0x1FF8+slot*2,0x1FF9+slot*2}
    copy_phase = False
    entry_cpu = None
    saved_table = None
    last_clock = None
    last_exec = None
    success = False
    for position, event in enumerate(records[1:], 1):
        c.require(type(event) is dict and type(event.get("kind")) is str, "event object")
        kind = event["kind"]
        if kind == "snapshot":
            c.require(set(event) == {"kind", "name", "cpu"}, "snapshot fields")
            name, cpu = event["name"], event["cpu"]
            c.require(len(seen) < len(SNAPSHOTS) and name == SNAPSHOTS[len(seen)], "snapshot order")
            c.require(snapshots[name] == (bytes(state["wram"]), bytes(state["sram"])),
                      f"unexplained memory difference at {name}")
            expected_pc = sites["entry"] if name in ("entry", "prepared") else (
                sites["table"] if name == "table" else (
                    sites["terminal"] if name == "terminal" else sites["copy_complete"]))
            c.require(cpu["pc24"] == expected_pc, "snapshot instruction boundary")
            if name == "entry":
                entry_cpu = cpu
                sp = integer(cpu["sp"], 0x100, 0x1FFC, "entry SP")
                c.require(cpu["emulationMode"] is False and cpu["d"] == 0 and cpu["dbr"] == 0x7E,
                          "entry native/D/DBR")
                c.require(int.from_bytes(initial_wram[sp+1:sp+4], "little") == sites["caller"],
                          "actual native JSL frame mismatch")
            elif name == "prepared":
                c.require(purposes == ["prepare-candidate", "prepare-marker"], "preparation order")
                copy_phase = True
            elif name == "table":
                c.require(cpu["a"] == 0xFFFF and cpu["x"] == 0xFAA3 and cpu["y"] == 0x98B8
                          and cpu["d"] == 0 and cpu["dbr"] == 0x7E and cpu["ps"] & 0x30 == 0,
                          "post-MVN CPU contract")
                saved_table = bytes(state["wram"][0x9890:0x98C2])
                c.require(saved_table[:40] == c.VANILLA_TABLE, "vanilla table copy mismatch")
            elif name == "copy_complete":
                c.require(loop_indices == list(range(0, 50, 5)) and comparisons == list(range(5, 51, 5)),
                          "ten iterations not witnessed")
                c.require(state["wram"][0x2830:0x2880] == c.MARKER, "marker damaged by native copy")
                copy_phase = False
            elif name == "restored":
                c.require(purposes == ["prepare-candidate", "prepare-marker", "translated-table",
                                       "restore-natural", "restore-candidate", "restore-table"], "restoration order")
            elif name == "terminal":
                c.require(cpu["sp"] == entry_cpu["sp"] and cpu["ps"] == entry_cpu["ps"], "pre-RTL CPU balance")
            seen.append(name)
        elif kind == "inject":
            c.require(set(event) == {"kind", "purpose", "address", "hex", "pc"}, "injection fields")
            purpose = event["purpose"]
            index = len(purposes)
            order = ["prepare-candidate", "prepare-marker", "translated-table",
                     "restore-natural", "restore-candidate", "restore-table"]
            c.require(index < len(order) and purpose == order[index], "extra/reordered diagnostic injection")
            expected = {
                "prepare-candidate": (0x2CA0, natural if mode == "save" else c.LOAD_POISON, "entry", sites["entry"]),
                "prepare-marker": (0x2830, c.MARKER, "entry", sites["entry"]),
                "translated-table": (0x9890, c.TABLE, "table", sites["table"]),
                "restore-natural": (0x2830, natural if mode == "save" else
                                    snapshots["copy_complete"][0][0x2CA0:0x2CF0], "copy_complete", sites["copy_complete"]),
                "restore-candidate": (0x2CA0, candidate, "copy_complete", sites["copy_complete"]),
                "restore-table": (0x9890, saved_table, "copy_complete", sites["copy_complete"]),
            }[purpose]
            address, data, required_snapshot, pc = expected
            c.require(seen and seen[-1] == required_snapshot and data is not None and
                      event["address"] == address and event["pc"] == pc and event["hex"] == data.hex(),
                      "unapproved injection bytes/span/boundary")
            state["wram"][address:address + len(data)] = data
            purposes.append(purpose)
        elif kind == "exec":
            c.require(set(event) == {"kind", "pc", "cpu"}, "exec fields")
            cpu = event["cpu"]
            last_exec = event["pc"]
            try:
                code_offset = physical_offset(last_exec,"wram")
            except c.ContractError:
                code_offset = -1
            c.require(not (0x2830 <= code_offset < 0x2880 or 0x2CA0 <= code_offset < 0x2CF0 or
                           0x9890 <= code_offset < 0x98C2), "execution entered diagnostic data span")
            c.require(event["pc"] == cpu["pc24"] == ((cpu["k"] << 16) | cpu["pc"]), "exec PC encoding")
            now = integer(cpu["clock"], 0, (1 << 63) - 1, "full master clock")
            c.require(entry_cpu is not None and now >= entry_cpu["clock"] and
                      now - entry_cpu["clock"] <= 1000000 and (last_clock is None or now >= last_clock), "clock order/bound")
            last_clock = now
            c.require(state["wram"][0xD01] >= 128, "negative menu task flag lost")
            if event["pc"] == sites["loop"]:
                c.require(seen[-1] == "table" and "translated-table" in purposes, "loop before injection")
                loop_indices.append(cpu["x"] if mode == "save" else cpu["y"])
            elif event["pc"] == sites["cmp"]:
                comparisons.append(cpu["a"])
        elif kind == "bus":
            c.require(set(event) == {"kind", "space", "op", "address", "value", "bus_address", "pc"}, "bus fields")
            space, op = event["space"], event["op"]
            c.require(space in state and op in ("read", "write") and seen, "bus scope")
            c.require(last_exec is not None and event["pc"] == last_exec, "bus row lacks latest exec witness")
            address = integer(event["address"], 0, len(state[space])-1, "physical bus offset")
            integer(event["bus_address"], 0, 0xFFFFFF, "CPU bus address")
            c.require(physical_offset(event["bus_address"], space) == address,
                      "reported physical mapping disagrees with bus alias")
            value = integer(event["value"], 0, 255, "bus byte")
            if space == "sram" and op == "write":
                c.require(mode == "save" and address in allowed_sram_writes,
                          "observed write outside selected save SRAM footprint")
                if base <= address < base+0x834:
                    c.require(copy_phase, "serialized-prefix write after copy completion")
            if copy_phase and space == "wram":
                c.require(not 0x2830 <= address < 0x2880, "native marker access")
                c.require(not 0x2C9C <= address < 0x2CA0 and not 0x2CF0 <= address < 0x2D00,
                          "native guard access")
                if 0x2CA0 <= address < 0x2CF0:
                    c.require(event["pc"] == 0x7E9690 and op == ("read" if mode == "save" else "write"),
                              "unexpected relocated compatibility access")
                if op == "write" and "translated-table" in purposes:
                    c.require(not 0x9890 <= address < 0x98C2, "native injected-table write")
                if op == "write" and 0x9690 <= address < 0x9694:
                    c.require(event["pc"] in (0xFFFA11, 0xFFFA17, 0xFFFA32, 0xFFFAA9, 0xFFFAAF, 0xFFFAC9),
                              "unexpected MVN stub writer")
            if op == "read":
                c.require(state[space][address] == value, "read contradicts complete memory replay")
            else:
                c.require(space != "table_rom", "ROM write in read-only table ledger")
                state[space][address] = value
            bus_counts[(space, op)] += 1
            if event["pc"] == 0x7E9690 and space == "sram":
                (native_copy_reads if op == "read" else native_copy_writes).append((address, value))
            relevant_transfer = ((space == "wram" and address in moved_wram and
                                  op == ("read" if mode == "save" else "write")) or
                                 (space == "sram" and base <= address < base+0x834 and
                                  op == ("write" if mode == "save" else "read")))
            if event["pc"] == 0x7E9690 and relevant_transfer:
                transfer_events.append((space,op,address,value))
            relevant_table = space == "table_rom" or (space == "wram" and op == "write" and
                                                       0x9890 <= address < 0x98B8)
            if event["pc"] == (0xFFFA23 if mode == "save" else 0xFFFABB) and relevant_table:
                table_events.append((space,op,address,value))
            if space == "sram" and event["pc"] == 0xFFFBFB and op == "read":
                checksum_reads.append((address,value))
            if space == "sram" and event["pc"] == 0xFFFA58 and op == "write":
                checksum_writes.append((address,value))
            if space == "sram" and event["pc"] == 0xFFFA5F and op == "write":
                magic_writes.append((address,value))
        elif kind == "success":
            c.require(position == len(records)-1 and seen == list(SNAPSHOTS) and
                      event == {"kind": "success", "loops": 10, "comparisons": 10,
                                "terminal_before_rtl": True, "post_stop_execution_excluded": True},
                      "invalid/early success terminal")
            success = True
        else:
            raise c.ContractError("unknown/failure event")
    c.require(success, "missing success terminal")
    expected_table = []
    for i,value in enumerate(c.VANILLA_TABLE):
        expected_table.extend((("table_rom","read",i,value),("wram","write",0x9890+i,value)))
    c.require(table_events == expected_table, "incomplete/reordered original table-copy bus pairs")
    c.require(len(transfer_events) == 2*0x834, "incomplete translated MVN read/write pairs")
    serialized = bytearray()
    cursor = 0
    for region in layout.PROJECT_EPOCH_REGIONS:
        offset = region.address + (0x10000 if region.bank == 0x7F else 0)
        for i in range(region.length):
            read,write = transfer_events[2*cursor:2*cursor+2]
            source_space,source_address = ("wram",offset+i) if mode == "save" else ("sram",base+cursor)
            target_space,target_address = ("sram",base+cursor) if mode == "save" else ("wram",offset+i)
            c.require(read[:3] == (source_space,"read",source_address) and
                      write == (target_space,"write",target_address,read[3]),
                      "translated MVN source/destination pair mismatch")
            serialized.append(read[3])
            cursor += 1
    complete_wram, complete_sram = snapshots["copy_complete"]
    final_wram, final_sram = snapshots["terminal"]
    if mode == "save":
        expected = bytes(serialized)
        c.require(native_copy_writes == [(base+i, b) for i, b in enumerate(expected)] and not native_copy_reads,
                  "SRAM bus sequence during last-exec MVN context mismatch")
        c.require(complete_sram[base:base+0x834] == expected and
                  final_sram[base:base+0x834] == expected and
                  complete_wram[0x2CA0:0x2CF0] == natural, "save copy result mismatch")
        checksum = inspect_ct_srm.slot_checksum(final_sram[base:base+0xA00])
        expected_checksum_reads = [(base+word+i,final_sram[base+word+i])
                                   for word in range(0x9FE,-1,-2) for i in (0,1)]
        c.require(checksum_reads == expected_checksum_reads, "native checksum read sequence incomplete")
        c.require(checksum_writes == [(0x1FF0+slot*2+i,b) for i,b in enumerate(checksum.to_bytes(2,"little"))]
                  and magic_writes == [(0x1FF8+slot*2,0x1B),(0x1FF9+slot*2,0xE4)],
                  "native checksum/magic publications incomplete")
        c.require(final_sram[0x1FF0+slot*2:0x1FF2+slot*2] == checksum.to_bytes(2,"little") and
                  final_sram[0x1FF8+slot*2:0x1FFA+slot*2] == b"\x1b\xe4", "native final checksum/magic mismatch")
        c.require(all(a in allowed_sram_writes for a,(old,new) in enumerate(zip(initial_sram,final_sram)) if old!=new),
                  "save changed other slot/tail/global SRAM")
    else:
        expected = initial_sram[base:base+0x834]
        c.require(native_copy_reads == [(base+i,b) for i,b in enumerate(expected)] and not native_copy_writes,
                  "SRAM bus read sequence during last-exec MVN context mismatch")
        # Exact paired stores prove each region at the time of publication.
        # Later observed clock/input writes are already reconciled above; do
        # not incorrectly require every destination to remain frozen until exit.
        c.require(complete_wram[0x2CA0:0x2CF0] == expected[0x430:0x480],
                  "loaded compatibility changed before restoration")
        c.require(final_sram == initial_sram and bus_counts[("sram","write")] == 0, "loader wrote SRAM")
    expected_natural = natural if mode == "save" else initial_sram[base+0x430:base+0x480]
    c.require(final_wram[0x2830:0x2880] == expected_natural and final_wram[0x2CA0:0x2CF0] == candidate,
              "synchronous compatibility restoration mismatch")
    return {"schema": c.SCHEMA + "-validation", "mode": mode, "slot": slot,
            "evidence": "verified-runtime", "scope": "instrumented-native-ten-region-loop-only",
            "records": len(records), "bus_counts": {f"{a}_{b}":n for (a,b),n in sorted(bus_counts.items())},
            "native_copy_bytes": 0x834, "native_copy_iterations":10,
            "clock_span": last_clock-entry_cpu["clock"],
            "entry_sram_sha256":c.sha256(initial_sram), "terminal_sram_sha256":c.sha256(final_sram),
            "marker_preserved_during_copy":True,"compatibility_restored_before_stop_request":True,
            "post_stop_execution_proved":False,"caller_return_observed":False,
            "native_load_validation_observed_in_this_trace":False,
            "bus_callbacks_include_dma":True,"bus_pc_is_last_cpu_exec_not_dma_owner":True,
            "complete_native_control_flow_proved":False,"paired_table_copy_bytes":40,
            "save_checksum_reads":len(checksum_reads),"memory_snapshot_reconciled_with_observed_bus":True,
            "playable_pc07":False,"sidecar_installed":False,"production_allocation_approved":False}


def validate_run(prefix: Path, entry_bytes: bytes, bundle_pin: str) -> dict:
    prefix = c.private_path(prefix)
    entry = strict_json(entry_bytes)
    c.entry_contract(entry, entry["mode"])
    trace = Path(str(prefix)+".jsonl").read_bytes()
    c.require(len(trace) <= 64*1024*1024 and trace.endswith(b"\n"), "trace size/termination")
    records = [strict_json(line) for line in trace.splitlines()]
    snapshots = {name: (Path(str(prefix)+f".{name}.wram.bin").read_bytes(),
                        Path(str(prefix)+f".{name}.sram.bin").read_bytes()) for name in SNAPSHOTS}
    report = validate_records(records, snapshots, entry, c.sha256(entry_bytes), bundle_pin)
    report["trace_sha256"] = c.sha256(trace)
    report["snapshot_hashes"] = {name:{"wram":c.sha256(w),"sram":c.sha256(s)} for name,(w,s) in snapshots.items()}
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix",type=Path,required=True)
    parser.add_argument("--entry-contract",type=Path,required=True)
    parser.add_argument("--bundle-sha256",required=True)
    args=parser.parse_args()
    print(json.dumps(validate_run(args.prefix,args.entry_contract.read_bytes(),args.bundle_sha256),indent=2,sort_keys=True))


if __name__ == "__main__":
    main()
