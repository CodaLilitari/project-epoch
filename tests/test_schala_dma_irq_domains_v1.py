"""Adversarial bounds and independent imperative DMA/HDMA call projection."""

from dataclasses import fields, replace
from itertools import product
import random
import unittest

from tools.schala_dma_irq_domains_v1 import (
    AddressDomain, BusAccess, ChannelConfig, DomainPremises, MAX_SERVICES,
    RefusedPremise, b_address, circular_domain, copy_bus_accesses,
    dispatch_route, dma_domains, hdma_domains,
)


P = DomainPremises(True, True, True, True, True)


def config(**changes):
    return replace(ChannelConfig(
        source_bank=0x00, source_address=0x4200, transfer_size=1,
        dest_address=0x00, transfer_mode=0, invert_direction=False,
        decrement=False, fixed_transfer=False, dma_active=True,
        hdma_bank=0x80, hdma_table_address=0x4200, hdma_line_counter=1,
        do_transfer=True, hdma_finished=False, hdma_indirect=False,
        hdma_enabled=True,
    ), **changes)


def imperative_hdma(channel, services, values, initialize, last_channel):
    """Independent mutable translation; no production domain helpers reused.

    Table values are chosen independently per read, including discarded reads.
    The call projection deliberately includes WRAM/$2180 candidates (matching
    the public domain overapproximation), with precise read/write direction.
    """
    counts = [1, 2, 2, 4, 4, 4, 2, 4]
    patterns = ["0000", "0101", "0000", "0011", "0123", "0101", "0000", "0011"]
    calls = []
    table = channel.hdma_table_address
    indirect = channel.transfer_size
    line = channel.hdma_line_counter
    finished = channel.hdma_finished
    transfer = channel.do_transfer

    def read_table(pointer):
        calls.append(BusAccess("A", "read", channel.source_bank * 65536 + pointer))
        return next(values)

    if not channel.hdma_enabled:
        return calls
    if initialize:
        table = channel.source_address
        line = read_table(table)
        table = (table + 1) % 65536
        finished = line == 0
        transfer = True
        if channel.hdma_indirect:
            low = read_table(table)
            table = (table + 1) % 65536
            if finished:
                indirect = low * 256
            else:
                high = read_table(table)
                table = (table + 1) % 65536
                indirect = high * 256 + low
    for _ in range(services):
        if finished:
            continue
        if transfer:
            for off in patterns[channel.transfer_mode][:counts[channel.transfer_mode]]:
                bank = channel.hdma_bank if channel.hdma_indirect else channel.source_bank
                pointer = indirect if channel.hdma_indirect else table
                addr_a = bank * 65536 + pointer
                addr_b = 0x2100 | (channel.dest_address + int(off))
                if channel.invert_direction:
                    calls += [BusAccess("B", "read", addr_b), BusAccess("A", "write", addr_a)]
                else:
                    calls += [BusAccess("A", "read", addr_a), BusAccess("B", "write", addr_b)]
                if channel.hdma_indirect:
                    indirect = (indirect + 1) % 65536
                else:
                    table = (table + 1) % 65536
        line = (line - 1) % 256
        transfer = bool(line & 128)
        counter = read_table(table)
        if line % 128 == 0:
            line = counter
            table = (table + 1) % 65536
            if channel.hdma_indirect:
                if line == 0 and last_channel:
                    high = read_table(table)
                    table = (table + 1) % 65536
                    indirect = high * 256
                else:
                    low = read_table(table)
                    table = (table + 1) % 65536
                    high = read_table(table)
                    table = (table + 1) % 65536
                    indirect = high * 256 + low
            finished = line == 0
            transfer = True
    return calls


