import asyncio
import asyncio.staggered
import os

from bleak import BleakScanner
from loguru import logger


from .. import const
from ..charger import publish_charger_state
from ..inverter import publish_inverter_state
from ..shunt import publish_shunt_state


async def run_async():
    logger.info("Finding Renogy devices")
    shunt_address = assert_environment(const.ENV_SHUNT_BLE_ADDRESS)
    await BleakScanner.find_device_by_address(shunt_address)

    charger_address = assert_environment(const.ENV_CHARGER_BLE_ADDRESS)
    await BleakScanner.find_device_by_address(charger_address)

    inverter_address = assert_environment(const.ENV_INVERTER_BLE_ADDRESS)
    await BleakScanner.find_device_by_address(inverter_address)

    logger.info("Beginning device information publishing tasks")
    async with asyncio.TaskGroup() as tg:
        tg.create_task(publish_shunt_state(shunt_address))
        await asyncio.sleep(3.0)
        tg.create_task(publish_charger_state(charger_address))
        await asyncio.sleep(3.0)
        tg.create_task(publish_inverter_state(inverter_address))


def assert_environment(env_name: str) -> str:
    if env_name not in os.environ:
        raise AssertionError(f"{env_name} not found in environment")
    return os.environ[env_name]


def run():
    asyncio.run(run_async())
