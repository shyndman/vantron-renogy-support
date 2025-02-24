import asyncio
import asyncio.staggered

from bleak import BleakScanner
from bleak.backends.device import BLEDevice

from .. import const
from ..charger import run_charger
from ..inverter import run_inverter
from ..shunt import run as run_shunt


async def run_async():
    shunt_ble_device, charger_ble_device, inverter_ble_device = await find_ble_devices()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(run_shunt(shunt_ble_device))
        await asyncio.sleep(1.0)
        tg.create_task(run_charger(charger_ble_device))
        await asyncio.sleep(1.0)
        tg.create_task(run_inverter(inverter_ble_device))


async def find_ble_devices() -> tuple[BLEDevice, BLEDevice, BLEDevice]:
    shunt_ble_device = None
    charger_ble_device = None
    inverter_ble_device = None

    while shunt_ble_device is None:
        shunt_ble_device = await BleakScanner.find_device_by_address(
            const.SHUNT_ADDRESS
        )
        if shunt_ble_device is None:
            print(f"could not find device with address '{const.SHUNT_ADDRESS}'")
            print(f"trying again in 5 seconds")
            await asyncio.sleep(5.0)
            continue

    while charger_ble_device is None:
        charger_ble_device = await BleakScanner.find_device_by_address(
            const.CHARGER_ADDRESS
        )
        if charger_ble_device is None:
            print(f"could not find device with address '{const.CHARGER_ADDRESS}'")
            print(f"trying again in 5 seconds")
            await asyncio.sleep(5.0)
            continue

    while inverter_ble_device is None:
        inverter_ble_device = await BleakScanner.find_device_by_address(
            const.INVERTER_ADDRESS
        )
        if inverter_ble_device is None:
            print(f"could not find device with address '{const.INVERTER_ADDRESS}'")
            print(f"trying again in 5 seconds")
            await asyncio.sleep(5.0)
            continue

    return shunt_ble_device, charger_ble_device, inverter_ble_device


def run():
    asyncio.run(run_async())
