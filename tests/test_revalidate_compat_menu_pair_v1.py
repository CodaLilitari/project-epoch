"""Read-only paired probe tests; adversaries mutate captured fixtures in memory."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import revalidate_compat_menu_pair_v1 as audit


class MetadataTests(unittest.TestCase):
    def test_duplicate_json_and_path_escape_refused(self):
        with self.assertRaises(audit.PairError): audit.decode(b'{"a":1,"a":2}')
        with self.assertRaises(audit.PairError): audit.path('../outside')

    def test_reference_drift_refused_before_artifact_access(self):
        fake=mock.Mock();fake.read_bytes.return_value=b'{}'
        with mock.patch.object(audit,'REFERENCE',fake), mock.patch.object(audit,'path') as access:
            with self.assertRaisesRegex(audit.PairError,'reference identity drift'): audit.audit()
            access.assert_not_called()

    def test_physical_aliases_do_not_accept_unrelated_offset(self):
        self.assertEqual(audit.physical(0x7E2830),('wram',0x2830))
        self.assertEqual(audit.physical(0x800A78),('wram',0xA78))
        self.assertEqual(audit.physical(0x306430),('sram',0x430))
        with self.assertRaises(audit.PairError): audit.physical(0x002830)


@unittest.skipUnless((audit.ROOT/audit.BASE/audit.RUNS['relocated'][0]/'events.jsonl').exists(),
                     'exact private accepted probes unavailable')
class PrivatePairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures={}
        for mode in audit.RUNS:
            d=audit.ROOT/audit.BASE/audit.RUNS[mode][0]
            rows=[audit.decode(line) for line in (d/'events.jsonl').read_bytes().splitlines()]
            snapshots={label:((d/(label+'.wram.bin')).read_bytes(),(d/(label+'.sram.bin')).read_bytes())
                       for label in audit.LABELS}
            cls.fixtures[mode]=(rows,snapshots,(d/'input.sram').read_bytes())

    def fixture(self,mode='relocated'):
        return deepcopy(self.fixtures[mode])

    @staticmethod
    def change_snapshot(snapshots,label,offset):
        raw,sram=snapshots[label];raw=bytearray(raw);raw[offset]^=1;snapshots[label]=(bytes(raw),sram)

    def test_complete_four_run_audit_preserves_presentation_exception(self):
        result=audit.audit()
        self.assertEqual(result['artifacts'],155)
        self.assertEqual(result['declared_byte_equality_groups'],72)
        self.assertEqual(result['matched_bus_events'],239)
        self.assertEqual(result['matched_snapshot_cpu_tuples'],9)
        self.assertEqual(result['same_value_original_record_writes_per_run'],104)
        self.assertEqual(result['same_value_roster_adjacent_writes_per_run'],1)
        self.assertFalse(result['presentation_exception']['byte_equal'])
        self.assertTrue(result['pointer_residue']['not_full_wram_equivalence'])
        self.assertEqual(result['observed_consumers']['C2830E'],0)
        self.assertFalse(result['scope']['sram_reads_observed'])
        self.assertFalse(result['native_execution_performed'])
        self.assertFalse(result['rom_emitted'])

    def test_preparation_extra_write_refused(self):
        rows,snaps,sram=self.fixture();self.change_snapshot(snaps,'prepared',0x3000)
        with self.assertRaisesRegex(audit.PairError,'complete preparation footprint'):
            audit.validate_observation(rows,snaps,sram,'relocated')

    def test_cleanup_extra_write_refused(self):
        rows,snaps,sram=self.fixture();self.change_snapshot(snaps,'cleanup',0x3000)
        with self.assertRaisesRegex(audit.PairError,'complete cleanup footprint'):
            audit.validate_observation(rows,snaps,sram,'relocated')

    def test_marker_changed_in_middle_snapshot_refused(self):
        rows,snaps,sram=self.fixture();self.change_snapshot(snaps,'poll_630',0x2830)
        with self.assertRaisesRegex(audit.PairError,'marker snapshot changed'):
            audit.validate_observation(rows,snaps,sram,'relocated')

    def test_marker_guard_and_sram_bus_events_refused(self):
        for address,physical,reason in ((0x7E2830,0x2830,'opaque marker bus access'),
                                         (0x7E2C9C,0x2C9C,'guard bus access'),
                                         (0x306430,0x430,'observed SRAM activity')):
            with self.subTest(address=address):
                rows,snaps,sram=self.fixture();row=next(r for r in rows if r['kind']=='bus')
                row.update(address=address,physical=physical)
                with self.assertRaisesRegex(audit.PairError,reason):
                    audit.validate_observation(rows,snaps,sram,'relocated')

    def test_incorrect_physical_mapping_refused(self):
        rows,snaps,sram=self.fixture();row=next(r for r in rows if r['kind']=='bus')
        row['physical']^=1
        with self.assertRaisesRegex(audit.PairError,'physical mapping'):
            audit.validate_observation(rows,snaps,sram,'relocated')

    def test_missing_same_value_original_record_write_refused(self):
        rows,snaps,sram=self.fixture()
        row=next(r for r in rows if r['kind']=='bus' and 0x2600<=r['physical']<0x2830)
        self.assertEqual(row['value'],snaps['prepared'][0][row['physical']])
        rows.remove(row)
        for n,row in enumerate(rows,1): row['n']=n
        with self.assertRaisesRegex(audit.PairError,'exact record count'):
            audit.validate_observation(rows,snaps,sram,'relocated')

    def test_bus_pair_clock_difference_refused(self):
        c,cs,ss=self.fixture('control');r,rs,_=self.fixture()
        co=audit.validate_observation(c,cs,ss,'control');ro=audit.validate_observation(r,rs,ss,'relocated')
        event=list(ro['bus'][0]);event[-1]+=1;ro['bus'][0]=tuple(event)
        with self.assertRaisesRegex(audit.PairError,'inverse-relocated bus equivalence'):
            audit.compare_modes(cs,rs,co,ro)

    def test_unenumerated_wram_difference_refused(self):
        c,cs,ss=self.fixture('control');r,rs,_=self.fixture()
        co=audit.validate_observation(c,cs,ss,'control');ro=audit.validate_observation(r,rs,ss,'relocated')
        self.change_snapshot(rs,'poll_630',0x3000)
        with self.assertRaisesRegex(audit.PairError,'unenumerated full-WRAM difference'):
            audit.compare_modes(cs,rs,co,ro)


if __name__=='__main__': unittest.main()
