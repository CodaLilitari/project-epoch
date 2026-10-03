"""Reviewed conditional source-derived structural envelope; no admission certificate.

No emulator, image emission or old collector is used. Sampled timing is only
a comparison; it contributes nothing to the structural execution envelope.
Counts both sides of each branch and all straight-line exit blocks, intentionally
overapproximating execution; exactly bounded source loops are expanded separately.
"""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIMARY_PINS = {'asm/schala_package_helper_v2_stack.asm': (8617, '7ee849f04444567ae6a67f5642edc0ec0b7ef09f41c7ea5f2b1773e6373fdb5f'), 'asm/original_snes_package_cartridge_v1.asm': (1151, '3cd5b800e57ec4085e5b706e3bc283be6e2d2d7fb79000c2741d5828819be15b'), 'tools/original_snes_package_fixtures_v1.py': (4761, 'b7911e1bea10bf9294e3ca4a896e203bd1d12aec03a33da137aa7caabcb10a60'), 'private/research/mesen_timing_api_2_1_1/SnesCpu.cpp': (3666, 'ea81ccb2b6093fdde5ff2d1bfbc4a4a88a596e39b841e94786f343c5974491b8'), 'private/research/mesen_timing_api_2_1_1/SnesCpu.Shared.h': (20483, 'dd84d0794c9588adfd28932659edb07a7b5b9d2d052fbcd4696925026237210f'), 'private/research/mesen_timing_api_2_1_1/SnesCpu.Instructions.h': (27673, '9b24ffaf04411f309a2d0b7899c6a883d64b146b42513cdbd850ba44f34649bd'), 'private/research/mesen_timing_api_2_1_1/SnesMemoryManager.cpp': (12100, '2f1e365d5a2b5e7f2bbfe61abf8ecf04c96760842e0ec68de2aa603118664d58'), 'private/research/mesen_timing_api_2_1_1/SnesPpu.cpp': (83153, '5f61ed7c8da25938b494a4d42b270109dd9500ea5d155130b6b69ff774458180')}
for relative, (size, digest) in PRIMARY_PINS.items():
    payload=(ROOT/relative).read_bytes()
    assert len(payload)==size and hashlib.sha256(payload).hexdigest()==digest, relative
SOURCE = ROOT / 'asm/schala_package_helper_v2_stack.asm'
EXPECTED_SOURCE = '7ee849f04444567ae6a67f5642edc0ec0b7ef09f41c7ea5f2b1773e6373fdb5f'
ROM = ROOT / 'private/test_runs/original_package_20260908_build1/original_package_test.sfc'
raw = SOURCE.read_bytes()
assert hashlib.sha256(raw).hexdigest() == EXPECTED_SOURCE
rom = ROM.read_bytes()
assert hashlib.sha256(rom).hexdigest() == '1e0788500ad4181fea0ed767eed48c9d8da0f52ce86fec27cc8107d29033621b'
assert hashlib.sha256(rom[0x410000:0x410241]).hexdigest() == '7242ff96f07e8d5ed9f0a994e474dbf3b49e7c2e576bd07d6536b6dfe3004f3b'
registry_rows = [tuple(int.from_bytes(rom[0x430000+i*16+j:0x430000+i*16+j+2], 'little')
                       for j in range(0,16,2)) for i in range(16)]
assert [r[0] for r in registry_rows] == [1]*4+[0]*12
assert [r[5] for r in registry_rows[:4]] == [2,2,1,1]
rows = []
labels = {}
active = False
for line_no, raw_line in enumerate(raw.decode().splitlines(), 1):
    line = raw_line.split(';')[0].strip()
    if line == 'EpochPackageHelperV2Stack_Start:': active = True
    if not active or not line: continue
    if line.endswith(':'):
        labels[line[:-1]] = len(rows)
        continue
    if line.startswith('%PH2_Require'):
        rows += [(line_no, 'BCC' if 'CarryClear' in line else 'BEQ', ''),
                 (line_no, 'BRL', '')]
        continue
    op, *operand = line.split(None, 1)
    rows.append((line_no, op, operand[0] if operand else ''))

