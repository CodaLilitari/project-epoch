"""Deterministic BPS1 codec; no filesystem access or game-specific policy.

Format reference: byuu's public-domain BPS specification, retained at
https://github.com/Sir-Walrus/Flips/blob/master/bps_spec.md
Encoding is deliberately simple and stable, not an optimal patch-size search.
"""
from collections import Counter
import zlib


def number(value):
    if type(value) is not int or value < 0:
        raise ValueError('BPS integer must be nonnegative')
    out = bytearray()
    while True:
        low = value & 127
        value >>= 7
        if not value:
            out.append(low | 128)
            return bytes(out)
        out.append(low)
        value -= 1


def signed(value):
    return number((abs(value) << 1) | (value < 0))


def encode(source, target, metadata=b''):
    """Use same-offset source runs, source copies, literals and repeated-byte runs.

    Source searches occur at sixteen-byte literal intervals and choose the
    first matching source location. This bounds search cost and makes tie
    behavior explicit. Long expanded fill uses overlapping TargetCopy.
    """
    if any(type(x) is not bytes for x in (source, target, metadata)):
        raise ValueError('immutable bytes required')
    out = bytearray(b'BPS1' + number(len(source)) + number(len(target)) +
                    number(len(metadata)) + metadata)
    counts = Counter()
    lengths = Counter()
    literal = bytearray()
    pos = source_cursor = target_cursor = 0

    def action(kind, length, extra=b''):
        out.extend(number(((length - 1) << 2) | kind))
        out.extend(extra)
        counts[kind] += 1
        lengths[kind] += length

    def flush():
        if literal:
            action(1, len(literal), bytes(literal))
            literal.clear()

    while pos < len(target):
        if pos < len(source) and source[pos] == target[pos]:
            end = pos + 1
            limit = min(len(source), len(target))
            while end < limit and source[end] == target[end]:
                end += 1
            if end - pos >= 4:
                flush(); action(0, end - pos); pos = end
                continue
        if pos and target[pos] == target[pos - 1]:
            end = pos + 1
            while end < len(target) and target[end] == target[pos]:
                end += 1
            if end - pos >= 8:
                flush()
                action(3, end - pos, signed(pos - 1 - target_cursor))
                target_cursor = end - 1
                pos = end
                continue
        if len(literal) % 16 == 0 and pos + 16 <= len(target):
            match = source.find(target[pos:pos + 16])
            if match >= 0:
                length = 16
                limit = min(len(source) - match, len(target) - pos)
                while length < limit and source[match + length] == target[pos + length]:
                    length += 1
                flush(); action(2, length, signed(match - source_cursor))
                source_cursor = match + length
                pos += length
                continue
        literal.append(target[pos]); pos += 1
    flush()
    out.extend(zlib.crc32(source).to_bytes(4, 'little'))
    out.extend(zlib.crc32(target).to_bytes(4, 'little'))
    out.extend(zlib.crc32(out).to_bytes(4, 'little'))
    names = ('SourceRead', 'TargetRead', 'SourceCopy', 'TargetCopy')
    return bytes(out), {names[i]: {'actions': counts[i], 'output_bytes': lengths[i]}
                        for i in range(4)}


def apply(source, patch, *, maximum_target_size=0x800000):
    """Strict in-memory BPS reader, with bounds and all three footer CRCs."""
    if type(source) is not bytes or type(patch) is not bytes:
        raise ValueError('immutable bytes required')
    if len(patch) < 19 or patch[:4] != b'BPS1':
        raise ValueError('invalid BPS header')
    if zlib.crc32(patch[:-4]) != int.from_bytes(patch[-4:], 'little'):
        raise ValueError('patch CRC mismatch')
    if zlib.crc32(source) != int.from_bytes(patch[-12:-8], 'little'):
        raise ValueError('source CRC mismatch')
    offset, end = 4, len(patch) - 12

    def integer():
        nonlocal offset
        value, shift = 0, 1
        for _ in range(10):
            if offset >= end:
                raise ValueError('truncated BPS integer')
            digit = patch[offset]; offset += 1
            value += (digit & 127) * shift
            if digit & 128:
                return value
            shift <<= 7
            value += shift
        raise ValueError('oversized BPS integer')

    source_size, target_size, metadata_size = integer(), integer(), integer()
    if source_size != len(source) or target_size > maximum_target_size:
        raise ValueError('source length or target limit mismatch')
    if offset + metadata_size > end:
        raise ValueError('truncated metadata')
    metadata = patch[offset:offset + metadata_size]; offset += metadata_size
    result = bytearray()
    relative = [0, 0]
    records = Counter()
    while len(result) < target_size:
        token = integer(); kind, length = token & 3, (token >> 2) + 1
        if len(result) + length > target_size:
            raise ValueError('action exceeds declared target')
        records[kind] += length
        if kind == 0:
            start = len(result)
            if start + length > len(source):
                raise ValueError('SourceRead outside source')
            result.extend(source[start:start + length])
        elif kind == 1:
            if offset + length > end:
                raise ValueError('truncated literal')
            result.extend(patch[offset:offset + length]); offset += length
        else:
            encoded = integer()
            delta = -(encoded >> 1) if encoded & 1 else encoded >> 1
            index = kind - 2
            relative[index] += delta
            start = relative[index]
            if kind == 2:
                if start < 0 or start + length > len(source):
                    raise ValueError('SourceCopy outside source')
                result.extend(source[start:start + length])
            else:
                if start < 0 or start >= len(result):
                    raise ValueError('TargetCopy requires earlier output')
                # A bytewise reader intentionally permits overlap for RLE.
                for address in range(start, start + length):
                    result.append(result[address])
            relative[index] += length
    if offset != end:
        raise ValueError('unused bytes before footer')
    if zlib.crc32(result) != int.from_bytes(patch[-8:-4], 'little'):
        raise ValueError('target CRC mismatch')
    return bytes(result), {'metadata': metadata, 'source_size': source_size,
                           'target_size': target_size, 'action_output_bytes': dict(records)}
