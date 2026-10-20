"""Independent bounded encoder for the two original portrait helpers.

Asar independently assembles these same sources in the private build contract.
This module accepts only the instruction grammar actually authored here.
"""
import re

ROOTS = {'Pc07StatusPortraitTilesV1': (0x4A0000, 0x200),
         'Pc07StatusPortraitPaletteV1': (0x4A0200, 0x100)}
SIMPLE = {'php': 0x08, 'pha': 0x48, 'phx': 0xDA, 'phy': 0x5A, 'tdc': 0x7B,
          'phb': 0x8B, 'pla': 0x68, 'txa': 0x8A, 'tax': 0xAA, 'cld': 0xD8,
          'clc': 0x18, 'ply': 0x7A, 'plx': 0xFA, 'plp': 0x28, 'rtl': 0x6B, 'inx':0xE8}
BRANCH = {'beq': 0xF0, 'bne': 0xD0, 'bcc': 0x90, 'bcs': 0xB0, 'bra': 0x80, 'brl': 0x82}
IMMEDIATE = {'rep': (0xC2, 1), 'sep': (0xE2, 1), 'cmp.b': (0xC9, 1), 'cmp.w': (0xC9, 2),
             'and.b': (0x29, 1), 'and.w': (0x29, 2), 'lda.w': (0xA9, 2),
             'adc.b': (0x69, 1), 'cpx.w': (0xE0, 2), 'cpy.w': (0xC0, 2), 'ldx.w': (0xA2, 2)}


def encode(source):
    groups, name = {}, None
    for raw in source.splitlines():
        line = raw.split(';', 1)[0].strip()
        if not line:
            continue
        if line.endswith(':') and line[:-1] in ROOTS:
            name = line[:-1]
            if name in groups:
                raise ValueError('duplicate helper')
            groups[name] = []
        elif name is None:
            raise ValueError('source outside helper')
        else:
            groups[name].append(line)
    if set(groups) != set(ROOTS):
        raise ValueError('two exact helpers required')
    result = {}
    for name, lines in groups.items():
        base, reservation = ROOTS[name]
        labels, anonymous, operations, offset = {}, [], [], 0
        for index, line in enumerate(lines):
            if line == '+':
                anonymous.append((index, offset))
                continue
            if line.startswith('.') and ' ' not in line:
                if line in labels:
                    raise ValueError('duplicate local label')
                labels[line] = offset
                continue
            op, _, operand = line.partition(' ')
            operand = operand.strip()
            if op in SIMPLE and not operand:
                raw = bytes([SIMPLE[op]])
            elif op in BRANCH:
                raw = bytes([BRANCH[op]]) + bytes(2 if op == 'brl' else 1)
            elif op in IMMEDIATE and re.fullmatch(r'#\$[0-9A-F]+', operand):
                opcode, width = IMMEDIATE[op]
                raw = bytes([opcode]) + int(operand[2:], 16).to_bytes(width, 'little')
            elif op in ('lda.l', 'cmp.l', 'sta.l') and re.fullmatch(r'\$[0-9A-F]{6}(,x)?', operand):
                indexed = operand.endswith(',x')
                opcode = {('lda.l', False): 0xAF, ('lda.l', True): 0xBF,
                          ('cmp.l', False): 0xCF, ('sta.l', False): 0x8F, ('sta.l', True): 0x9F}.get((op, indexed))
                if opcode is None:
                    raise ValueError('unsupported indexed instruction')
                raw = bytes([opcode]) + int(operand[1:7], 16).to_bytes(3, 'little')
            elif op == 'inc.w' and re.fullmatch(r'\$[0-9A-F]{4}', operand):
                raw = bytes([0xEE]) + int(operand[1:], 16).to_bytes(2, 'little')
            elif op == 'mvn' and re.fullmatch(r'\$[0-9A-F]{2},\$[0-9A-F]{2}', operand):
                raw = bytes([0x54, int(operand[1:3], 16), int(operand[5:7], 16)])
            else:
                raise ValueError('unsupported authored instruction: ' + line)
            operations.append((index, offset, op, operand, raw, line))
            offset += len(raw)
        if not 0 < offset <= reservation:
            raise ValueError('helper exceeds named reservation')
        data, instructions = bytearray(), []
        for index, offset, op, operand, raw, line in operations:
            if op in BRANCH:
                target = next((position for label_index, position in anonymous if label_index > index), None) if operand == '+' else labels.get(operand)
                if target is None:
                    raise ValueError('unresolved branch')
                width = len(raw) - 1
                raw = raw[:1] + (target - offset - len(raw)).to_bytes(width, 'little', signed=True)
            data.extend(raw)
            instructions.append({'cpu': base+offset, 'source': line, 'bytes': raw.hex()})
        result[name] = {'cpu_start': base, 'data': bytes(data), 'instructions': instructions,
                        'source': name + ':\n' + '\n'.join(lines) + '\n'}
    return result
