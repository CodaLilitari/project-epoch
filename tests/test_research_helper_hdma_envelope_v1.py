"""Original finite arithmetic boundaries and refusal cases, without game data."""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import research_helper_hdma_envelope_v1 as a


def phase_fixture():
    hardware={'dmaController.hdmaChannels':255}
    hardware.update({'dmaController.'+p:False for p in
        ('dmaPending','dmaStartDelay','needToProcess','hdmaPending','hdmaInitPending')})
    entry={'kind':'resolver-entry','poll':378,'master_clock':123456,'scanline':119,'hclock':754,
        'dma_active_channels':[],'hdma_unfinished_enabled_channels':list(range(8)),'hardware':hardware}
    return {'schema':'project-epoch-package-resolver-phase-v2-accepted-pair',
        'full_trace_bytes_identical':True,'deadline_certified':False,
        'native_helper_executed':False,'production_approval':False,
        'runs':[{'projection':{'phases':[copy.deepcopy(entry)]}} for _ in range(2)]}


class Arithmetic(unittest.TestCase):
    def test_skipped_transfer_still_reads_counter(self):
        self.assertEqual(a.channel_cost(4,True,False,False,False,2,False,False),8)

    def test_counter_decrement_wrap_does_not_reload(self):
        self.assertEqual(a.channel_cost(4,True,False,False,True,0,False,False),8)

    def test_repeat_bit_does_not_avoid_low_seven_bit_reload(self):
        for counter in (1,129):
            self.assertEqual(a.channel_cost(4,True,False,True,True,counter,False,False),56)

    def test_last_zero_counter_uses_one_pointer_byte(self):
        self.assertEqual(a.channel_cost(0,True,False,False,True,1,True,True),16)
        self.assertEqual(a.channel_cost(0,True,False,False,True,1,True,False),24)

    def test_finished_channel_owes_no_channel_cost(self):
        self.assertEqual(a.channel_cost(4,True,True,True,True,1,False,False),0)

    def test_integer_bound_rounds_fraction_up(self):
        self.assertEqual(a.solve(1,1,4),4)
        self.assertEqual(a.solve(2,1,4),6)
        self.assertEqual(a.solve(17,0,4),17)

    def test_saturated_event_duty_has_no_finite_certificate(self):
        for cost in (4,5):
            with self.assertRaisesRegex(ValueError,'duty'):
                a.solve(1,cost,4)

    def test_late_phase_does_not_borrow_no_init_refinement(self):
        result=a.envelope(65046,261,1000)
        self.assertIsNone(result['phase_no_init'])
        self.assertEqual(result['phase_independent_at_most_one_init'],106689)

    def test_larger_helper_does_not_borrow_fixed_fixture_init_count(self):
        result=a.envelope(235926,119,754)
        self.assertIsNone(result['phase_no_init'])
        self.assertIsNone(result['phase_independent_at_most_one_init'])

    def test_invalid_numeric_inputs_refuse(self):
        for args in ((True,1,4),(-1,1,4),(0,True,4),(0,1,0),(0,1,4.0)):
            with self.subTest(args=args),self.assertRaises(ValueError):a.solve(*args)
        with self.assertRaises(ValueError):a.channel_cost(8,True,False,False,False,1,False,False)
        with self.assertRaises(ValueError):a.channel_cost(1,True,False,False,False,256,False,False)
        with self.assertRaises(ValueError):a.channel_cost(1,1,False,False,False,1,False,False)


class SourceAndObservationGuards(unittest.TestCase):
    def test_pending_dma_and_mismatched_pair_refuse(self):
        good=phase_fixture()
        self.assertFalse(a.phase_observation(good)['transfer_modes_or_table_payloads_inferred'])
        for change in ('pending','active','pair','deadline','phase'):
            bad=copy.deepcopy(good)
            if change=='deadline':bad['deadline_certified']=True
            else:
                row=bad['runs'][0]['projection']['phases'][0]
                if change=='pending':row['hardware']['dmaController.hdmaPending']=True
                if change=='active':row['dma_active_channels']=[0]
                if change=='pair':row['master_clock']+=1
                if change=='phase':row['scanline']=261
                if change!='pair':bad['runs'][1]=copy.deepcopy(bad['runs'][0])
            with self.subTest(change=change),self.assertRaises(ValueError):a.phase_observation(bad)

    def test_same_size_source_mutation_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=root/'original.txt';path.write_bytes(b'abc')
            with mock.patch.object(a,'ROOT',root):
                self.assertEqual(a.identity('original.txt',3,a.sha(b'abc'))['size_bytes'],3)
                path.write_bytes(b'abd')
                with self.assertRaisesRegex(ValueError,'hash drift'):
                    a.identity('original.txt',3,a.sha(b'abc'))

    def test_import_is_pure_and_serialization_is_lf(self):
        spec=importlib.util.spec_from_file_location('hdma_pure_import_fixture',a.__file__)
        module=importlib.util.module_from_spec(spec)
        with mock.patch.object(Path,'read_bytes',side_effect=AssertionError('unexpected file read')):
            spec.loader.exec_module(module)
        raw=module.serial({'original':True})
        self.assertNotIn(b'\r',raw)
        self.assertTrue(raw.endswith(b'\n'))
        self.assertFalse(raw.endswith(b'\n\n'))


if __name__=='__main__':
    unittest.main()
