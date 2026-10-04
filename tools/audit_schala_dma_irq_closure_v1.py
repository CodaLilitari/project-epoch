"""Reuse accepted resolver traces and bound DMA bus domains, without a new run.

Only hardware configuration and original analysis are emitted. Channel-domain
premises are hypotheses; this packet cannot certify a game deadline or hook.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE_PIN = ('references/schala_package_resolver_phase_v3.json', 63846,
             'ef647b161531bc1d207f3aa1feacb4b8d669863e04b7390348d0d16381a3d1c1')
TRACE_PIN = (17946524, 'cbcfee04c0eab0381d77392e43baf8cc5ed3c62b8a22ac533bf2d263424bd619')
SOURCE_MANIFEST = 'references/mesen_dma_irq_closure_sources_v1.json'
CALLBACK_FACTS = 'references/schala_dma_callback_facts_v1.json'
SOURCE_PIN = (SOURCE_MANIFEST, 20104, '07a69c89af44a67a7491c563fab0df80ef811d055b7fa9183530f097b20f4578')
FACTS_PIN = (CALLBACK_FACTS, 36051, 'a620789cd223d94916863a08862c2bfc2b841a8b5483c7b1c1f646a4b955f376')
CONFIG_FIELDS = ('srcBank', 'hdmaBank', 'destAddress', 'transferMode',
                 'invertDirection', 'hdmaIndirectAddressing', 'decrement', 'fixedTransfer')
FIELD_MAP = dict(source_bank='srcBank', source_address='srcAddress',
    transfer_size='transferSize', dest_address='destAddress', transfer_mode='transferMode',
    invert_direction='invertDirection', decrement='decrement', fixed_transfer='fixedTransfer',
    dma_active='dmaActive', hdma_bank='hdmaBank', hdma_table_address='hdmaTableAddress',
    hdma_line_counter='hdmaLineCounterAndRepeat', do_transfer='doTransfer',
    hdma_finished='hdmaFinished', hdma_indirect='hdmaIndirectAddressing')
ORIGINAL_FILES = ('tools/schala_dma_irq_domains_v1.py', 'tests/test_schala_dma_irq_domains_v1.py',
    'tools/audit_schala_dma_irq_closure_v1.py', 'tests/test_audit_schala_dma_irq_closure_v1.py')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def serial(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode('utf-8')


def read_identity(relative, size=None, digest=None):
    require(type(relative) is str and not Path(relative).is_absolute() and
            '..' not in Path(relative).parts, 'bounded repository path')
    raw = (ROOT / relative).read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    require(size is None or len(raw) == size, 'size drift: ' + relative)
    require(digest is None or sha == digest, 'hash drift: ' + relative)
    return raw, dict(path=relative, size_bytes=len(raw), sha256=sha)


def identity(relative, size=None, digest=None):
    return read_identity(relative, size, digest)[1]


def hardware_bus(address):
    require(type(address) is int and 0 <= address <= 0xFFFFFF, 'exact bus address')
    bank, offset = address >> 16, address & 0xFFFF
    return (bank < 0x40 or 0x80 <= bank < 0xC0) and (
        offset == 0x4200 or 0x4207 <= offset <= 0x420D or 0x4300 <= offset <= 0x437F)


def clock(row):
    value = row['timing']['memoryManager.masterClock']
    require(type(value) is int and 0 <= value < 2**64, 'full serialized clock')
    return value


def channels(row):
    from schala_dma_irq_domains_v1 import ChannelConfig
    h = row['engine']
    mask = h['dmaController.hdmaChannels']
    require(type(mask) is int and 0 <= mask <= 255, 'exact HDMA mask')
    return [ChannelConfig(**{name: h[f'dmaController.channel[{i}].{field}']
        for name, field in FIELD_MAP.items()}, hdma_enabled=bool(mask & (1 << i))) for i in range(8)]


def project(records):
    require(type(records) is list and len(records) == 2263, 'accepted record count')
    def one(kind):
        found = [i for i, r in enumerate(records) if r['kind'] == kind]
        require(len(found) == 1, 'one ' + kind)
        return found[0]
    first, last = one('resolver-entry'), one('resolver-tail')
    require(first < last, 'ordered resolver interval')
    entry, tail = records[first], records[last]
    require((clock(entry), entry['timing']['ppu.scanline'], entry['timing']['memoryManager.hClock']) ==
            (2155080050, 119, 754), 'pinned entry')
    interval = records[first:last+1]
    require(clock(tail)-clock(entry) == 4244 and len(interval) == 81, 'pinned observed interval')
    configs = channels(entry)
    require(all(c.source_bank == c.hdma_bank == 0x7E and not c.invert_direction and
        c.hdma_indirect and c.hdma_enabled and not c.hdma_finished and not c.dma_active
        for c in configs), 'observed entry bank/direction/lifecycle')
    watched = [r for r in records if r['kind'] in ('bus-read', 'bus-write') and hardware_bus(r['address'])]
    inside = [r for r in interval if r['kind'] in ('bus-read', 'bus-write') and hardware_bus(r['address'])]
    require(not inside, 'observed resolver hardware traffic changed')
    selected_keys = [f'dmaController.channel[{i}].{field}' for i in range(8) for field in CONFIG_FIELDS]
    require(all(r['engine'][k] == entry['engine'][k] and type(r['engine'][k]) is type(entry['engine'][k])
                for r in interval for k in selected_keys), 'sampled configuration drift')
    later = [r for r in watched if clock(r) > clock(entry) and r['kind'] == 'bus-write']
    require(later, 'later watched write required')
    first_write = later[0]
    irq = next(r for r in records[last+1:] if r['kind'] == 'interrupt-entry')
    before_irq = [r for r in records[first:] if clock(r) <= clock(irq)]
    require(len(before_irq) == 682 and clock(irq)-clock(entry) == 124904,
            'following interrupt interval')
    require(not any(r['kind'] in ('bus-read', 'bus-write') and hardware_bus(r['address'])
                    for r in before_irq), 'pre-IRQ hardware traffic changed')
    return dict(entry_clock=clock(entry), entry_scanline=119, entry_hclock=754,
        channels=[asdict(c) for c in configs], resolver_interval=dict(selected_rows=len(interval),
            master_clocks=4244, watched_hardware_events=len(inside),
            sampled_configuration_fields=list(CONFIG_FIELDS), sampled_configuration_equal=True,
            endpoint_equality_is_lifetime_proof=False),
        through_following_interrupt=dict(selected_rows=len(before_irq), master_clocks=124904,
            watched_hardware_events=0, counterfactual_helper_execution=False),
        full_window_watched_hardware_reads=sum(r['kind']=='bus-read' for r in watched),
        full_window_watched_hardware_writes=sum(r['kind']=='bus-write' for r in watched),
        first_later_watched_write=dict(address=first_write['address'], value=first_write['value'],
            master_clock=clock(first_write), offset=clock(first_write)-clock(entry)),
        watcher_covers_timeup=False, table_and_payload_values_captured=False,
        controller_profile_captured=False, future_configuration_certified=False)


def accepted_projection():
    reference_raw, _ = read_identity(*PHASE_PIN)
    reference = json.loads(reference_raw)
    # Pin the frozen auditor before executing it. Its own transitive file ledger
    # revalidates the accepted source, launch receipts and raw artifacts offline.
    for item in reference['acceptance_source_identities']:
        identity(item['path'], item['size_bytes'], item['sha256'])
    import audit_package_resolver_phase_v3 as previous
    directories = [ROOT / r['directory'] for r in reference['runs']]
    require(serial(previous.audit_pair(*directories)) == reference_raw,
            'complete accepted v3 revalidation differs')
    projections = []
    traces = []
    for directory in directories:
        name = (directory / 'trace.json').relative_to(ROOT).as_posix()
        raw, trace_id = read_identity(name, *TRACE_PIN)
        traces.append(trace_id)
        projections.append(project(json.loads(raw)['records']))
    require(projections[0] == projections[1], 'reused hardware projection pair differs')
    return projections[0], traces


def collect():
    # Capture original artifacts and pinned metadata before consuming any of
    # them. End-of-collection checks compare to these initial identities.
    artifacts = [identity(p) for p in ORIGINAL_FILES]
    source_raw, source_id = read_identity(*SOURCE_PIN)
    facts_raw, facts_id = read_identity(*FACTS_PIN)
    artifacts += [source_id, facts_id, identity(*PHASE_PIN)]
    from schala_dma_irq_domains_v1 import (ChannelConfig, DomainPremises,
        hdma_domains, dma_domains, SOURCE_REVISION)
    sources = json.loads(source_raw)
    require(sources['revision'] == SOURCE_REVISION, 'source revision')
    require(sources['schema'] == 'project-epoch-dma-irq-closure-upstream-sources-v1', 'source schema')
    require(len(sources['sources']) == len({s['upstream_path'] for s in sources['sources']}) == 42,
            'complete unique source inventory')
    checked = []
    for item in sources['sources']:
        raw, source_identity = read_identity(item['path'], item['size_bytes'], item['sha256'])
        checked.append(source_identity)
        blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        require(blob == item['git_blob_sha1'], 'source Git blob identity')
    facts = json.loads(facts_raw)
    require(facts['source_revision'] == SOURCE_REVISION and
            facts['game_callback_closure_proved'] is False, 'callback fact scope')
    require(facts['schema'] == 'project-epoch-callback-closure-review-facts-v1' and
            [f['id'] for f in facts['facts']] == [f'CC{i:02}' for i in range(1,25)],
            'complete ordered callback facts')
    by_upstream = {s['upstream_path']: s for s in sources['sources']}
    span_count = 0
    for fact in facts['facts']:
        require(fact['status'] in ('closed','open'), 'explicit conditional fact status')
        for span in fact['evidence']:
            source = by_upstream[span['upstream_path']]
            raw, _ = read_identity(source['path'],source['size_bytes'],source['sha256'])
            lines = raw.splitlines(keepends=True)
            lo, hi = span['line_start'], span['line_end']
            require(type(lo) is type(hi) is int and 1 <= lo <= hi <= len(lines), 'exact source span')
            require(hashlib.sha256(b''.join(lines[lo-1:hi])).hexdigest() == span['span_sha256'],
                    'source span drift: '+fact['id'])
            span_count += 1
    observed, traces = accepted_projection()
    premise = DomainPremises(True, True, True, True, True)
    configs = [ChannelConfig(**c) for c in observed['channels']]
    domains = [hdma_domains(c, 65536, premise).to_dict() for c in configs]
    require(all(not any(d['irq_candidates'].values()) for d in domains), '7E IRQ domain exclusion')
    bports = sorted({address for d in domains for v in d['domains'] if v['bus']=='B'
        for lo, hi in v['addresses']['intervals_inclusive'] for address in range(lo,hi+1)})
    require(0x2133 in bports and all(0x2100 <= x <= 0x2133 for x in bports), 'observed B ports')
    donor = configs[0]
    table_ack = hdma_domains(replace(donor, source_bank=0, hdma_table_address=0x4211,
        do_transfer=False), 1, premise).to_dict()
    reverse = dma_domains(replace(donor, source_bank=0, source_address=0,
        transfer_size=0, dma_active=True, invert_direction=True), premise).to_dict()
    require(len(table_ack['irq_candidates']['timeup_reads']) == 1,
            'HDMA control-read acknowledgment candidate')
    require(len(reverse['irq_candidates']['irq_register_writes']) == 5,
            'manual reverse IRQ-write candidates')
    # Recheck every input after computation, preserving the earlier frozen audit.
    for item in checked + traces + artifacts:
        identity(item['path'], item['size_bytes'], item['sha256'])
    return dict(schema='project-epoch-dma-irq-closure-v1',
        evidence_level='reused-observation-and-source-conditional-domain-model',
        source_revision=SOURCE_REVISION, original_and_reference_identities=artifacts,
        upstream_identities=checked, accepted_trace_identities=traces,
        original_v3_auditor_reproduced_byte_identically=True,
        observed_hardware=observed, conditional_domain_premises=asdict(premise),
        premises_are_certificates=False, hdma_service_bound=65536,
        service_bound_is_a_time_bound=False, channel_domains=domains,
        possible_b_payload_ports=bports, direct_irq_register_candidates=[],
        all_table_and_payload_A_reads_stay_in_bank_7E=True,
        synthetic_counterexamples=dict(table_read_even_without_payload=table_ack,
            reverse_manual_zero_size_wrap=reverse), callback_facts=facts,
        callback_evidence_spans_rehashed=span_count,
        callback_semantics_automatically_derived=False,
        new_native_run=False, raw_game_data_emitted=False,
        all_memory_handler_effects_closed=False, callback_closure_proved=False,
        game_deadline=None, game_helper_admitted=False, production_approval=False,
        reproduce=['python','-B','tools/audit_schala_dma_irq_closure_v1.py'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    raw = serial(collect())
    if args.output:
        args.output.write_bytes(raw)
    else:
        import sys
        sys.stdout.buffer.write(raw)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