class DomainArithmeticTests(unittest.TestCase):
    def test_promoted_b_addition_equivalence_over_complete_domain(self):
        for dest, offset in product(range(256), range(4)):
            actual = b_address(dest, offset)
            self.assertEqual(actual, 0x2100 | ((dest + offset) & 255))
            self.assertTrue(0x2100 <= actual <= 0x21FF)
        self.assertEqual(b_address(255, 1), 0x2100)
        self.assertEqual(b_address(255, 3), 0x2102)

    def test_circular_domains_match_independent_modular_sets(self):
        for start, count, step in product((0, 1, 0x4200, 65533, 65535),
                                          (0, 1, 2, 5, 65535, 65536), (-1, 0, 1)):
            expected = {(start + i * step) % 65536 for i in range(count)}
            domain = circular_domain(0xBF, start, count, step)
            observed = {n for lo, hi in domain.intervals for n in range(lo, hi + 1)}
            self.assertEqual(observed, expected)
            self.assertEqual(domain.cardinality, len(expected))
            self.assertFalse(domain.contains(0xC00000 | start))

    def test_large_extent_saturates_one_bank(self):
        domain = circular_domain(0x7E, 65000, 200000)
        self.assertEqual(domain.intervals, ((0, 65535),))
        self.assertTrue(domain.contains(0x7E4211))
        self.assertFalse(domain.contains(0x7F4211))

    def test_domains_require_canonical_interval_form(self):
        for intervals in ([(0, 1)], ((2, 1),), ((0, 1), (1, 2)),
                          ((0, 1), (2, 3)), ((True, 3),), ((0, 65536),)):
            with self.assertRaises(ValueError):
                AddressDomain(0, intervals)


class CopyAndDispatchTests(unittest.TestCase):
    def test_copy_direction_and_wram_port_exception(self):
        self.assertEqual(copy_bus_accesses(0x004211, 0x2140, False, a_is_wram=False), (
            BusAccess("A", "read", 0x004211), BusAccess("B", "write", 0x2140)))
        self.assertEqual(copy_bus_accesses(0x804207, 0x2140, True, a_is_wram=False), (
            BusAccess("B", "read", 0x2140), BusAccess("A", "write", 0x804207)))
        self.assertEqual(copy_bus_accesses(0x7E0000, 0x2180, False, a_is_wram=True), ())
        self.assertEqual(copy_bus_accesses(0x7E0000, 0x2180, True, a_is_wram=True), (
            BusAccess("A", "write", 0x7E0000),))
        self.assertEqual(len(copy_bus_accesses(0x004211, 0x2180, False, a_is_wram=False)), 2)

    def test_irq_addresses_route_internal_under_explicit_map(self):
        for bank, reg, operation in product((0, 0x3F, 0x80, 0xBF),
                                             (0x4200, 0x4207, 0x420A, 0x4211),
                                             ("read", "write")):
            self.assertEqual(dispatch_route(bank * 65536 + reg, "A", operation, P),
                             "internal-register-handler")

    def test_dma_register_block_does_not_cover_timeup_or_timer(self):
        for reg in (0x420B, 0x420C, 0x4300, 0x437F):
            self.assertEqual(dispatch_route(reg, "A", "read", P), "dma-register-open-bus")
            self.assertEqual(dispatch_route(reg, "A", "write", P), "dma-register-write-suppressed")
        self.assertEqual(dispatch_route(0x4380, "A", "read", P), "dma-controller-handler")
        self.assertEqual(dispatch_route(0x4016, "A", "write", P), "control-handler")
        self.assertEqual(dispatch_route(0x4017, "A", "read", P), "control-handler")
        self.assertEqual(dispatch_route(0x4017, "A", "write", P), "internal-register-handler")

    def test_base_alias_exclusion_does_not_assign_other_handler(self):
        for bank in (0x40, 0x7D, 0x7E, 0x7F, 0xC0, 0xFF):
            self.assertEqual(dispatch_route(bank * 65536 + 0x4211, "A", "read", P),
                             "outside-assumed-register-a-map")


