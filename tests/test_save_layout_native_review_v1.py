from pathlib import Path
import sys
import unittest
import json
import copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_save_layout_native_review_v1 as review
import schala_save_layout as layout

class ReviewChecks(unittest.TestCase):
    def test_current_stream_is_ordered_and_physically_unique(self):
        self.assertEqual(review.check_stream()['unique_physical_bytes'],0x834)

    def test_same_size_reordered_compatibility_is_refused(self):
        r=list(layout.PROJECT_EPOCH_REGIONS);r[0],r[1]=r[1],r[0]
        with self.assertRaises(ValueError): review.check_stream(tuple(r))

    def test_low_bank_alias_overlap_is_refused(self):
        r=list(layout.PROJECT_EPOCH_REGIONS)
        # Move the sixteen-byte config descriptor onto the bank00 low-RAM
        # descriptor's physical bytes without changing banks or total size.
        i=next(i for i,x in enumerate(r) if x.label=='config')
        r[i]=layout.SaveRegion(0x100,0x7E,0x10,'alias')
        with self.assertRaisesRegex(ValueError,'overlap'): review.check_stream(tuple(r))

    def test_unsupported_bank_or_low_mirror_extent_is_refused(self):
        for r in (layout.SaveRegion(0x2000,0,1,'io'),layout.SaveRegion(0,0x40,1,'rom')):
            with self.assertRaises(ValueError): review.physical_stream((r,))

    def test_actual_chain_with_global_publication_contexts(self):
        report=review.audit()
        self.assertTrue(report['stream']['ordered_physical_equivalence'])
        for name,row in report['runs'].items():
            self.assertEqual(row['writes'],1 if '_save_' in name else 0)

    def test_wrong_slot_metadata_is_rejected_even_with_matching_terminal_snapshot(self):
        folder=review.c.ROOT/'private/test_runs/mesen2/save_layout_native_v1_save_run1'
        rows=[json.loads(line) for line in (folder/'trace.jsonl').read_text().splitlines()]
        snapshots={label:((folder/f'trace.{label}.wram.bin').read_bytes(),
                          (folder/f'trace.{label}.sram.bin').read_bytes())
                   for label in ('entry','terminal')}
        bad=copy.deepcopy(rows)
        next(r for r in bad if r['kind']=='bus' and r['space']=='sram' and r['op']=='write' and r['address']==0x1FE0)['value']=7
        sram=bytearray(snapshots['terminal'][1]);sram[0x1FE0]=7
        snapshots['terminal']=(snapshots['terminal'][0],bytes(sram))
        with self.assertRaisesRegex(ValueError,'global metadata value'):
            review.check_metadata(bad,snapshots,'save',0)

    def test_same_value_metadata_publication_at_wrong_context_is_rejected(self):
        folder=review.c.ROOT/'private/test_runs/mesen2/save_layout_native_v1_save_run1'
        rows=[json.loads(line) for line in (folder/'trace.jsonl').read_text().splitlines()]
        snapshots={label:((folder/f'trace.{label}.wram.bin').read_bytes(),
                          (folder/f'trace.{label}.sram.bin').read_bytes())
                   for label in ('entry','terminal')}
        next(r for r in rows if r['kind']=='bus' and r['space']=='sram' and r['op']=='write' and r['address']==0x1FE0)['pc']=0x7E9690
        with self.assertRaisesRegex(ValueError,'global metadata value'):
            review.check_metadata(rows,snapshots,'save',0)

if __name__=='__main__': unittest.main()
