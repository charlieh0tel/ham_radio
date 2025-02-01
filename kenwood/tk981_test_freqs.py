#!/usr/bin/python3

from decimal import Decimal
import sys

_TEST_FREQ_OFFSET=0x172
_TEST_FREQ_SIZE=10
_N_TEST_FREQS=10

_MEM_OFFSET=0x330
_MEM_SIZE=64
_N_MEMS=500

_FREQ_PLACES=[
    Decimal(1)/Decimal(100_000), # in memory order
    Decimal(1)/Decimal(1000),  
    Decimal(1)/Decimal(10),
    Decimal(10)]
_FREQ_QUANTIZE=Decimal("1.00000")


def read_bytes(path: str) -> bytes:
    with open(path, 'rb') as f:
        return f.read()

def write_bytes(path: str, buf: bytes):
    with open(path, 'wb') as f:
        return f.write(buf)

def bcd_hex_to_int(value: int) -> int:
    if not 0x00 <= value <= 0x99:
        raise ValueError()
    return (value >> 4) * 10 + (value & 0x0f)

def int_to_bcd_hex(value: int) -> int:
    if not 0 <= value <= 99:
        raise ValueError()
    return value // 10 << 4 | (value % 10)

def freq_mhz_from_bytes(buf) -> Decimal:
    assert len(buf) == 4
    result = Decimal(0)
    for offset, place in enumerate(_FREQ_PLACES):
        result += Decimal(bcd_hex_to_int(buf[offset])) * place
    assert result == result.quantize(_FREQ_QUANTIZE)
    return result


def freq_mhz_to_bytes(freq_mhz: Decimal) -> list:
    freq_mhz = freq_mhz.quantize(_FREQ_QUANTIZE)
    result=[]
    remainder_mhz = freq_mhz
    # Bytes in memory are small to large places.  Do the math in
    # reverse from large to small places and reverse the output to put
    # the bytes in the right order.
    for place in reversed(_FREQ_PLACES):
        v = remainder_mhz // place
        remainder_mhz -= v * place
        print(f"v={v} r={remainder_mhz}")
        result.append(int_to_bcd_hex(int(v)))
    return list(reversed(result))


def read_freq(dat: bytes, offset) -> Decimal:
    return freq_mhz_from_bytes(dat[offset:offset+4])

def write_freq(dat: bytes, offset, freq_mhz: Decimal):
    dat[offset:offset+4] = freq_mhz_to_bytes(freq_mhz)


def dump_mem_freqs(dat: bytes):
    print("memory freqs")
    offset = _MEM_OFFSET
    for i in range(_N_MEMS):
        try:
            rx = read_freq(dat, offset + 35)
            tx = read_freq(dat, offset + 39)
        except ValueError:
            print(f"{i:2d} --EMPTY--")
        else:
            print(f"{i:2d} {rx:.4f} {tx:.4f}")
        offset += _MEM_SIZE
            

def dump_test_freqs(dat: bytes):
    print("test freqs")
    offset = _TEST_FREQ_OFFSET
    for i in range(_N_TEST_FREQS):
        try:
            rx = read_freq(dat, offset)
            tx = read_freq(dat, offset + 4)
        except ValueError:
            print(f"{i:2d} --EMPTY--")
        else:            
            print(f"{i:2d} {rx:.4f} {tx:.4f}")
        offset += _TEST_FREQ_SIZE


def frob_test_freqs(dat: bytes):
    MY_TEST_FREQS=[(Decimal("902.00000"), Decimal("902.00000")),
                   (Decimal("910.00000"), Decimal("910.00000")),
                   (Decimal("915.00000"), Decimal("915.00000")),
                   (Decimal("920.00000"), Decimal("920.00000")),
                   (Decimal("924.00000"), Decimal("924.00000")),
                   (Decimal("928.00000"), Decimal("928.00000")),
                   #
                   (Decimal("902.01250"), Decimal("927.01250")),
                   (Decimal("927.01250"), Decimal("902.01250")),
                   (Decimal("902.07500"), Decimal("927.07500")),
                   (Decimal("927.07500"), Decimal("902.07500"))]
    offset = _TEST_FREQ_OFFSET
    dat = list(dat)
    for i, (rx, tx) in enumerate(MY_TEST_FREQS):
        write_freq(dat, offset, rx)
        write_freq(dat, offset + 4, tx)
        offset += _TEST_FREQ_SIZE
    return bytes(dat)

                   
def main(argv):
    assert 2 <= len(argv) <= 3, "Wrong number of arguments."
    
    path = argv[1]
    dat = read_bytes(path)

    if len(argv) == 3:
        out_path = argv[2]
        dat = frob_test_freqs(dat)
        write_bytes(out_path, dat)

    dump_test_freqs(dat)
    #dump_mem_freqs(dat)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
    