class ManualDmaTests(unittest.TestCase):
    def test_complete_manual_sequences_are_contained(self):
        # Independent transfer patterns and modular pointer arithmetic.
        patterns = ((0,), (0, 1), (0,), (0, 0, 1, 1),
                    (0, 1, 2, 3), (0, 1), (0,), (0, 0, 1, 1))
        for mode, reverse, step in product(range(8), (False, True), (-1, 0, 1)):
            channel = config(transfer_mode=mode, invert_direction=reverse,
                             decrement=step < 0, fixed_transfer=step == 0,
                             source_address=65534, transfer_size=9, dest_address=255)
            report = dma_domains(channel, P)
            for i in range(9):
                addr_a = (65534 + step * i) % 65536
                addr_b = 0x2100 | (255 + patterns[mode][i % len(patterns[mode])])
                self.assertTrue(report.contains(BusAccess("A", "write" if reverse else "read", addr_a)))
                self.assertTrue(report.contains(BusAccess("B", "read" if reverse else "write", addr_b)))

    def test_zero_size_is_full_bank_except_fixed_pointer(self):
        for decrement in (False, True):
            report = dma_domains(config(transfer_size=0, decrement=decrement), P)
            self.assertEqual(report.domains[0].addresses.cardinality, 65536)
        fixed = dma_domains(config(transfer_size=0, fixed_transfer=True), P)
        self.assertEqual(fixed.domains[0].addresses.intervals, ((0x4200, 0x4200),))

    def test_forward_timeup_and_reverse_timer_candidates_differ(self):
        forward = dma_domains(config(source_address=0x4211), P).irq_candidates()
        self.assertEqual([x["register"] for x in forward["timeup_reads"]], [0x4211])
        self.assertEqual(forward["irq_register_writes"], [])
        reverse = dma_domains(config(source_address=0x4200, transfer_size=11,
                                     invert_direction=True), P).irq_candidates()
        self.assertEqual(reverse["timeup_reads"], [])
        self.assertEqual([x["register"] for x in reverse["irq_register_writes"]],
                         [0x4200, 0x4207, 0x4208, 0x4209, 0x420A])

    def test_no_active_manual_call_has_empty_domain(self):
        self.assertEqual(dma_domains(config(dma_active=False), P).domains, ())


class HdmaTests(unittest.TestCase):
    def test_always_table_read_even_without_transfer_or_reload(self):
        channel = config(do_transfer=False, hdma_line_counter=5, hdma_table_address=0x4211)
        report = hdma_domains(channel, 1, P)
        calls = imperative_hdma(channel, 1, iter([0]), False, True)
        self.assertEqual(calls, [BusAccess("A", "read", 0x4211)])
        self.assertTrue(report.contains(calls[0]))
        self.assertEqual([x["role"] for x in report.irq_candidates()["timeup_reads"]],
                         ["hdma-table-and-indirect-address"])
        self.assertEqual(len(report.domains), 1)

    def test_reverse_payload_keeps_table_and_indirect_pointer_reads(self):
        channel = config(invert_direction=True, hdma_indirect=True, do_transfer=False,
                         hdma_table_address=0x4211, hdma_line_counter=1)
        report = hdma_domains(channel, 1, P)
        self.assertEqual([x["address"] for x in report.irq_candidates()["timeup_reads"]], [0x4211])
        calls = imperative_hdma(channel, 1, iter([1, 0x00, 0x42]), False, False)
        self.assertEqual([x.address for x in calls], [0x4211, 0x4212, 0x4213])
        self.assertTrue(all(report.contains(x) for x in calls))

    def test_indirect_current_pointer_is_bounded_but_reload_future_is_full_bank(self):
        channel = config(hdma_indirect=True, hdma_bank=0x80, transfer_size=0xFFFF, transfer_mode=4)
        first = hdma_domains(channel, 1, P)
        domain = next(x.addresses for x in first.domains if x.role == "hdma-payload")
        self.assertEqual(domain.intervals, ((0, 2), (65535, 65535)))
        future = hdma_domains(channel, 2, P)
        domain = next(x.addresses for x in future.domains if x.role == "hdma-payload")
        self.assertEqual(domain.intervals, ((0, 65535),))

    def test_initialization_and_last_channel_zero_reload_oddities_covered(self):
        for initialize in (False, True):
            channel = config(hdma_indirect=True, do_transfer=False, hdma_line_counter=1,
                             source_address=65535, hdma_table_address=65535)
            calls = imperative_hdma(channel, 1, iter([0, 0x42, 0, 0]), initialize, True)
            self.assertEqual([x.address for x in calls], [65535, 0])
            report = hdma_domains(channel, 1, P, include_init=initialize)
            self.assertTrue(all(report.contains(x) for x in calls))
        calls = imperative_hdma(channel, 1, iter([0, 0x12, 0x34]), False, False)
        self.assertEqual([x.address for x in calls], [65535, 0, 1])

    def test_direct_payload_ignores_manual_fixed_and_decrement_flags(self):
        channel = config(source_bank=0x7F, hdma_table_address=65535, transfer_mode=4,
                         fixed_transfer=True, decrement=True)
        calls = imperative_hdma(channel, 1, iter([0]), False, True)
        self.assertEqual([x.address for x in calls if x.bus == "A"],
                         [0x7FFFFF, 0x7F0000, 0x7F0001, 0x7F0002, 0x7F0003])
        self.assertTrue(all(hdma_domains(channel, 1, P).contains(x) for x in calls))

    def test_disabled_finished_and_init_reset_distinctions(self):
        self.assertEqual(hdma_domains(config(hdma_enabled=False), 2, P, include_init=True).domains, ())
        self.assertEqual(hdma_domains(config(hdma_finished=True), 2, P).domains, ())
        self.assertTrue(hdma_domains(config(hdma_finished=True), 2, P, include_init=True).domains)
        self.assertEqual(hdma_domains(config(), 0, P).domains, ())
        initialized = hdma_domains(config(), 0, P, include_init=True)
        self.assertEqual(len(initialized.domains), 1)
        self.assertEqual(initialized.domains[0].addresses.intervals, ((0x4200, 0x4200),))

    def test_all_modes_directions_wraps_and_hostile_table_reads(self):
        generator = random.Random(0xD4A2026)
        cases = 0
        for mode, reverse, indirect, initialize, initial_transfer, counter, last_channel in product(
            range(8), (False, True), (False, True), (False, True), (False, True),
            (0, 1, 2, 0x7F, 0x80, 0x81, 0xFF), (False, True)
        ):
            start = generator.choice([0, 0x4200, 0x4210, 65533, 65535])
            channel = config(transfer_mode=mode, invert_direction=reverse,
                             hdma_indirect=indirect, source_address=start,
                             hdma_table_address=start, transfer_size=generator.randrange(65536),
                             do_transfer=initial_transfer, hdma_line_counter=counter,
                             dest_address=generator.choice([0, 0x80, 0xFE, 0xFF]))
            # Bias to reload, repeat, terminate and wrap boundaries, interleaved
            # with arbitrary pointer bytes. Content may change on every read.
            choices = [generator.choice([0, 1, 2, 0x80, 0x81, 0xFF, generator.randrange(256)])
                       for _ in range(64)]
            report = hdma_domains(channel, 6, P, include_init=initialize)
            calls = imperative_hdma(channel, 6, iter(choices), initialize, last_channel)
            self.assertTrue(all(report.contains(x) for x in calls), (channel, calls, report))
            cases += 1
        self.assertEqual(cases, 1792)

    def test_large_service_count_saturates_without_bank_carry(self):
        report = hdma_domains(config(transfer_mode=4, source_bank=0x3F), MAX_SERVICES, P)
        self.assertTrue(all(x.addresses.bank == (0 if x.bus == "B" else 0x3F) for x in report.domains))
        self.assertEqual(report.domains[0].addresses.cardinality, 65536)

    def test_reports_do_not_promote_hypotheses_or_domains(self):
        payload = hdma_domains(config(), 1, P).to_dict()
        for key in ("hypotheses_verified", "mapping_identity_proved", "handler_side_effects_closed",
                    "callback_closure_proved", "game_duration_bound", "runtime_observation",
                    "production_approval"):
            self.assertIs(payload[key], False)


