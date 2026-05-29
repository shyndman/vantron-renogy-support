import unittest

from ..parse import (
    MIN_I16,
    parse_fixed_short_as_float,
    parse_optional_temperature,
    parse_short,
)


class ParseTests(unittest.TestCase):
    def test_parse_short_reads_signed_big_endian_words(self) -> None:
        self.assertEqual(parse_short(b"\x7f\xff", 0), 32767)
        self.assertEqual(parse_short(b"\x80\x00", 0), MIN_I16)
        self.assertEqual(parse_short(bytearray(b"\x00\xff\x9c"), 1), -100)

    def test_parse_fixed_short_as_float_scales_precision(self) -> None:
        self.assertEqual(parse_fixed_short_as_float(b"\x12\x34", 0, 2), 46.6)

    def test_parse_optional_temperature_uses_sentinel(self) -> None:
        self.assertIsNone(parse_optional_temperature(b"\x80\x00", 0))
        self.assertEqual(parse_optional_temperature(b"\x00\xfb", 0), 25.1)
