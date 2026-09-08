"""Original host rejection tests for the corrected observable phase contract."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import audit_mesen_nmi_phase_contract_v2 as tool


def specimen():
    before={'latch':False,'peek':0,'clock':10,'scanline':224}
    after={'latch':True,'peek':128,'clock':20,'scanline':225}
    timing={k:0 for k in tool.TIMING};timing.update({'memoryManager.masterClock':30,'ppu.scanline':226})
    return {'name':'original host specimen, not runtime evidence',
            'preparation':{'latch_rise':{'before':before,'after':after}},
            'events':[{'kind':'fixture-baseline','flags':dict.fromkeys(tool.FLAGS,False),'timing':timing}]}


class PhaseContractTests(unittest.TestCase):
    def test_original_specimen(self):
        self.assertEqual(tool.phase_witness(specimen())['baseline_timing']['ppu.scanline'],226)
    def test_hidden_key_never_required(self):
        self.assertNotIn('ppu.nmiScanline',tool.TIMING|tool.FLAGS)
    def test_missing_public_key_refuses(self):
        r=specimen();del r['events'][0]['timing']['ppu.scanline']
        with self.assertRaises(ValueError):tool.phase_witness(r)
    def test_hidden_key_substitution_refuses(self):
        r=specimen();t=r['events'][0]['timing'];t['ppu.nmiScanline']=t.pop('ppu.scanline')
        with self.assertRaises(ValueError):tool.phase_witness(r)
    def test_no_false_sample_refuses(self):
        r=specimen();r['preparation']['latch_rise']['before']['latch']=True
        with self.assertRaises(ValueError):tool.phase_witness(r)
    def test_peek_disagreement_refuses(self):
        r=specimen();r['preparation']['latch_rise']['after']['peek']=0
        with self.assertRaises(ValueError):tool.phase_witness(r)
    def test_reversed_sample_clock_refuses(self):
        r=specimen();r['preparation']['latch_rise']['after']['clock']=9
        with self.assertRaises(ValueError):tool.phase_witness(r)
    def test_leading_edge_baseline_refuses(self):
        r=specimen();r['events'][0]['timing']['ppu.scanline']=225
        with self.assertRaises(ValueError):tool.phase_witness(r)
    def test_span_uses_exact_line_endings(self):
        raw=b'a\nline2\nend\n';digest=hashlib.sha256(b'line2\n').hexdigest()
        self.assertEqual(tool.source_span(raw,2,2,digest)['bytes'],6)
        with self.assertRaises(ValueError):tool.source_span(raw.replace(b'\n',b'\r\n'),2,2,digest)
    def test_invalid_span_refuses(self):
        with self.assertRaises(ValueError):tool.source_span(b'a\n',0,1,'x')


if __name__=='__main__':unittest.main()
