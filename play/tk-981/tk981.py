#!/usr/bin/python3


def read(path):
    with open(path, "rb") as file:
        return file.read()
    
CONTENTS=read("kpg49d_example.dat")

def memories(contents):
    start=0x330
    record_length=32
    max_records=32 * 16
    return [contents[start + n * record_length:
                     start + (n + 1) * record_length]
            for n in range(max_records)]
    
MEMORIES = memories(CONTENTS)

#print(MEMORIES[0])

def freq(mem):
    assert len(mem) == 4
    bcd_digits = [mem[3] >> 4,
                  mem[3] & 0xf,
                  mem[2] >> 4,
                  mem[2] & 0xf,
                  mem[1] >> 4,
                  mem[1] & 0xf,
                  mem[0] >> 4,
                  mem[0] & 0xf]
    digits = [chr(48 + bcd_digit) for bcd_digit in bcd_digits]
    try:
        return float(''.join(digits[0:3]) + '.' + ''.join(digits[3:]))
    except:
        return -1


def get_tone(mem):
    assert len(mem) == 2
    raw = mem[1] << 8 | mem[0]
    if raw == 0xffff:
        return "none "
    elif raw > 0x2800:
        code = raw & 0x07FF
        pol =  "R" if raw & 0x8000 else "N"
        return f"D{code:03o}{pol}"
    else:
        return "%5.1f" % (float(raw) / 10.)

print()
print()

for index, memory in enumerate(MEMORIES):
    ffff = memory[1] << 8 | memory[0]
    assert ffff == 0xffff

    n = memory[2]
    if n == 0xff: continue
    if memory[4] != 0xff: 
        down = freq(memory[3:7])
        up = freq(memory[7:11])
        dtone = get_tone(memory[13:15])
        utone = get_tone(memory[15:17])
        name = memory[17:27].decode('ascii', errors='backslashreplace')
        print(f"{n:2} {down:8.4f} {up:8.4f} {dtone} {utone} {name}")
    else:
        group = memory[3]
        name = memory[5:15].decode('ascii', errors='backslashreplace')
        print(f"-- {n:2} {group:3} {name}")
        
