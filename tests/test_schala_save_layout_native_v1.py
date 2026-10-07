"""Adversarial host tests; all trace fixtures below are synthetic original data.

The optional canonical-input test builds only in memory. No patched image or
emulator execution is performed by this suite.
"""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import build_schala_save_layout_native_v1 as builder
import inspect_ct_srm
import schala_save_layout as layout
import schala_save_layout_native_v1 as c
import validate_mesen_save_layout_native_v1 as v
import validate_rom_write_intents as guard


def fixture(mode="save", interrupts=False):
    sites=c.MODES[mode]
    w=bytearray((i*17+33)%256 for i in range(0x20000))
    s=bytearray((i*29+71)%256 for i in range(0x2000))
    w[0x2C9C:0x2D00]=bytes(100)
    w[0x500:0x508]=bytes.fromhex("5c0e84c25c7284c2")
    w[0xD01]=255; w[0x79]=0; w[0x51:0x53]=bytes(2)
    sp=0xA78; ps=0xA1
    w[sp+1:sp+4]=sites["caller"].to_bytes(3,"little")
    if mode=="load":
        w[0x2400]=s[0]  # Deliberately same-value first native destination store.
        s[0x1FF8:0x1FFA]=b"\x1b\xe4"
        s[0x1FF0:0x1FF2]=inspect_ct_srm.slot_checksum(bytes(s[:0xA00])).to_bytes(2,"little")
    initial_w=bytes(w); initial_s=bytes(s)
    contract={"schema":c.SCHEMA+"-entry","mode":mode,"checkpoint_size":123,
        "checkpoint_sha256":"1"*64,"checkpoint_pc":0xC2CF51 if mode=="save" else 0xC2E657,
        "sram_sha256":c.sha256(initial_s),"slot":0,"entry_pc":sites["entry"],
        "caller_return":sites["caller"],"evidence":"verified-runtime",
        "acquisition_reference":"synthetic test fixture, not native evidence"}
    records=[{"kind":"header","schema":c.SCHEMA,"mode":mode,"slot":0,
        "entry_pin":"2"*64,"bundle_pin":"3"*64,"stop_is_deferred":True}]
    snaps={}; clock=0; lastpc=sites["entry"]
    def cpu(pc,**extra):
        nonlocal clock
        clock+=8
        result={"a":0xCFFF,"x":0,"y":1,"d":0,"dbr":0x7E,"sp":sp,
            "ps":ps,"k":pc>>16,"pc":pc&65535,"pc24":pc,"emulationMode":False,"clock":clock}
        result.update(extra)
        return result
    def execute(pc,**extra):
        nonlocal lastpc
        lastpc=pc; records.append({"kind":"exec","pc":pc,"cpu":cpu(pc,**extra)})
    def snap(name,pc,**extra):
        snaps[name]=(bytes(w),bytes(s))
        records.append({"kind":"snapshot","name":name,"cpu":cpu(pc,**extra)})
    def inject(purpose,address,data,pc):
        records.append({"kind":"inject","purpose":purpose,"address":address,"hex":data.hex(),"pc":pc})
        w[address:address+len(data)]=data
    def bus(space,op,address,value):
        mapping={"wram":0x7E0000,"sram":0x306000,"table_rom":0xFFFA7B}
        records.append({"kind":"bus","space":space,"op":op,"address":address,
                        "bus_address":mapping[space]+address,"value":value,"pc":lastpc})
        if op=="write":
            (w if space=="wram" else s)[address]=value
    snap("entry",sites["entry"])
    inject("prepare-candidate",0x2CA0,initial_w[0x2830:0x2880] if mode=="save" else c.LOAD_POISON,sites["entry"])
    inject("prepare-marker",0x2830,c.MARKER,sites["entry"])
    snap("prepared",sites["entry"])
    execute(sites["entry"])
    for i,b in enumerate(c.VANILLA_TABLE):
        execute(0xFFFA23 if mode=="save" else 0xFFFABB)
        bus("table_rom","read",i,b); bus("wram","write",0x9890+i,b)
    if interrupts:
        # Hardware-frame stores can retain last CPU exec=MVN. These physical
        # stack writes are reconciled but must not inflate table-copy pairs.
        bus("wram","write",0xA77,17)
    execute(sites["table"],a=0xFFFF,x=0xFAA3,y=0x98B8,ps=0x81)
    snap("table",sites["table"],a=0xFFFF,x=0xFAA3,y=0x98B8,ps=0x81)
    original_table=bytes(w[0x9890:0x98C2])
    inject("translated-table",0x9890,c.TABLE,sites["table"])
    cursor=0
    for ordinal,region in enumerate(layout.PROJECT_EPOCH_REGIONS):
        if interrupts and ordinal==4:
            execute(0xC28473)
            bus("wram","write",0x0400,(w[0x0400]+1)&255)
        execute(sites["loop"],x=ordinal*5,y=ordinal*5)
        offset=region.address+(65536 if region.bank==0x7F else 0)
        for i in range(region.length):
            execute(0x7E9690)
            if mode=="save":
                value=w[offset+i]
                bus("wram","read",offset+i,value); bus("sram","write",cursor,value)
            else:
                value=s[cursor]
                bus("sram","read",cursor,value); bus("wram","write",offset+i,value)
            cursor+=1
        if interrupts and ordinal==4:
            # A DMA read outside either copy domain may share the MVN's
            # latest-exec annotation. Later NMI clocks may alter loaded $0400.
            bus("wram","read",0x7000,w[0x7000])
            execute(0xC28473)
            bus("wram","write",0x0400,(w[0x0400]+1)&255)
        execute(sites["cmp"],a=(ordinal+1)*5)
    execute(sites["copy_complete"])
    snap("copy_complete",sites["copy_complete"])
    restored=initial_w[0x2830:0x2880] if mode=="save" else bytes(w[0x2CA0:0x2CF0])
    inject("restore-natural",0x2830,restored,sites["copy_complete"])
    inject("restore-candidate",0x2CA0,initial_w[0x2CA0:0x2CF0],sites["copy_complete"])
    inject("restore-table",0x9890,original_table,sites["copy_complete"])
    snap("restored",sites["copy_complete"])
    if mode=="save":
        for word in range(0x9FE,-1,-2):
            execute(0xFFFBFB)
            bus("sram","read",word,s[word]); bus("sram","read",word+1,s[word+1])
        checksum=inspect_ct_srm.slot_checksum(bytes(s[:0xA00])).to_bytes(2,"little")
        execute(0xFFFA58)
        for i,b in enumerate(checksum): bus("sram","write",0x1FF0+i,b)
        execute(0xFFFA5F)
        for i,b in enumerate(b"\x1b\xe4"): bus("sram","write",0x1FF8+i,b)
    execute(sites["terminal"])
    snap("terminal",sites["terminal"])
    records.append({"kind":"success","loops":10,"comparisons":10,"terminal_before_rtl":True,
                    "post_stop_execution_excluded":True})
    return records,snaps,contract


