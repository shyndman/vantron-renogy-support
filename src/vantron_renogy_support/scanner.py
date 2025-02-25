from asyncio import timeout as async_timeout
from typing import Optional

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from loguru import logger


class RenogyScanner(BleakScanner):
    def __init__(
        self,
        *args,
        charger_ble_address: str,
        inverter_ble_address: str,
        shunt_ble_address: str,
        **kwargs,
    ):
        self.charger_ble_address = charger_ble_address.upper()
        self.inverter_ble_address = inverter_ble_address.upper()
        self.shunt_ble_address = shunt_ble_address.upper()
        super().__init__(*args, detection_callback=self.on_detection, **kwargs)

    def on_detection(self, device: BLEDevice, _):
        logger.trace(f"Detected: {device}")

    @property
    async def shunt_device(self) -> Optional[BLEDevice]:
        return await self._find_device(self.shunt_ble_address)

    @property
    async def charger_device(self) -> Optional[BLEDevice]:
        return await self._find_device(self.charger_ble_address)

    @property
    async def inverter_device(self) -> Optional[BLEDevice]:
        return await self._find_device(self.inverter_ble_address)

    async def _find_device(self, address: str) -> Optional[BLEDevice]:
        if address in self.discovered_devices_and_advertisement_data:
            return self.discovered_devices_and_advertisement_data[address][0]

        try:
            async with async_timeout(10.0):
                async for bd, ad in self.advertisement_data():
                    if bd.address == address:
                        return bd
        except:
            return None
