"""Strict source-only encoder for the bounded PC07 caster helper subset.

No ROM input, emulator, source-generated game bytes or image emitter. The
independent builder must cross-check these emitted components against Asar.
"""
import hashlib
import json
from pathlib import Path
import re

ROOTS = {'Pc07CasterApproachV1': 0x490100, 'Pc07CasterNormalV1': 0x490180,
         'Pc07CasterPathV1': 0x490200, 'Pc07CasterCriticalV1': 0x490280,
         'Pc07CasterSwingSoundV1': 0x490300}
SINGLE = {'php': 0x08, 'plp': 0x28, 'rtl': 0x6B}
BRANCH = {'bne': 0xD0, 'beq': 0xF0}
FORMS = {('cpx.w', '#'): (0xE0, 2), ('cmp.b', '#'): (0xC9, 1),
         ('lda.b', '#'): (0xA9, 1), ('lda.l', ''): (0xAF, 3),
         ('lda.l', ',x'): (0xBF, 3), ('sta.l', ''): (0x8F, 3),
         ('jml', ''): (0x5C, 3)}


def encode(source):
    result, active = {}, None
    for number, line in enumerate(source.splitlines(), 1):
        line = line.partition(';')[0].strip()
        if not line:
            continue
        if line.endswith(':'):
            label = line[:-1]
            if label in ROOTS:
                if active is not None or label in result:
                    raise ValueError('nested/duplicate routine')
                active = {'data': bytearray(), 'labels': {}, 'branches': [], 'instructions': [], 'cpu_start': ROOTS[label]}
                result[label] = active
            elif label.endswith('End') and active is not None:
                if label != next(reversed(result)) + 'End':
                    raise ValueError('wrong ending label')
                active = None
            elif active is not None and label.startswith('.'):
                if label in active['labels']:
                    raise ValueError('duplicate local label')
                active['labels'][label] = len(active['data'])
            else:
                raise ValueError(f'unsupported label at line {number}')
            continue
        if active is None:
            raise ValueError('instruction outside declared routine')
        offset, parts = len(active['data']), line.lower().split()
        if len(parts) == 1 and parts[0] in SINGLE:
            raw = bytes([SINGLE[parts[0]]])
        elif len(parts) == 2 and parts[0] in BRANCH:
            raw = bytes([BRANCH[parts[0]], 0])
            active['branches'].append((offset, parts[1]))
        elif len(parts) == 2:
            match = re.fullmatch(r'(#?)\$([0-9a-f]+)(,x)?', parts[1])
            if not match:
                raise ValueError('unsupported operand')
            marker = match[1] or match[3] or ''
            if (parts[0], marker) not in FORMS:
                raise ValueError('unsupported instruction form')
            opcode, size = FORMS[parts[0], marker]
            raw = bytes([opcode]) + int(match[2], 16).to_bytes(size, 'little')
        else:
            raise ValueError('unsupported syntax')
        active['data'].extend(raw)
        active['instructions'].append({'cpu': active['cpu_start'] + offset, 'bytes': len(raw), 'source_line': number, 'source': line})
    if active is not None or set(result) != set(ROOTS):
        raise ValueError('incomplete helper source')
    for name, record in result.items():
        for offset, label in record.pop('branches'):
            relative = record['labels'][label] - (offset + 2)
            if not -128 <= relative <= 127:
                raise ValueError('relative branch overflow')
            record['data'][offset + 1] = relative & 255
        record['data'] = bytes(record['data'])
        if len(record['data']) > 128:
            raise ValueError(f'{name} exceeds private candidate window')
    return result


def report(source_path):
    raw = Path(source_path).read_bytes()
    encoded = encode(raw.decode('utf-8'))
    return {'schema': 'epoch-caster-source-encoding-v1', 'source': {'path': str(source_path), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}, 'ROM_read_or_written': False,
            'components': {name: {**{k: v for k, v in row.items() if k != 'data'}, 'bytes': len(row['data']),
            'hex': row['data'].hex(), 'sha256': hashlib.sha256(row['data']).hexdigest()} for name, row in encoded.items()}}


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = report(args.source)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({name: {'bytes': row['bytes'], 'sha256': row['sha256']} for name, row in result['components'].items()}))