def check(f):
    return v.validate_records(*f,"2"*64,"3"*64)


class NativeLayoutTests(unittest.TestCase):
    def test_save_and_load_pair_censuses(self):
        for mode in ("save","load"):
            report=check(fixture(mode))
            self.assertEqual(report["native_copy_bytes"],0x834)
            self.assertFalse(report["complete_native_control_flow_proved"])
            self.assertFalse(report["caller_return_observed"])

    def test_frame_dma_and_live_clock_effects_do_not_fake_mvn_ownership(self):
        for mode in ("save","load"):
            check(fixture(mode,interrupts=True))

    def test_missing_save_source_read_rejected(self):
        f=fixture(); rows=f[0]
        index=next(i for i,r in enumerate(rows) if r["kind"]=="bus" and r["pc"]==0x7E9690 and r["op"]=="read")
        del rows[index]
        with self.assertRaises(c.ContractError): check(f)

    def test_missing_same_value_load_write_rejected(self):
        f=fixture("load"); rows,snaps,_=f
        self.assertEqual(snaps["prepared"][0][0x2400],snaps["entry"][1][0])
        # Exact transfer-pair census must reject even though replay cannot see
        # omission of this deliberately same-value first destination store.
        index=next(i for i,r in enumerate(rows) if r["kind"]=="bus" and r["pc"]==0x7E9690 and r["op"]=="write")
        rows.pop(index)
        with self.assertRaises(c.ContractError): check(f)

    def test_table_read_omission_rejected(self):
        f=fixture(); rows=f[0]
        del rows[next(i for i,r in enumerate(rows) if r["kind"]=="bus" and r["space"]=="table_rom")]
        with self.assertRaises(c.ContractError): check(f)

    def test_bus_pc_not_owner_claim_but_must_match_last_exec(self):
        f=fixture()
        next(r for r in f[0] if r["kind"]=="bus")["pc"]=0x123456
        with self.assertRaises(c.ContractError): check(f)

    def test_alias_mapping_not_claimed_offset(self):
        self.assertEqual(v.physical_offset(0x802830-0x2000,"wram"),0x830)
        self.assertEqual(v.physical_offset(0x7F1000,"wram"),0x11000)
        with self.assertRaises(c.ContractError): v.physical_offset(0x7E2830,"sram")
        f=fixture()
        next(r for r in f[0] if r["kind"]=="bus")["bus_address"]=0
        with self.assertRaises(c.ContractError): check(f)

    def test_early_or_duplicate_success_rejected(self):
        f=fixture(); f[0].insert(-1,copy.deepcopy(f[0][-1]))
        with self.assertRaises(c.ContractError): check(f)

    def test_marker_native_read_rejected(self):
        f=fixture(); rows=f[0]
        i=next(i for i,r in enumerate(rows) if r["kind"]=="exec")+1
        rows.insert(i,{"kind":"bus","space":"wram","op":"read","address":0x2830,
                       "bus_address":0x7E2830,"value":c.MARKER[0],"pc":c.MODES["save"]["entry"]})
        with self.assertRaises(c.ContractError): check(f)

    def test_marker_instruction_fetch_rejected(self):
        f=fixture(); row=next(r for r in f[0] if r["kind"]=="exec")
        row["pc"]=0x7E2830; row["cpu"].update(pc24=0x7E2830,k=0x7E,pc=0x2830)
        with self.assertRaises(c.ContractError): check(f)

    def test_other_slot_transient_write_and_restore_rejected(self):
        f=fixture(); rows,snaps,_=f
        index=next(i for i,r in enumerate(rows) if r["kind"]=="exec" and r["pc"]==0xFFFBFB)+1
        original=snaps["entry"][1][0xA00]
        for value in (original^1,original):
            rows.insert(index,{"kind":"bus","space":"sram","op":"write","address":0xA00,
                "bus_address":0x306A00,"value":value,"pc":0xFFFBFB}); index+=1
        with self.assertRaises(c.ContractError): check(f)

    def test_checksum_read_omission_rejected(self):
        f=fixture(); rows=f[0]
        del rows[next(i for i,r in enumerate(rows) if r["kind"]=="bus" and r["pc"]==0xFFFBFB)]
        with self.assertRaises(c.ContractError): check(f)

    def test_serialized_prefix_closed_after_copy_even_for_same_value_write(self):
        f=fixture(); rows,snaps,_=f
        index=next(i for i,r in enumerate(rows) if r["kind"]=="snapshot" and r["name"]=="restored")+1
        rows.insert(index,{"kind":"bus","space":"sram","op":"write","address":0,
            "bus_address":0x306000,"value":snaps["copy_complete"][1][0],
            "pc":c.MODES["save"]["copy_complete"]})
        with self.assertRaises(c.ContractError): check(f)

    def test_wrong_restore_or_extra_injection_rejected(self):
        f=fixture()
        next(r for r in f[0] if r.get("purpose")=="restore-natural")["hex"]=c.MARKER.hex()
        with self.assertRaises(c.ContractError): check(f)

    def test_invalid_load_checksum_rejected_before_ledger(self):
        f=fixture("load")
        w,s=f[1]["entry"]; damaged=bytearray(s); damaged[0]^=1
        f[1]["entry"]=(w,bytes(damaged)); f[2]["sram_sha256"]=c.sha256(damaged)
        with self.assertRaises(c.ContractError): check(f)

    def test_entry_exec_checkpoint_is_not_pre_jsl_checkpoint(self):
        entry=fixture()[2]; entry["checkpoint_pc"]=entry["entry_pc"]
        with self.assertRaises(c.ContractError): c.entry_contract(entry,"save")

    def test_duplicate_json_keys_refused(self):
        with self.assertRaises(c.ContractError): v.strict_json(b'{"mode":"save","mode":"load"}')

    def test_nonprivate_path_rejected(self):
        with self.assertRaises(c.ContractError): c.private_path(c.ROOT/"diagnostic.sfc")

    def test_emit_review_gate_rejects_before_build_or_write(self):
        with mock.patch.object(builder,"build_image") as build:
            with self.assertRaises(c.ContractError):
                builder.emit(b"",c.ROOT/"private/nonexistent-native-layout-test.sfc","0"*64)
            build.assert_not_called()

    @unittest.skipUnless(c.DEFAULT_ROM.exists(),"private canonical input unavailable")
    def test_canonical_in_memory_builder_and_complete_diff_guard(self):
        source=c.DEFAULT_ROM.read_bytes()
        target,report=builder.build_image(source,c.ROOT/"private/test_runs/save_layout_native_v1_test/diagnostic.sfc")
        self.assertEqual([i for i,(a,b) in enumerate(zip(source,target)) if a!=b],[0x3FFA50,0x3FFAE7])
        self.assertEqual(target[0xFFDC:0xFFE0],source[0xFFDC:0xFFE0])
        damaged=bytearray(target); damaged[0]^=1
        manifest=copy.deepcopy(report["write_intent_manifest"])
        manifest["target_sha256"]=c.sha256(damaged)
        with self.assertRaises(guard.WriteIntentError): guard.audit_images(manifest,source,bytes(damaged))
        self.assertEqual(guard.APPROVED_PRODUCTION_ALLOCATIONS,())
        self.assertEqual(guard.APPROVED_PRODUCTION_HOOKS,())


if __name__ == "__main__": unittest.main()
