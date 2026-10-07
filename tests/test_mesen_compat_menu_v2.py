"""Measurement-ledger rejection tests; no emulator launch or image emission."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import run_mesen_compat_menu_v2 as v2


def synthetic_ledger():
    """Independent four-byte write/read history, not a simulation of the game."""
    rows=[];snapshots={};memory=bytearray(0x20000);index=0
    def emit(row):
        row.update(n=len(rows)+1,poll=0);rows.append(row)
    def cpu(pc):
        return dict(a=0,x=0,y=0,d=0,dbr=0x7E,sp=0x0A79,ps=0x20,
                    k=pc>>16,pc=pc&65535,emulationMode=False,clock=2**33+len(rows))
    def snapshot(label):
        snapshots[label]=bytes(memory);emit(dict(kind='snapshot',label=label))
    def witness(pc):
        nonlocal index
        index+=1
        opcode,role,phase=v2.RESIDUE_SITES[pc]
        emit(dict(kind='residue-exec',site=pc,opcode=opcode,role=role,phase=phase,
                  cpu=cpu(pc),exec_index=index,
                  stack_word=int.from_bytes(memory[0xA78:0xA7A],'little'),
                  backup_word=int.from_bytes(memory[0x12158:0x1215A],'little')))
    def bus(pc,operation,address,value=None):
        nonlocal index
        index+=1
        if value is None:value=memory[address]
        emit(dict(kind='residue-bus',operation=operation,address=0x7E0000+address,
                  physical=address,value=value,preceding_exec_pc=pc,exec_index=index,
                  cpu_observed=cpu(pc)))
        if operation=='write':memory[address]=value
    emit(dict(kind='header'))
    snapshot('post_load');snapshot('prepared')
    witness(0xC28403);witness(0xC2821F)
    bus(0xC2821F,'write',0xA79,0x2C);bus(0xC2821F,'write',0xA78,0xCC)
    witness(0xC28220);witness(0xC28213)
    bus(0xC28213,'read',0xA78);bus(0xC28213,'read',0xA79)
    witness(0xC28214);snapshot('poll_150')
    witness(0xC00924)
    for a in (0xA78,0xA79):
        bus(0xC00924,'read',a);bus(0xC00924,'write',a+0x116E0,memory[a])
    witness(0xC00927)
    for label in ('poll_390','poll_630','poll_900','poll_1200'):snapshot(label)
    witness(0xC00911)
    for a in (0x12158,0x12159):
        bus(0xC00911,'read',a);bus(0xC00911,'write',a-0x116E0,memory[a])
    witness(0xC00914);snapshot('poll_1500');snapshot('cleanup')
    emit(dict(kind='success'))
    return rows,snapshots


class ResidueLedgerTests(unittest.TestCase):
    def test_complete_four_byte_history_reconciles_without_safety_claim(self):
        rows,snapshots=synthetic_ledger();result=v2.audit_residue(rows,snapshots)
        self.assertTrue(result['four_byte_values_reconciled'])
        self.assertEqual(result['bus_records'],12)
        self.assertFalse(result['instruction_ownership_proved'])
        self.assertFalse(result['semantic_read_safety_proved'])

    def test_unexpected_read_is_retained_as_a_boundary(self):
        rows,snapshots=synthetic_ledger()
        row=next(r for r in rows if r.get('operation')=='read')
        row['preceding_exec_pc']=0xC09A99
        result=v2.audit_residue(rows,snapshots)
        boundary=[r for r in result['access_contexts'] if r['outside_initial_context_hypothesis']]
        self.assertEqual(len(boundary),1)
        self.assertEqual(boundary[0]['preceding_exec_pc'],'C09A99')

    def test_missing_native_write_rejected_by_later_observation(self):
        rows,snapshots=synthetic_ledger()
        del rows[next(i for i,r in enumerate(rows) if r.get('operation')=='write')]
        for i,row in enumerate(rows,1):row['n']=i
        with self.assertRaisesRegex(ValueError,'readback|reconciliation'):
            v2.audit_residue(rows,snapshots)

    def test_wrong_read_value_rejected_even_if_snapshots_match(self):
        rows,snapshots=synthetic_ledger()
        next(r for r in rows if r.get('operation')=='read')['value']^=1
        with self.assertRaisesRegex(ValueError,'read/write reconciliation'):
            v2.audit_residue(rows,snapshots)

    def test_snapshot_only_mutation_is_not_accepted(self):
        rows,snapshots=synthetic_ledger()
        bad=bytearray(snapshots['poll_900']);bad[0x12159]^=1;snapshots['poll_900']=bytes(bad)
        with self.assertRaisesRegex(ValueError,'snapshot/write reconciliation'):
            v2.audit_residue(rows,snapshots)

    def test_missing_witness_is_not_complete_observation(self):
        rows,snapshots=synthetic_ledger()
        rows=[r for r in rows if r.get('site')!=0xC00914]
        for i,row in enumerate(rows,1):row['n']=i
        with self.assertRaisesRegex(ValueError,'witness coverage'):
            v2.audit_residue(rows,snapshots)

    def test_wrong_ply_opcode_pc_is_rejected(self):
        rows,snapshots=synthetic_ledger()
        next(r for r in rows if r.get('site')==0xC28213)['cpu']['pc']=0x8214
        with self.assertRaisesRegex(ValueError,'witness CPU PC'):
            v2.audit_residue(rows,snapshots)

    def test_record_hole_and_boolean_byte_refuse(self):
        for change in ('hole','bool'):
            rows,snapshots=synthetic_ledger()
            if change=='hole':rows[2]['n']=99
            else:next(r for r in rows if r['kind']=='residue-bus')['value']=True
            with self.subTest(change=change),self.assertRaises(ValueError):
                v2.audit_residue(rows,snapshots)

    def test_independent_wram_aliases_include_low_bank_mirrors(self):
        for bank in (0x00,0x3F,0x80,0xBF,0x7E):
            with self.subTest(bank=bank):
                self.assertEqual(v2.physical_wram((bank<<16)|0x0A78),0x0A78)
                rows,snapshots=synthetic_ledger()
                for row in rows:
                    if row['kind']=='residue-bus' and row['physical']==0x0A78:
                        row['address']=(bank<<16)|0x0A78
                self.assertTrue(v2.audit_residue(rows,snapshots)['four_byte_values_reconciled'])
        self.assertEqual(v2.physical_wram(0x7F2158),0x12158)
        for address in (0x002000,0x3F2158,0xBF2158,0x400A78,0xC00A78):
            with self.subTest(address=address),self.assertRaisesRegex(ValueError,'not a WRAM alias'):
                v2.physical_wram(address)

    def test_false_bus_bank_alias_rejects_matching_value_ledger(self):
        rows,snapshots=synthetic_ledger()
        row=next(r for r in rows if r['kind']=='residue-bus')
        row['address']=0x7F0000+row['physical']
        with self.assertRaisesRegex(ValueError,'bus/physical address mismatch'):
            v2.audit_residue(rows,snapshots)

    def test_unrelated_frozen_bus_projection_is_not_folded_into_residue(self):
        rows,snapshots=synthetic_ledger()
        rows.insert(3,dict(kind='bus',physical=0x2837,value=255,operation='read',poll=0))
        for i,row in enumerate(rows,1):row['n']=i
        self.assertEqual(v2.audit_residue(rows,snapshots)['bus_records'],12)

    def test_frozen_v1_bundle_drift_refuses(self):
        with mock.patch.object(v2.c,'bundle_identity',return_value={'sha256':'0'*64}):
            with self.assertRaisesRegex(ValueError,'frozen v1 builder bundle drift'):v2.bundle()


@unittest.skipUnless(v2.c.DEFAULT_ROM.exists(),'private canonical input unavailable')
class NativeSourceTests(unittest.TestCase):
    def test_native_spans_and_actual_ply_opcode_match_canonical_input(self):
        rom=v2.c.DEFAULT_ROM.read_bytes()
        contract=v2.native_source_contract(rom)
        self.assertEqual(rom[0x28213],0x7A)
        self.assertEqual(len(contract['spans']),11)
        self.assertEqual(contract['watched_physical_bytes'],[0xA78,0xA79,0x12158,0x12159])
        self.assertFalse((v2.ROOT/'private/test_runs/compat_menu_v2_test/never.sfc').exists())

    def test_native_source_mutation_refuses(self):
        rom=bytearray(v2.c.DEFAULT_ROM.read_bytes());rom[0x00924]^=1
        with self.assertRaisesRegex(ValueError,'canonical ROM'):v2.native_source_contract(bytes(rom))


if __name__=='__main__':unittest.main()
