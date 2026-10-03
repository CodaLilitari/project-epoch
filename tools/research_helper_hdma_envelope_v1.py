"""Conditional generic HDMA/refresh composition; no admission certificate.

Pure import. Reads source pins and accepted metadata only, never raw traces/ROMs.
"""
from pathlib import Path
from itertools import product
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'tools/research_helper_hdma_envelope_v1.py'
TESTS = 'tests/test_research_helper_hdma_envelope_v1.py'
COMMIT = '137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1'
PINS = {
 'baseline_source': ('tools/research_helper_timing_envelope_v1.py',7962,'c8f160d8eb57bd4b22f10954bc6cbda231802272df1f55344345a2c30158733a'),
 'baseline_reference': ('references/schala_package_helper_timing_envelope_v1.json',5974,'058d9f1ac1a2bb1c9a2f7ea375e9f507d3e1536e475eaf1316f1afd5dad0d8db'),
 'phase_reference': ('references/schala_package_resolver_phase_v2.json',53831,'8e3898c7886a88e166bf5fd13f69ac37b44b59bd202d5780c0a8ae98ae30c120'),
 'dma': ('private/research/mesen_nmi_request_2_1_1/SnesDmaController.cpp',19939,'f0bd85d5a3001cb3c847980922d6cf2aa19ef294a562a9c827f189328a1cfae6'),
 'dma_header': ('private/research/mesen_nmi_request_2_1_1/SnesDmaController.h',1451,'05a4c63d0f18efd11b12bd476f4bf99bb0d7cd8ba2b51f95bdb463653f82cdfd'),
 'dma_types': ('private/research/mesen_resolver_phase_2_1_1/DmaControllerTypes.h',540,'b03114d7ff465eee145356c204ab95ca110a856f95dc80edfbe1833e7a0537c7'),
 'memory': ('private/research/mesen_timing_api_2_1_1/SnesMemoryManager.cpp',12100,'2f1e365d5a2b5e7f2bbfe61abf8ecf04c96760842e0ec68de2aa603118664d58'),
 'ppu': ('private/research/mesen_timing_api_2_1_1/SnesPpu.cpp',83153,'5f61ed7c8da25938b494a4d42b270109dd9500ea5d155130b6b69ff774458180'),
 'cpu': ('private/research/mesen_timing_api_2_1_1/SnesCpu.cpp',3666,'ea81ccb2b6093fdde5ff2d1bfbc4a4a88a596e39b841e94786f343c5974491b8'),
 'bus_b': ('private/research/mesen_irq_dma7_2_1_1/RegisterHandlerB.cpp',2969,'a3ebaecac6e6fe2d2bdfc04f072e77a9ba47251cdc5ae9d4b6fcdd4618af7ea7'),
 'irq_header': ('private/research/mesen_nmi_request_2_1_1/InternalRegisters.h',5020,'d4433c01d99f587d3686a5df72d50fc5942e51ad56ef868987d7ec0bce2a4698'),
 'irq_cpp': ('private/research/mesen_nmi_request_2_1_1/InternalRegisters.cpp',12742,'2b964a17f6cd16bb98f7953d7f8f8036cdf0c1178e87bb204eb846782cf96cbc'),
}
COUNTS = (1, 2, 2, 4, 4, 4, 2, 4)
SPANS = (
 ('dma',8,12,'transfer-mode byte counts and register offsets'),
 ('dma',46,66,'one DMA data byte has eight base clocks'),
 ('dma',68,102,'manual DMA transfer loop and HDMA interleaving'),
 ('dma',104,172,'initialization at most three table bytes per enabled channel'),
 ('dma',174,204,'HDMA bounded payload loop'),
 ('dma',206,218,'start/end synchronization'),
 ('dma',230,335,'HDMA transfer and counter/indirect reload service'),
 ('dma',347,405,'request flags, start delay and service dispatch'),
 ('dma',408,436,'CPU MDMAEN and HDMAEN writes'),
 ('memory',158,219,'clock increments and refresh cost'),
 ('memory',224,264,'HDMA/refresh requests and frame-zero initialization'),
 ('memory',293,328,'DMA read four clocks'),
 ('memory',360,388,'DMA write four clocks; DMA-controller writes ignored'),
 ('ppu',395,398,'scanline timing under the declared minimum-line premise'),
 ('ppu',459,486,'scanline advancement and frame zero'),
 ('ppu',538,560,'frame threshold updates; declared minimum-frame premise remains required'),
 ('ppu',2253,2257,'serialized scanline is the internal scanline'),
 ('cpu',88,96,'idle CPU speed six'),
 ('cpu',119,130,'pending service at CPU cycle'),
 ('cpu',143,157,'CPU speed selected before pending service'),
 ('bus_b',61,88,'PPU versus WRAM-port destinations'),
 ('irq_header',27,34,'separate uint16 internal IRQ counters'),
 ('irq_header',79,102,'timer comparison uses internal counters'),
 ('irq_header',104,162,'counter update and overclock-aware advancement'),
 ('irq_cpp',409,410,'internal IRQ counters are serialized'),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def serial(value):
    return (json.dumps(value, indent=2)+'\n').encode('utf-8')


def identity(relative, size=None, digest=None):
    require(not Path(relative).is_absolute() and '..' not in Path(relative).parts, 'bounded source path')
    raw = (ROOT/relative).read_bytes()
    require(size is None or len(raw) == size, f'size drift: {relative}')
    require(digest is None or sha(raw) == digest, f'hash drift: {relative}')
    return {'path': relative, 'size_bytes': len(raw), 'sha256': sha(raw)}


def channel_cost(mode, enabled, finished, transfer, indirect, counter, new_zero, last):
    """Finite source-equivalence classes; payload values need not be observed."""
    require(type(mode) is int and 0 <= mode < 8, 'exact transfer mode')
    require(type(counter) is int and 0 <= counter < 256, 'exact counter byte')
    require(all(type(v) is bool for v in (enabled, finished, transfer, indirect, new_zero, last)), 'exact state booleans')
    if not enabled or finished:
        return 0
    table_reads = 1
    if ((counter-1)&127) == 0 and indirect:
        table_reads += 1 if new_zero and last else 2
    return 8*((COUNTS[mode] if transfer else 0)+table_reads)


def solve(base, event_charge, spacing=1352):
    """Ceil solution to T <= base + 2*C + (C/D)*T; refuse no finite bound."""
    require(type(base) is int and base >= 0, 'nonnegative integer base')
    require(type(spacing) is int and spacing > 0, 'positive integer spacing')
    require(type(event_charge) is int and 0 <= event_charge < spacing, 'event duty must be below spacing')
    numerator = (base+2*event_charge)*spacing
    denominator = spacing-event_charge
    return (numerator+denominator-1)//denominator


def envelope(base, scanline, hclock):
    require(type(scanline) is int and 0 <= scanline < 262, 'phase within first 262 lines')
    require(type(hclock) is int and 0 <= hclock < 1364, 'exact line clock')
    refresh, hdma, init = 40, 472, 216
    coarse = solve(base, refresh+hdma+init)
    init_spacing = 262*1360-8
    next_frame_min = max(0, (262-scanline)*1360-hclock)
    return {'helper_base_clocks': base, 'hdma_service_max': hdma, 'refresh_event_clocks': refresh,
        'initialization_service_max': init, 'weakened_event_spacing': 1352,
        'coarse_allowing_init_at_line_frequency': coarse,
        'minimum_initialization_event_spacing': init_spacing,
        'phase_independent_at_most_one_init': solve(base+init, refresh+hdma) if coarse < init_spacing else None,
        'phase_to_next_frame_zero_lower_bound': next_frame_min,
        'phase_no_init': solve(base, refresh+hdma) if coarse < next_frame_min else None,
        'initialization_refinement_requires_no_pending_initial_service': True}


def finite_cost_model():
    maxima = [0]*8
    cases = 0
    for args in product(range(8), (False, True), (False, True), (False, True),
                        (False, True), range(256), (False, True), (False, True)):
        maxima[args[0]] = max(maxima[args[0]], channel_cost(*args))
        cases += 1
    require(cases == 131072 and maxima == [32,40,40,56,56,56,40,56], 'finite per-mode maxima')
    sync = []
    for phase, speed, body in product((0,2,4,6), (6,8), range(8,457,8)):
        before = 8-phase
        after = speed-((before+body)%speed)
        require(before in (2,4,6,8) and after in (2,4,6,8), 'source clock alignment')
        sync.append(before+after)
    require(len(sync) == 456 and max(sync) == 16, 'finite synchronization maximum')
    require(8*max(maxima)+8+max(sync) == 472 and 8*24+8+max(sync) == 216, 'service maxima')
    return {'channel_equivalence_cases': cases, 'per_mode_max_base_clocks': maxima,
        'alignment_cases': len(sync), 'maximum_start_plus_end_alignment': max(sync),
        'common_service_clocks': 8, 'generic_eight_mode_hdma_clocks': 472,
        'generic_eight_channel_initialization_clocks': 216,
        'per_channel_derivation': 'at most four payload bytes, one counter read, two indirect-pointer reads; each costs eight base clocks'}


def phase_observation(reference):
    require(reference['schema'] == 'project-epoch-package-resolver-phase-v2-accepted-pair', 'accepted phase schema')
    require(reference['full_trace_bytes_identical'] is True and len(reference['runs']) == 2, 'accepted repeated phase pair')
    require(reference['deadline_certified'] is False and reference['native_helper_executed'] is False
            and reference['production_approval'] is False, 'preserve phase proof boundaries')
    entries = []
    for run in reference['runs']:
        selected = [row for row in run['projection']['phases'] if row['kind'] == 'resolver-entry']
        require(len(selected) == 1, 'one resolver entry per accepted projection')
        entries.append(selected[0])
    require(entries[0] == entries[1], 'matching accepted entry projections')
    row = entries[0]
    require(row['scanline'] == 119 and row['hclock'] == 754, 'exact observed phase')
    require(row['dma_active_channels'] == [] and row['hdma_unfinished_enabled_channels'] == list(range(8)), 'observed channel status')
    hardware = row['hardware']
    require(hardware['dmaController.hdmaChannels'] == 255, 'observed enable mask')
    names = ('dmaPending','dmaStartDelay','needToProcess','hdmaPending','hdmaInitPending')
    require(all(hardware['dmaController.'+k] is False for k in names), 'observed pending flags clear')
    return {'kind': row['kind'], 'poll': row['poll'], 'master_clock': row['master_clock'],
        'scanline': row['scanline'], 'hclock': row['hclock'], 'hdma_enabled_mask': 255,
        'dma_active_channels': [], 'hdma_unfinished_enabled_channels': list(range(8)),
        'pending_flags': {k: False for k in names},
        'transfer_modes_or_table_payloads_inferred': False,
        'source': 'accepted compact projection only; no raw trace or native rerun'}


def collect():
    pins = {key: identity(*value) for key, value in PINS.items()}
    own = [identity(p) for p in (SOURCE, TESTS)]
    baseline = json.loads((ROOT/PINS['baseline_reference'][0]).read_bytes())
    require(baseline['schema'] == 'project-epoch-helper-timing-envelope-v1'
        and baseline['model_sha256'] == PINS['baseline_source'][2], 'exact reviewed timing model')
    require(baseline['production_approval'] is False and baseline['interrupt_exclusion_proved'] is False,
        'preserve earlier non-admission scope')
    base = baseline['results']['immutable_v3_all_paths']['base_clocks']
    require(base == 65046, 'exact immutable-v3 base inventory')
    inherited = baseline['source_identities']
    underlying = [identity(p, v['size_bytes'], v['sha256']) for p, v in sorted(inherited.items())]
    phase = phase_observation(json.loads((ROOT/PINS['phase_reference'][0]).read_bytes()))
    costs = finite_cost_model()
    bound = envelope(base, phase['scanline'], phase['hclock'])
    require(bound['coarse_allowing_init_at_line_frequency'] == 144088
        and bound['phase_independent_at_most_one_init'] == 106689
        and bound['phase_to_next_frame_zero_lower_bound'] == 193726
        and bound['phase_no_init'] == 106342, 'exact generic envelope arithmetic')
    spans = []
    for key, first, last, role in SPANS:
        path = PINS[key][0]
        lines = (ROOT/path).read_bytes().splitlines(keepends=True)
        require(0 < first <= last <= len(lines), 'bounded semantic span')
        spans.append({'path': path, 'first_line': first, 'last_line_inclusive': last,
            'sha256': sha(b''.join(lines[first-1:last])), 'role': role,
            'interpretation': 'reviewer-derived over pinned source'})
    result = {'schema': 'project-epoch-helper-hdma-envelope-v1',
        'evidence_level': 'conditional-static-model', 'status': 'conditional-envelope-not-admission-certificate',
        'source_identities': own, 'prerequisites': pins, 'baseline_source_identities_rechecked': underlying,
        'mesen_commit': COMMIT, 'reviewed_source_spans': spans, 'phase_observation': phase,
        'cost_model': costs, 'generic_envelope': bound,
        'derivation': 'For every finite elapsed execution prefix, CPU work is at most B; charge any partially started service its entire bound. For each family N<=1+ceil(T/1352)<=2+T/1352. Thus T<=B+2*C+(C/1352)*T. Solving this inequality bounds every prefix and rules out unbounded starvation under the premises without assuming completion. Strict coarse-bound comparisons then permit at-most-one-init or no-init refinement.',
        'baseline_scope': 'Unchanged immutable-v3 fixture only, including original entry JML through final helper JML; excludes tail opcode and additional wrappers.',
        'validation_scope': 'Exact published baseline source/reference and its eight declared source identities rechecked. Accepted compact phase reference checked. Neither earlier collector is regenerated; no raw ROM or trace is read.',
        'premises': ['Original helper CPU cycles have six/eight-clock speeds; native fixed-SP and immutable registry/source assumptions remain.',
            'Normal pinned event scheduling with minimum 1360-clock lines and 262-line frames as explicit independent premises; no reset/stop or external CPU mutation. Actual configuration and cached timing thresholds are not certified here.',
            'No interrupt handler, coprocessor stall, memory corruption or new manual-DMA request occurs in the interval.',
            'Initially clear pending/manual-active state is observed; future absence must follow from an established writer/handler contract.',
            'HDMA control remains valid, with at most eight channels and supported modes; normal internal pointers/counters may evolve and all table/payload values remain unconstrained.',
            'HDMA does not corrupt helper live counters, frames, registry or code. The compact phase projection does not certify destination/source isolation.',
            'Any extra admission, trampoline or wrapper work needs additional base-cost accounting.'],
        'open_obligations': ['InternalRegisters hCounter/vCounter and overclock/extra-scanline configuration were not captured; PPU line119 plus verticalTimer211 is not a certified request boundary.',
            'Nonnegative extra-scanline settings alone do not establish the line/frame minima: cached thresholds may wrap. Configuration bounds and valid cache recomputation remain unproved for the observed phase.',
            'An observed IRQ handler-entry gap follows recognition and is not an admission deadline.',
            'Unknown forward HDMA source reads may observe helper stack/publication writes and transmit changed values to PPU; source-read isolation and rendering equivalence remain open.',
            'Unknown payloads may alter SETINI when that destination is configured; initial PPU mode flags are not assumed constant.',
            'Generic 32-target helper base235926 is a separate contract; even no-init HDMA arithmetic would be381377. The fixed-v3 bound is not reusable for arbitrary future bindings.',
            'Transfer modes omitted from compact phase metadata are not reconstructed here; mode-specific private refinements are not published by this model.'],
        'native_helper_executed': False, 'new_native_run': False, 'raw_game_data_emitted': False,
        'deadline_certified': False, 'memory_source_isolation_proved': False,
        'render_equivalence_proved': False, 'production_approval': False,
        'reproduce': ['python','-B',SOURCE], 'serialization': 'binary UTF-8/LF JSON with one trailing newline'}
    require(own == [identity(p) for p in (SOURCE, TESTS)], 'own source drift')
    require(pins == {key: identity(*value) for key, value in PINS.items()}, 'prerequisite drift')
    require(underlying == [identity(p,v['size_bytes'],v['sha256']) for p,v in sorted(inherited.items())], 'baseline source drift')
    return result


if __name__ == '__main__':
    sys.stdout.buffer.write(serial(collect()))
