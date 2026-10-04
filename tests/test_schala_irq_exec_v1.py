"""Order and refusal tests, independent of the emitted metadata."""
import sys
from dataclasses import replace
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from schala_irq_transition_core_v1 import IrqState
from schala_irq_exec_v1 import (ExecModel, NestedEvent, Premises,
    CONDITIONAL_PREMISES, game_deadline)


def state(**kw):
    base = dict(h_counter=186, v_counter=119, h_timer=0, v_timer=211,
                need_irq=0, irq_flag=False, irq_level=False, ppu_irq_source=False,
                h_enabled=False, v_enabled=True, irq_enabled_cache=True,
                nmi_enabled=False, nmi_flag=False, auto_joy_enabled=False)
    base.update(kw)
    return IrqState(**base)


def model(**kw):
    base = dict(state=state(), clock=2155080050, line=119, hclock=754,
                premises=CONDITIONAL_PREMISES)
    base.update(kw)
    return ExecModel(**base)


class ExecOrder(unittest.TestCase):
    def test_v_only_exact_source_request(self):
        m = model()
        r = m.run_until(lambda x: x.state.ppu_irq_source)
        self.assertEqual([(x['field'], x['offset']) for x in r['changes']], [
            ('need_irq',124740), ('irq_level',124740), ('need_irq',124744),
            ('irq_flag',124744), ('need_irq',124748), ('ppu_irq_source',124748)])
        self.assertEqual((r['line'],r['hclock']), (211,14))
        self.assertTrue(r['hdma_request_pending'])
        self.assertFalse(r['game_request_deadline_certified'])
        self.assertIsNone(r['handler_entry_clock'])

    def test_short_line_comparison_is_distinct(self):
        r = model(line_clocks=1360).run_until(lambda x: x.state.ppu_irq_source)
        self.assertEqual([x['offset'] for x in r['changes'] if x['field'] in
            ('irq_level','irq_flag','ppu_irq_source')], [124372,124376,124380])
        self.assertEqual(r['line_model'], 'shortened-1360-comparison')

    def test_refresh_omits_538_and_duplicates_578(self):
        m = model(state=state(h_counter=0), clock=10, hclock=10,
                  next_event='refresh', next_event_h=538)
        r = m.run_until(lambda x: x.hclock >= 754, max_clocks=800)
        hs = [t[2] for t in m.ticks]
        self.assertNotIn(538, hs)
        self.assertEqual(hs.count(578),2)
        self.assertEqual((r['counter_h'],r['irq_counter_calls']), (186,186))
        self.assertEqual(r['distinct_tick_clocks'],185)

    def test_all_four_even_refresh_phases(self):
        for h in (532,534,536,538):
            with self.subTest(h=h):
                m=model(state=state(h_counter=0),clock=10+(538-h),hclock=10,next_event='refresh',next_event_h=h)
                self.assertEqual(m.run_until(lambda x:x.hclock>=754,max_clocks=800)['counter_h'],186)

    def test_refresh_can_set_flag_and_source_at_same_clock(self):
        m = model(state=state(h_counter=131,h_timer=140,h_enabled=True,v_enabled=False),
                  clock=534,hclock=534,next_event='refresh',next_event_h=538)
        r=m.run_until(lambda x:x.state.ppu_irq_source,max_clocks=80)
        selected={x['field']:x['clock'] for x in r['changes'] if x['after'] is True}
        self.assertEqual(selected, {'irq_level':574,'irq_flag':578,'ppu_irq_source':578})

    def test_counter_updates_before_match_and_after_pending(self):
        m=model(state=state(v_counter=210),clock=0,line=211,hclock=0,
                next_event='refresh',next_event_h=538)
        m.run_until(lambda x:x.hclock>=6,max_clocks=10)
        self.assertEqual(m.state.need_irq,2)
        self.assertFalse(m.state.irq_flag)
        self.assertFalse(m.state.ppu_irq_source)

    def test_pending_one_false_clears_next_tick(self):
        m=model(state=state(need_irq=1,ppu_irq_source=True))
        m.exec();m.exec()
        self.assertFalse(m.state.ppu_irq_source)
        self.assertFalse(m.state.irq_flag)

    def test_pending_two_false_has_early_request(self):
        r=model(state=state(need_irq=2)).run_until(lambda x:x.state.ppu_irq_source,max_clocks=10)
        self.assertEqual(r['clock']-2155080050,8)

    def test_explicit_nested_boundary_duplicates_h6(self):
        m=model(state=state(h_counter=336,v_counter=210),clock=1362,line=210,hclock=1362,
                next_event='end',next_event_h=1364,callbacks=(NestedEvent(211,0,6),))
        r=m.run_until(lambda x:x.line==211 and x.hclock>=6,max_clocks=20)
        self.assertEqual([t[2] for t in m.ticks], [2,6,6])
        self.assertEqual(m.state.v_counter,212)
        self.assertTrue(r['scripted_adversarial_callbacks'])
        self.assertFalse(r['game_request_deadline_certified'])

    def test_unknown_each_callback_or_write_premise_refuses(self):
        for name in vars(CONDITIONAL_PREMISES):
            for value in (False,None,1,'closed'):
                with self.subTest(name=name,value=value), self.assertRaises(ValueError):
                    model(premises=replace(CONDITIONAL_PREMISES,**{name:value}))

    def test_reaching_vblank_refuses(self):
        m=model(clock=1362,line=224,hclock=1362,next_event='end',next_event_h=1364)
        with self.assertRaisesRegex(ValueError,'VBlank'):m.exec()
        with self.assertRaisesRegex(ValueError,'poisoned'):m.exec()
        with self.assertRaisesRegex(ValueError,'poisoned'):m.summary()

    def test_duration_is_enforced_inside_refresh(self):
        m=model(clock=536,hclock=536,next_event='refresh',next_event_h=538)
        with self.assertRaisesRegex(ValueError,'nested duration'):
            m.run_until(lambda x:x.hclock>=540,max_clocks=2)
        self.assertEqual(m.clock,538)
        with self.assertRaisesRegex(ValueError,'poisoned'):m.exec()

    def test_uint64_wrap_refuses(self):
        with self.assertRaises(ValueError):model(clock=2**64)
        m=model(clock=2**64-2)
        with self.assertRaisesRegex(ValueError,'wrap'):m.exec()

    def test_synthetic_event_cannot_take_source_label(self):
        for args in ({'next_event':'hdma','next_event_h':756},
                     {'next_event':'refresh','next_event_h':756},
                     {'next_event':'end','next_event_h':1362},
                     {'clock':538,'hclock':538,'next_event':'hdma','next_event_h':1104}):
            with self.subTest(args=args), self.assertRaises(ValueError):model(**args)

    def test_unreached_script_refuses(self):
        m=model(callbacks=(NestedEvent(211,0,2),))
        with self.assertRaisesRegex(ValueError,'unreached'):m.run_until(lambda x:True)

    def test_no_caller_claim_grants_game_deadline(self):
        for args in ({},{'callback_closure':True,'reset_write_closure':True,'cpu_schedule':True}):
            with self.assertRaisesRegex(ValueError,'no game'):game_deadline(**args)

    def test_bad_clock_event_and_callback_refuse(self):
        for args in ({'clock':True},{'clock':1},{'hclock':-2},{'line':0},{'line_clocks':1362},
                     {'next_event':'unknown'},{'next_event_h':754},{'hdma_channels':True},
                     {'callbacks':[]},{'premises':True}):
            with self.subTest(args=args),self.assertRaises(ValueError):model(**args)
        for args in ((0,0,2),(1,1,2),(1,0,0),(1,0,82)):
            with self.assertRaises(ValueError):NestedEvent(*args)


if __name__ == '__main__':
    unittest.main()
