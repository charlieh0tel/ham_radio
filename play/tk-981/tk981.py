#!/usr/bin/python3


def read(path):
    with open(path, "rb") as file:
        return file.read()
    
CONTENTS=read("kpg49d_example.dat")

def memories(contents):
    start=0x330
    record_length=64
    max_records = 200
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
    raw = mem[1]<<8 | mem[0]
    if raw == 0xffff:
        return "none "
    elif raw > 0x2800:
        code = raw & 0x07FF
        pol =  "R" if raw & 0x8000 else "N"
        return f"{code:03o} {pol}"
    else:
        return "%5.1f" % (float(raw) / 10.)

print()
print()

for index, memory in enumerate(MEMORIES):
    name = memory[49:59].decode('ascii', errors='backslashreplace')
    down = freq(memory[35:39])
    up = freq(memory[39:43])
    tone = get_tone(memory[45:47])
    if ord(name[0]) == 0: continue
    if down < 0: continue
    print(f"{index:3} {down:7.3f} {up:7.3f} {tone} {name}")
    
