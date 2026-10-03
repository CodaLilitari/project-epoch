"""Conditional scene8B half-fill termination and exact local CPU-write geometry.

Import is pure. Canonical bytes stay private; output contains metadata only.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'tools/audit_schala_scene8b_half_fill_v1.py'
TESTS = 'tests/test_schala_scene8b_half_fill_v1.py'
ROM = ROOT / 'private/input/rom_archive/Chrono Trigger (USA).sfc'
ROM_SHA = '06d1c2b06b716052c5596aaa0c2e5632a027fee1a9a28439e509f813c30829a9'
START, END = 0xCD34F1, 0xCD352D
EXCLUDED_Q = (2, 3, 6, 7)
PINS = {
    'copy_source': ('tools/audit_schala_scene8b_copy_producers_v1.py', 29492, '9a9619921c7cb310c8f0ad545109fe9b3c16cb04c63e3787b025c4087a39aec1'),
    'copy_tests': ('tests/test_schala_scene8b_copy_producers_v1.py', 16150, '60b316d31947f86703d6ba46384930f25a3f7aa04fc1db293f24d1fff6c2ae19'),
    'copy_reference': ('references/schala_scene8b_copy_producers_v1.json', 171599, 'f3fc3cf0999d0782f80c76a39ace13332dc31ef895482391e3e3282512d14ee6'),
    'irq_reference': ('references/schala_package_irq_memory_contract_v2.json', 84558, '6a6cc3ac65cc2e9ae5d5fe92a313a7a716f31cdbc1256fc18d38a4731eaadc31'),
    'cpu_instructions': ('private/research/mesen_timing_api_2_1_1/SnesCpu.Instructions.h', 27673, '9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd'),
    'cpu_shared': ('private/research/mesen_timing_api_2_1_1/SnesCpu.Shared.h', 20483, 'dd84d0794c9588adfd28932659edb07a7b5b9d2d052fbcd4696925026237210f'),
    'cpu_core': ('private/research/mesen_timing_api_2_1_1/SnesCpu.cpp', 3666, 'ea81ccb2b6093fdde5ff2d1bfbc4a4a88a596e39b841e94786f343c5974491b8'),
    'cpu_memory': ('private/research/mesen_timing_api_2_1_1/SnesMemoryManager.cpp', 12100, '2f1e365d5a2b5e7f2bbfe61abf8ecf04c96760842e0ec68de2aa603118664d58'),
}
FILL_SPANS = (
    (START, END, 'b9df1c83b5d4336c44848cef615acc9c51da614efd37e63403d7d0ddbddc70c8'),
    (0xCD350E, 0xCD3519, '5376e5bd2a369d754b41fa8b4f94c678f36930be63a30ffb3a5f96e824a30900'),
    (0xCD351E, 0xCD3529, 'f96e72446d5cfa5fefc44ad0c1714d98ea13ef6def308b572ac53935e19fcad9'),
)
WRITER_SPANS = (
    (0xCD2FBC, 0xCD3017, '4bff9f0807a89e766aaca2fb1ceb616f08b2749e605f45cb18ff36b46e9dba99'),
    (0xCD24F3, 0xCD2518, '19daf796369f42785a86065c353ad7160392566b7700a784cb56def0d11d8731'),
    (0xCD2436, 0xCD2460, '7d36aaf905137a336eac62422ed7a8bef5282258dfa85a46aa4e5cc0374d5c75'),
    (0xCD1B42, 0xCD1B5E, 'c894d84f43b7195f7a18a3d69bc52f6849698ca9af5cf1021b7cda14c4d92f32'),
    (0xCD1A8B, 0xCD1AB2, '4b1bea2954252c900444ffa8c9fef2982196dd9bed98c6fb4b3cffe6532b94f4'),
    (0xCD3189, 0xCD31B7, '93d0ebd1f808af0d973421c0d9cd3792adc3d547d645c4d41580e4d4617ec046'),
    (0xCD109F, 0xCD10B9, '6641bad845d13e252dc2281357366d8ca7a419ffdfaa0623dd1afb1af483af83'),
    (0xCD1F96, 0xCD1F9F, '4110f74a0744178e385033bf9b77a4df87029b49903da2bb385b4ab1079e9e78'),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def serial(value):
    return (json.dumps(value, indent=2) + '\n').encode('utf-8')


def identity(path, expected=None, size=None):
    raw = path.read_bytes()
    require(size is None or len(raw) == size, f'size drift: {path}')
    require(expected is None or sha(raw) == expected, f'hash drift: {path}')
    return {'path': path.relative_to(ROOT).as_posix(), 'size': len(raw), 'sha256': sha(raw)}


def input_contract(q, s, frame_word, unknown_high, fill, *, m8=False, x8=False,
                   d=0, dbr=0x7E, decimal=False, stable_target=True):
    for name, value in (('q', q), ('s', s), ('unknown_high', unknown_high)):
        require(type(value) is int and 0 <= value <= 255, f'exact byte {name}')
    for name, value in (('frame_word', frame_word), ('fill', fill)):
        require(type(value) is int and 0 <= value <= 65535, f'exact word {name}')
    require(q not in EXCLUDED_Q, 'preserved q-selected r/s aliases CAAA/CAAB unresolved')
    require(m8 is False and x8 is False, 'requires M16/X16')
    require(type(d) is int and d == 0 and type(dbr) is int and dbr == 0x7E, 'requires D0/DBR7E')
    require(decimal is False, 'requires binary arithmetic')
    require(stable_target is True, 'requires stable DP45 target and no asynchronous changes')


def execute(read, q, s, frame_word, *, unknown_high=0, fill=0xA55A,
            start=START, end=END, step_limit=120000, **premises):
    """Original finite interpreter, also usable with independently authored tests.

    All memory reads are the declared input words or defined DP words. Stores
    update DP45 or append physical indexed writes. Indexed writes must not alias
    live DP or the unread BA00 value. No stack contents/ownership are inferred.
    """
    input_contract(q, s, frame_word, unknown_high, fill, **premises)
    require(type(start) is int and type(end) is int and 0 <= start < end <= 0x1000000, 'exact code interval')
    require(type(step_limit) is int and 0 < step_limit <= 120000, 'finite step budget')
    pc, a, x, m8, carry, zero = start, None, None, False, None, None
    dp = {0x47: s, 0x7C: frame_word}
    indexed, dp_writes, contexts, read_sites, wraps = [], [], set(), [], 0
    lengths = {0xA5: 2, 0xAD: 3, 0xA9: 3, 0x0A: 1, 0x85: 2, 0x29: 3,
               0xAA: 1, 0x18: 1, 0x65: 2, 0xF0: 2, 0x9D: 3, 0xE8: 1,
               0xE4: 2, 0xD0: 2, 0x80: 2, 0x7B: 1, 0xE2: 2, 0x60: 1}
    for step in range(step_limit):
        require(start <= pc < end, 'control outside exact code interval')
        head = read(pc, 1)
        require(type(head) is bytes and len(head) == 1, 'exact opcode read')
        op = head[0]
        require(op in lengths, f'unmodeled opcode ${op:02X}')
        require(not m8 or op == 0x60, 'only RTS admitted after final SEP20')
        n = lengths[op]
        require(pc + n <= end, 'instruction crosses code boundary')
        raw = read(pc, n)
        require(type(raw) is bytes and len(raw) == n and raw[0] == op, 'exact stable instruction read')
        operand = int.from_bytes(raw[1:], 'little')
        contexts.add((pc, m8))
        nxt = pc + n
        if op == 0xA5:
            require(operand in dp, 'undefined DP word')
            a = dp[operand]; zero = a == 0
            read_sites.append((pc, 0x7E0000 + operand))
        elif op == 0xAD:
            require(operand in (0xCAAA, 0xBA00), 'unmodeled external read')
            require(not any(address in (0x7E0000 + operand, 0x7E0000 + operand + 1)
                            for _, low, high, _ in indexed for address in (low, high)),
                    'external reload aliases prior local indexed write')
            a = q | (unknown_high << 8) if operand == 0xCAAA else fill
            zero = a == 0; read_sites.append((pc, 0x7E0000 + operand))
        elif op == 0xA9:
            a = operand; zero = a == 0
        elif op == 0x0A:
            require(type(a) is int, 'undefined A')
            carry = bool(a & 0x8000); a = (a << 1) & 65535; zero = a == 0
        elif op == 0x85:
            require(operand == 0x45 and type(a) is int, 'only defined DP45 store')
            dp[operand] = a; dp_writes.append((pc, 0x7E0045, a))
        elif op == 0x29:
            require(type(a) is int, 'undefined A')
            a &= operand; zero = a == 0
        elif op == 0xAA:
            require(type(a) is int, 'undefined A')
            x = a; zero = x == 0
        elif op == 0x18:
            carry = False
        elif op == 0x65:
            require(type(a) is int and type(carry) is bool and operand in dp, 'undefined ADC inputs')
            total = a + dp[operand] + int(carry)
            a = total & 65535; carry = total > 65535; zero = a == 0
        elif op in (0xF0, 0xD0):
            require(type(zero) is bool, 'undefined branch zero flag')
            if zero == (op == 0xF0):
                nxt += int.from_bytes(raw[1:], 'little', signed=True)
        elif op == 0x9D:
            require(type(a) is int and type(x) is int, 'undefined indexed store input')
            address = (0x7E0000 + operand + x) & 0xFFFFFF
            high = (address + 1) & 0xFFFFFF
            require(0x7E0000 <= address < high < 0x800000, 'word store outside physical WRAM')
            require(not any(p in (0x7E0045, 0x7E0046, 0x7E0047, 0x7E0048,
                                  0x7E007C, 0x7E007D, 0x7EBA00, 0x7EBA01)
                            for p in (address, high)), 'store aliases local live input')
            indexed.append((pc, address, high, a))
        elif op == 0xE8:
            require(type(x) is int, 'undefined X')
            wraps += int(x == 65535); x = (x + 1) & 65535; zero = x == 0
        elif op == 0xE4:
            require(type(x) is int and operand in dp, 'undefined CPX inputs')
            zero = x == dp[operand]; carry = x >= dp[operand]
        elif op == 0x80:
            nxt += int.from_bytes(raw[1:], 'little', signed=True)
        elif op == 0x7B:
            a = 0; zero = True
        elif op == 0xE2:
            require(operand == 0x20, 'only SEP20 admitted')
            m8 = True
        elif op == 0x60:
            return {'a': a, 'x': x, 'm8': m8, 'dp': dp, 'indexed_writes': indexed,
                    'dp_writes': dp_writes, 'contexts': sorted(contexts),
                    'read_sites': sorted(set(read_sites)), 'x_wraps': wraps,
                    'return_site': pc, 'steps': step + 1}
        pc = nxt
    raise ValueError('finite step budget exhausted; no termination certificate')


def summarize(result, q, s, frame_word, fill=0xA55A):
    """Compare the actual interpreter ledger with a separate closed recurrence."""
    parity = frame_word & 1
    base = 0x7EC4E1 if parity else 0x7EC161
    count = s if s else 16384
    expected = [(base + 2 * (q & 1) + 4 * i,
                 base + 2 * (q & 1) + 4 * i + 1) for i in range(count)]
    writes = result['indexed_writes']
    require([(v[1], v[2]) for v in writes] == expected, 'loop differs from independent recurrence')
    require(all(v[3] == fill for v in writes), 'word fill value changed')
    require({v[0] for v in writes} == {0xCD350E if parity else 0xCD351E}, 'exact selected store site')
    target = 4 * s + 2 * (q & 1)
    require(result['dp_writes'] == [(0xCD34F5, 0x7E0045, 4 * s),
                                   (0xCD3502, 0x7E0045, target)], 'exact ordered DP45 setup')
    require(result['dp'][0x45] == target and result['x'] == target, 'exact final word target')
    require(result['a'] == 0 and result['m8'] and result['return_site'] == END - 1, 'exact final TDC/SEP/RTS return')
    require(result['x_wraps'] == int(s == 0), 'exact 16-bit X wrap count')
    flat = {address for pair in expected for address in pair}
    require(len(flat) == 2 * count, 'distinct indexed byte footprint')
    boundary = base + 0x380
    outside = next(({'iteration': i + 1, 'low': lo, 'high': hi}
                    for i, (lo, hi) in enumerate(expected) if hi >= boundary), None)
    bank7f = next(({'iteration': i + 1, 'low': lo, 'high': hi}
                   for i, (lo, hi) in enumerate(expected) if hi >= 0x7F0000), None)
    require((outside is None) == (1 <= s <= 224), 'exact comparison-envelope predicate')
    address_bytes = b''.join(address.to_bytes(3, 'little') for pair in expected for address in pair)
    cpu_bytes = b''.join(p.to_bytes(3, 'little') + value.to_bytes(2, 'little')
                         for _, p, value in result['dp_writes'])
    cpu_bytes += b''.join(lo.to_bytes(3, 'little') + value.to_bytes(2, 'little')
                          for _, lo, _, value in writes)
    return {'q': q, 's': s, 'frame_parity': parity, 'word_stores': count,
            'indexed_distinct_byte_writes': len(flat), 'dp_word_stores': 2,
            'ordinary_cpu_byte_store_events': 2 * count + 4,
            'first': expected[0], 'last': expected[-1], 'x_wraps': result['x_wraps'],
            'final_x': target, 'final_a': 0, 'return_m8': True,
            'comparison_envelope': [base, boundary], 'first_beyond_envelope': outside,
            'first_bank7f_write': bank7f,
            'writes_q_byte_7ecaaa': 0x7ECAAA in flat, 'writes_q_high_7ecaab': 0x7ECAAB in flat,
            'writes_known_irq_destination_7ec867': 0x7EC867 in flat,
            'writes_known_irq_destination_7ec868': 0x7EC868 in flat,
            'indexed_addresses_sha256': sha(address_bytes),
            'ordered_cpu_word_writes_sha256': sha(cpu_bytes),
            'contexts': result['contexts'], 'read_sites': result['read_sites'], 'steps': result['steps']}


def verify_case(read, q, s, frame_word, *, unknown_high=0, fill=0xA55A):
    return summarize(execute(read, q, s, frame_word, unknown_high=unknown_high, fill=fill),
                     q, s, frame_word, fill)


def pin_spans(read, spans):
    result = []
    for start, end, expected in spans:
        raw = read(start, end - start)
        require(type(raw) is bytes and len(raw) == end - start and sha(raw) == expected,
                f'canonical span drift ${start:06X}-${end:06X}')
        result.append({'start': f'${start:06X}', 'end_exclusive': f'${end:06X}',
                       'size': end - start, 'sha256': expected})
    return result


def preserved_copy_contract(previous):
    require(previous['schema'] == 'project-epoch-scene8b-copy-producers-v1', 'exact prerequisite schema')
    require(previous['q_alias_cases_unresolved'] == list(EXCLUDED_Q), 'preserve four alias refusals')
    half = [v for v in previous['producers'] if v['entry'] == '$CD347D']
    require(len(half) == 1 and half[0]['shape'] == 'half', 'unique half producer')
    post = half[0]['postcopy']
    require(post['entry'] == '$CD34F1' and post['termination_proved'] is False
            and post['memory_effects_proved'] is False, 'preserve earlier explicit open obligations')
    control = post['control']
    require(control['entry_m8'] is False and control['entry_x8'] is False
            and control['maximum_additional_bytes_below_callee_entry'] == 0
            and control['maximum_counted_bytes_including_root_call_frame'] == 2,
            'preserve typed width/near-frame contract')
    require(control['decoded_byte_intervals'] == [{'start': '$CD34F1', 'end_exclusive': '$CD352D',
                                                  'sha256': FILL_SPANS[0][2]}],
            'preserve exact earlier decoded span')
    return {'reference_sha256': PINS['copy_reference'][2], 'entry': '$CD347D',
            'continuation': '$CD34F1', 'earlier_termination_proved': False,
            'earlier_memory_effects_proved': False, 'reference_modified': False,
            'inherited_near_frame_bytes': 2, 'additional_stack_bytes': 0}


def reviewed_cpu_spans():
    recipes = (
        ('cpu_core', 29, 36, 'native instruction begins with 24-bit read/write mask'),
        ('cpu_shared', 374, 378, 'DBR-qualified absolute data address'),
        ('cpu_shared', 435, 454, 'word loads/stores and independently carried high byte'),
        ('cpu_shared', 506, 513, 'D-relative address and native direct-page addition'),
        ('cpu_shared', 580, 589, 'word register assignment and zero flag'),
        ('cpu_instructions', 35, 98, 'binary word ADC including carry and truncation'),
        ('cpu_instructions', 173, 226, 'BEQ/BNE consume current zero flag; relative branch'),
        ('cpu_instructions', 275, 284, 'SEP20 changes M without truncating X/Y'),
        ('cpu_instructions', 299, 302, 'INX calls increment helper'),
        ('cpu_instructions', 329, 332, 'index-width increment with word truncation'),
        ('cpu_instructions', 354, 386, 'CPX compares at X width and sets carry/zero'),
        ('cpu_instructions', 548, 554, 'AND at M width'),
        ('cpu_instructions', 578, 588, 'left shift carry and word truncation'),
        ('cpu_instructions', 626, 633, 'ASL accumulator at M width'),
        ('cpu_instructions', 915, 957, 'word data load/store selection'),
        ('cpu_instructions', 1058, 1081, 'TAX at X width and TDC transfers whole D'),
        ('cpu_instructions', 1173, 1185, 'absolute-X addition carries across bank boundary'),
        ('cpu_instructions', 1255, 1259, 'direct-page mode uses bank-zero address'),
        ('cpu_memory', 53, 68, 'WRAM banks 7E/7F and low-bank 0000..1FFF mirrors'),
    )
    result = []
    for key, first, last, role in recipes:
        path, _, _ = PINS[key]
        lines = (ROOT/path).read_bytes().splitlines(keepends=True)
        require(0 < first <= last <= len(lines), 'bounded CPU semantic span')
        result.append({'path': path, 'first_line': first, 'last_line_inclusive': last,
                       'sha256': sha(b''.join(lines[first-1:last])), 'role': role,
                       'interpretation': 'reviewer-derived over pinned source'})
    return result


def candidate_writer_evidence(read):
    spans = pin_spans(read, WRITER_SPANS)
    cells = []
    for command, cell, target in ((0x89, 0xCD16C7, 0xCD2FBC), (0x8A, 0xCD16C9, 0xCD2FED),
            (0x8B, 0xCD16CB, 0xCD2FB7), (0xAB, 0xCD170B, 0xCD24F3),
            (0xD3, 0xCD175B, 0xCD1A9C), (0xD4, 0xCD175D, 0xCD1A8B)):
        require(read(cell, 2) == (target & 65535).to_bytes(2, 'little'), 'exact command pointer cell')
        cells.append({'command': command, 'cell': f'${cell:06X}', 'target': f'${target:06X}',
                      'cell_sha256': sha(read(cell, 2))})
    pairs = [(r, s) for r in range(1, 128) for s in range(8, 213)]
    require(len(pairs) == 26035 and max(abs(r-s) for r, s in pairs) == 211, 'candidate bounded arithmetic relation')
    return {'status': 'reviewer-derived direct-writer candidate; not a proved rooted script chain',
            'source_spans': spans, 'command_cells': cells,
            'candidate': {'ordered_commands': ['$8A', '$AB', '$8B'],
                'slot0': {'initializer_parameter': '$20', 'ab_parameter_choices': ['$00', '$01'], 'draw_q': 0},
                'slot1': {'initializer_parameter': '$21', 'ab_parameter_choices': ['$80', '$81'], 'draw_q': 1},
                'chosen_r_inclusive': [1, 127], 'conditional_clamped_s_inclusive': [8, 212],
                'arithmetic_pairs_checked': len(pairs), 'maximum_abs_r_minus_s': 211,
                'requires': ['M8/X16/B0/D0/DBR7E at command entries and binary arithmetic.',
                    'Each command parameter is stable across its repeated reads.',
                    'The selected slot, r and s survive intervening commands, emitters and asynchronous effects.',
                    'The half-shape selector and matching final raw q are deliberately chosen.']},
            'counterexample': {'ordered_commands': ['$8A', '$89', '$8B'], 'q': 0, 'initial_r': 1,
                'initial_s': 1, 's_delta': 255, 'final_s': 0,
                'reason': '$89 computes min((old_s+delta)&255,211), so its upper clamp does not prove positivity.'},
            'other_direct_writes': ['$8A writes raw r/s and masks only its own index; it does not write q.',
                '$8B stores its own unmasked q at CAAA.',
                '$AB gives s8..212 only when its source parameter selects one of the just-clamped primary pairs.',
                '$D4 can saturate r to zero; $D3 uses a dynamic upper bound.',
                '$CD10B6 writes word CAAB/CAAC after AND00FF, leaving variable CAAB.',
                '$CD1F99 clears CAAA in the separate B5/B6 path, not this draw chain.'],
            'rooted_legal_script_proved': False, 'whole_wram_writer_census': False,
            'source_lifetime_proved': False, 'whole_emitter_memory_ownership_proved': False}


def audit(rom, replay_copy):
    require(type(rom) is bytes and len(rom) == 0x400000 and sha(rom) == ROM_SHA, 'canonical ROM identity')
    def read(pc, size):
        require(type(pc) is int and type(size) is int and size > 0
                and 0xC00000 <= pc < pc + size <= 0x1000000, 'bounded canonical read')
        return rom[pc-0xC00000:pc-0xC00000+size]
    spans = pin_spans(read, FILL_SPANS)
    rows = [verify_case(read, q, s, frame) for q in (0, 1) for frame in (0, 1) for s in range(256)]
    endpoint_cases = 0
    for q in (0, 1, 128, 129, 254, 255):
        for frame in (0, 1):
            for s in (0, 1, 224, 225, 226, 255):
                require(verify_case(read, q, s, frame, unknown_high=0)
                        == verify_case(read, q, s, frame, unknown_high=255), 'unknown-high projection differs')
                endpoint_cases += 1
    # This algebra is tied to the pinned LDA-word / AND0001 / ASL / TAX prefix.
    mask_pairs = 0
    for q in range(256):
        if q in EXCLUDED_Q:
            continue
        for high in range(256):
            require(((q | (high << 8)) & 1) * 2 == (q & 1) * 2, 'word-mask factorization')
            mask_pairs += 1
    require(all((word & 1) in (0, 1) for word in range(65536)), 'frame-word parity factorization')
    examples = []
    for q, r, s, frame in ((0, 1, 0, 0), (0, 2, 0, 0), (1, 1, 0, 1),
                          (0, 225, 225, 0), (1, 226, 226, 1), (0, 224, 224, 0)):
        count = r//2 + min(r, s) - max(r//2 + max(r, s) - 222, 0)
        require(abs(r-s) <= 222 and 0 <= count <= 222, 'copy-safe arithmetic witness')
        predecessor = replay_copy(read, q, r, s)
        require(predecessor['doubled_count'] == 2*count and predecessor['skipped'] == (count == 0),
                'actual pinned predecessor disagrees with witness formula')
        row = verify_case(read, q, s, frame)
        row.update(r=r, copy_pair_count=count, copy_skipped=predecessor['skipped'],
                   copy_pointer=predecessor['pointer'])
        examples.append(row)
    return {'schema': 'project-epoch-scene8b-half-fill-v1', 'evidence_level': 'verified-static',
            'canonical_rom': {'size': len(rom), 'sha256': ROM_SHA}, 'source_spans': spans,
            'local_interpretations': len(rows), 'matrix_sha256': sha(serial(rows)),
            'matrix_serialization': 'UTF-8/LF serial(list of complete compact summaries), q/frame/s order',
            'unknown_high_endpoint_pairs': endpoint_cases, 'additional_endpoint_interpretations': endpoint_cases*2,
            'word_mask_algebra_pairs': mask_pairs, 'frame_word_parity_inputs': 65536,
            'complete_instruction_contexts': sorted({tuple(c) for row in rows for c in row['contexts']}),
            'termination': {'recurrence': 'X_k=(2*(q&1)+4*k) mod 65536, target=2*(q&1)+4*s.',
                'first_test_after_store': True, 'period': 16384, 'positive_s_store_count': 's',
                'zero_s_store_count': 16384, 'zero_s_x_wraps': 1,
                'general_fixed_target_condition': 'A fixed target is reachable iff target-X0 is divisible by 4 modulo 65536; first positive solution is used.',
                'condition': 'DP45 stays fixed after setup; no asynchronous register/status/code mutation.'},
            'comparison_envelope': {'width': 0x380, 'meaning': 'distance between the two canonical fill bases; neither interval is an approved allocation',
                'indexed_writes_within_condition': '1<=s<=224 for either q parity and either frame parity'},
            'examples': examples, 'writer_candidate': candidate_writer_evidence(read),
            'known_irq_destination': {'reference_sha256': PINS['irq_reference'][2], 'site': '$CEEEB9',
                'bytes': ['$7EC867', '$7EC868'], 'claim': 'source-use overlap, not a proved concurrent runtime collision'},
            'premises': ['Native M16/X16, D0/DBR7E and binary arithmetic at CD34F1; DP47 is zero-extended s.',
                'The earlier emitter and optional copy return, retaining the accepted alias/input premises until this entry.',
                'DP45 is written twice during setup and remains fixed through the selected fill loop.',
                'Local physical stores cannot alias DP45/47/7C or BA00; asynchronous writers and live stack ownership remain separate.',
                'q is read once before the fill. A later own store to CAAA/CAAB does not change this local loop, but defeats stronger whole-path input-lifetime assumptions.'],
            'q_alias_cases_unresolved': list(EXCLUDED_Q), 'copy_packet_unchanged': True,
            'legal_game_input_domain_proved': False, 'whole_scene8b_closed': False,
            'effective_whole_path_alias_closure': False, 'native_execution': False,
            'production_approval': False, 'whole_nmi_bound': None}


def collect():
    pins = {key: identity(ROOT/path, digest, size) for key, (path, size, digest) in PINS.items()}
    own = [identity(ROOT/path) for path in (SOURCE, TESTS)]
    previous = json.loads((ROOT/PINS['copy_reference'][0]).read_bytes())
    preserved = preserved_copy_contract(previous)
    irq = json.loads((ROOT/PINS['irq_reference'][0]).read_bytes())
    irq_writes = [row for row in irq['irq_contract']['ordinary_cpu_write_contexts'] if row['pc'] == '$CEEEB9']
    require(len(irq_writes) == 1 and irq_writes[0]['mode'] == 'MVN'
            and irq_writes[0]['bus_addresses_in_write_order'][:2] == ['$7EC867', '$7EC868'],
            'exact known IRQ source-use destination')
    inherited = {}
    for item in previous['source_identities'] + previous['reused_underlying_source_identities'] + list(previous['prerequisites'].values()):
        path = item['path']
        require(not Path(path).is_absolute() and '..' not in Path(path).parts, 'bounded prerequisite path')
        require(path not in inherited or inherited[path] == item, 'consistent inherited identity')
        inherited[path] = item
    transitive = [identity(ROOT/path, item['sha256'], item['size']) for path, item in sorted(inherited.items())]
    tools_path = str(ROOT/'tools')
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)
    prior = importlib.import_module('audit_schala_scene8b_copy_producers_v1')
    require(Path(prior.__file__).resolve() == ROOT/PINS['copy_source'][0], 'exact pinned predecessor module')
    result = audit(ROM.read_bytes(), lambda read, q, r, s: prior.evaluate(read, 0xCD347D, q, r, s))
    result.update(prerequisites=pins, source_identities=own, reused_underlying_source_identities=transitive,
        preserved_copy_contract=preserved,
        reviewed_cpu_semantic_spans=reviewed_cpu_spans(),
        prerequisite_scope='Exact accepted copy source/tests/reference and declared transitive identities checked before/after; six selected canonical predecessor replays. No full prerequisite collector regeneration.',
        reviewed_cpu_semantics={'commit': '137ae7ce3bf3f539d007e2c4ef3cb3b6c97672a1',
            'interpretation': 'Reviewer-derived M16 ASL/ADC, X16 INX/CPX/flags, native direct-page and 24-bit absolute-X word stores; hashes identify source, not automatic semantics.'},
        reproduce=['python', '-B', SOURCE], serialization='UTF-8 indented JSON, LF, one trailing newline')
    require(own == [identity(ROOT/path) for path in (SOURCE, TESTS)], 'own source drift')
    require(pins == {key: identity(ROOT/path, digest, size) for key, (path, size, digest) in PINS.items()}, 'direct prerequisite drift')
    require(transitive == [identity(ROOT/path, item['sha256'], item['size']) for path, item in sorted(inherited.items())], 'transitive prerequisite drift')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Explicit metadata destination; default is binary UTF-8/LF stdout.')
    args = parser.parse_args()
    data = serial(collect())
    if args.output is None:
        sys.stdout.buffer.write(data)
    else:
        args.output.write_bytes(data)


if __name__ == '__main__':
    main()
