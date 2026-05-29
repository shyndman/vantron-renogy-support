import unittest

from ..inverter import PowerSavingMode, parse_inverter_info
from ..util.modbus_util import GetFieldBytes


class InverterParseTests(unittest.TestCase):
    def test_parse_inverter_info_reads_single_byte_flags(self) -> None:
        def build_slice(values: dict[int, bytes]) -> GetFieldBytes:
            def get_field(reg_word: int, len_bytes: int) -> bytes:
                value = values[reg_word]
                self.assertEqual(len(value), len_bytes)
                return value

            return get_field

        info = parse_inverter_info(
            state_slice=build_slice(
                {
                    0x0FA0: b"\x00\xc8",
                    0x0FA1: b"\x00\x64",
                    0x0FA2: b"\x00\xe6",
                    0x0FA3: b"\x00\x64",
                    0x0FA4: b"\x13\x88",
                    0x0FA5: b"\x00\xf0",
                    0x0FA6: b"\x00\xfa",
                }
            ),
            beep_switch_slice=build_slice({0x1005: b"\x01"}),
            ng_bonding_slice=build_slice({0x100E: b"\x00"}),
            power_saving_slice=build_slice({0x115E: b"\x00\x01"}),
        )

        self.assertEqual(info.power_saving_mode, PowerSavingMode.enable)
        self.assertTrue(info.beep_switch)
        self.assertFalse(info.ng_bonding_enable)