class RefusalTests(unittest.TestCase):
    def test_every_unknown_or_false_premise_refuses_even_empty_work(self):
        for field in fields(P):
            for bad in (False, None, 1, "true"):
                premise = replace(P, **{field.name: bad})
                for call in (lambda: dma_domains(config(dma_active=False), premise),
                             lambda: hdma_domains(config(), 0, premise),
                             lambda: dispatch_route(0x4211, "A", "read", premise)):
                    with self.assertRaises(RefusedPremise):
                        call()

    def test_exact_input_types_and_declared_bounds(self):
        for name, bad in (("source_bank", True), ("source_address", -1),
                          ("transfer_size", 65536), ("transfer_mode", 8),
                          ("do_transfer", 1), ("hdma_bank", 256)):
            with self.assertRaises(ValueError):
                config(**{name: bad})
        for bad in (True, -1, MAX_SERVICES + 1, None, 1.0):
            with self.assertRaises(ValueError):
                hdma_domains(config(), bad, P)
        with self.assertRaises(ValueError):
            hdma_domains(config(), 1, P, include_init=1)
        with self.assertRaises(RefusedPremise):
            dma_domains(config(), {"fixed": True})
        with self.assertRaises(ValueError):
            copy_bus_accesses(0, 0x2180, False, a_is_wram=None)


if __name__ == "__main__":
    unittest.main()
