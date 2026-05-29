MIN_I16 = -0x8000


def parse_short(data: bytes | bytearray, addr: int) -> int:
    value = (data[addr] << 8) | data[addr + 1]
    return value - 0x10000 if value & 0x8000 else value


def parse_fixed_short_as_float(
    data: bytes | bytearray, addr: int, precision: int
) -> float:
    scale = 1
    for _ in range(precision):
        scale *= 10
    return float(parse_short(data, addr)) / scale


def parse_optional_temperature(data: bytes | bytearray, addr: int) -> float | None:
    raw = parse_short(data, addr)
    return None if raw == MIN_I16 else raw / 10.0
