import asyncio
import asyncio.staggered
import os

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from loguru import logger

from ..scanner import RenogyScanner

from .. import const
from ..charger import run_charger
from ..inverter import run_inverter
from ..shunt import run as run_shunt


async def run_async():
    logger.info("Finding Renogy devices")

    assert_environment(const.ENV_CHARGER_BLE_ADDRESS)
    assert_environment(const.ENV_INVERTER_BLE_ADDRESS)
    assert_environment(const.ENV_SHUNT_BLE_ADDRESS)

    scanner = RenogyScanner(
        charger_ble_address=os.environ[const.ENV_CHARGER_BLE_ADDRESS],
        inverter_ble_address=os.environ[const.ENV_INVERTER_BLE_ADDRESS],
        shunt_ble_address=os.environ[const.ENV_SHUNT_BLE_ADDRESS],
    )

    async with scanner:
        # Give the scanner a few seconds to go at it
        logger.info("Scan for BLE devices")
        await asyncio.sleep(10.0)

        logger.info("Beginning device information publishing tasks")
        async with asyncio.TaskGroup() as tg:
            tg.create_task(run_shunt(scanner))
            tg.create_task(run_charger(scanner))
            tg.create_task(run_inverter(scanner))


def assert_environment(env_name: str):
    if env_name not in os.environ:
        raise AssertionError(f"{env_name} not found in environment")

def run():
    asyncio.run(run_async())