def cost(row):
    """code bytes, data bytes, definite internal idles, optional idle/read slots.

    All admitted code/data/stack accesses are eight clocks by the exact address
    classes. IdleOrRead is conservatively charged eight, not six. Data operations
    use word width even where execution narrows M; encoded immediate widths remain
    exact. Native X=0 throughout, so absolute-X reads always have one idle.
    """
    _, fullop, operand = row
    op = fullop.split('.')[0]
    if op in ('PHP','PHB'): return (1,1,1,0)
    if op in ('PHA','PHX','PHY'): return (1,2,1,0)
    if op in ('PLP','PLB'): return (1,1,2,0)
    if op in ('PLA','PLX','PLY'): return (1,2,2,0)
    if op == 'JSR': return (3,2,1,0)
    if op == 'RTS': return (1,2,3,0)
    if op == 'JML': return (4,0,0,0)
    if op == 'BRL': return (3,0,1,0)
    if op in ('BCC','BCS','BEQ','BNE','BRA'): return (2,0,1,0)
    if op in ('REP','SEP'): return (2,0,1,0)
    if op == 'XBA': return (1,0,1,1)
    if op in ('CLC','SEC','CLD','TSC','TCS','TAX','TXA','TAY','INX','DEY'):
        return (1,0,0,1)
    if op in ('ASL','DEC','INC') and operand == 'A': return (1,0,0,1)
    if op not in ('LDA','LDX','LDY','STA','CMP','ADC','SBC','AND','ORA'):
        raise ValueError(row)
    if operand.startswith('#'):
        assert fullop.endswith(('.b','.w')), row
        return (2 if fullop.endswith('.b') else 3,0,0,0)
    if operand.endswith(',s'): return (2,2,1,0)
    if fullop.endswith('.l'): return (4,2,0,0)
    if fullop.endswith('.w'): return (3,2,1 if operand.endswith(',X') else 0,0)
    raise ValueError(row)

costs = [cost(row) for row in rows]
assert sum(x[0] for x in costs) == 577
def vector(indices, multiple=1):
    return [sum(costs[i][k] for i in indices)*multiple for k in range(4)]
def clocks(v): return 8*(v[0]+v[1]+v[3])+6*v[2]
def span(a,b): return set(range(labels[a],labels[b]))

preflight = span('.preflight','.validated')
search = span('.target_search','.target_missing')
publication = span('.publish_loop','.done')
count = span('EpochPackageHelperV2Stack_CountBits','EpochPackageHelperV2Stack_End')
# CountBits: LDX/LDY; ASL/BCC/INX/DEY/BNE; TXA/RTS.
assert [rows[i][1].split('.')[0] for i in sorted(count)] == ['LDX','LDY','ASL','BCC','INX','DEY','BNE','TXA','RTS']
count_list = sorted(count)
outside = set(range(len(rows))) - preflight - publication - count

results = {}
for name, comparisons in [('immutable_v3_all_paths',64),('generic_registry_32_targets',1024)]:
    parts = {
        'all_nonloop_blocks_once_including_mutually_exclusive_exits': vector(outside),
        'preflight_body_32_times_excluding_nested_search': vector(preflight-search,32),
        'target_search_iterations': vector(search,comparisons),
        'publication_body_16_times_including_unselected_body': vector(publication,16),
        'countbits_init_and_exit_twice': vector(count_list[:2]+count_list[-2:],2),
        'countbits_body_32_times': vector(count_list[2:-2],32),
        'entry_bridge_JML_008060': [4,0,0,0],
    }
    base = sum(clocks(v) for v in parts.values())
    # Refresh positions vary over <8 clocks between lines of at least 1360.
    # A deliberately weaker 1352-clock minimum spacing suffices. With at most
    # 1+ceil(T/1352) events and 40 clocks/event: T <= (B+80)*1352/(1352-40).
    elapsed = ((base+80)*1352+1311)//1312
    results[name] = {
        'parts': {k:{'vector_code_data_idle_optional':v,'clocks':clocks(v)} for k,v in parts.items()},
        'base_clocks':base,'including_dram_refresh_upper_bound':elapsed,
        'difference_below_observed_irq_entry_124904':124904-elapsed,
        'comparison_iterations_bound':comparisons,
    }
result={'schema':'project-epoch-helper-timing-envelope-v1',
    'evidence_level':'reviewed-conditional-static-model',
    'source_identities':{p:{'size_bytes':s,'sha256':h} for p,(s,h) in PRIMARY_PINS.items()},
    'original_cartridge':{'path':ROM.relative_to(ROOT).as_posix(),'size_bytes':len(rom),'sha256':hashlib.sha256(rom).hexdigest()},
    'assembled_helper':{'cpu_address':0x410000,'size_bytes':577,'sha256':hashlib.sha256(rom[0x410000:0x410241]).hexdigest()},
    'model_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'reproduce':['python','-B','tools/research_helper_timing_envelope_v1.py'],
    'production_approval':False, 'interrupt_exclusion_proved':False, 'dma_hdma_bounded':False,
    'status':'reviewed-structural-envelope-not-admission-certificate',
    'encoded_instruction_bytes':577,'source_instruction_rows':len(rows),
    'scope':'interrupt-free, no DMA/HDMA service, no memory corruption, fixed v3 entry SPs, entry bridge through final JML before tail opcode',
    'results':results}
sys.stdout.buffer.write((json.dumps(result,indent=2)+'\n').encode())
