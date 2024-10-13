import io
import struct

def to_ablock_u16(values):
    with io.BytesIO() as b:
        n = len(values)
        b.write(struct.pack(">cch", b'#', b'A', n * 2))
        for value in values:
            b.write(value.to_bytes(2, 'big'))
        return b.getvalue()

@staticmethod
def from_ablock_u16(bytes):
    n = len(bytes)
    assert n >= 4
    (pound, cap_a, blen) = struct.unpack(">cch", bytes[0:4])
    assert pound == b'#'
    assert cap_a == b'A'
    assert blen == n - 4
    assert blen % 2 == 0
    return [int.from_bytes(bytes[i:i+2], byteorder='big')
            for i in range(4, n, 2)]

