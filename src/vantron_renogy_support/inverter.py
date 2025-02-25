import asyncio
import asyncio.staggered
import functools
from enum import Enum

from aiomqtt import Client as MqttClient
from bleak import BleakClient
from bleak.backends.device import BLEDevice
from loguru import logger
from pydantic import BaseModel, NonNegativeFloat

from . import const
from .scanner import RenogyScanner
from .util.asyncio_util import periodic_task
from .util.ble_util import read_modbus_from_device
from .util.modbus_util import field_slice


class PowerSavingMode(str, Enum):
    forbid = "forbid"  # 0000
    enable = "enable"  # 0001
    dormancy = "dormancy"  # 0002


BYTES_TO_POWER_SAVING_MODE = {
    0x0000: PowerSavingMode.forbid,
    0x0001: PowerSavingMode.enable,
    0x0002: PowerSavingMode.dormancy,
}


class InverterInfo(BaseModel):
    battery_voltage: NonNegativeFloat
    input_voltage: NonNegativeFloat
    input_current: NonNegativeFloat

    output_voltage: NonNegativeFloat
    output_current: NonNegativeFloat
    output_frequency: NonNegativeFloat

    inverter_temperature: float

    # power_saving_mode: PowerSavingMode
    # beep_switch: bool
    # ng_bonding_enable: bool

    # OVER_VOLTS_PROTECTION
    # OVER_VOLTS_RESTORE
    # OVER_DISCHARGE_SHUTDOWN
    # LOW_VOLTS_WARNING
    # LOW_VOLTS_RESTORE


STATE_START_WORD = 0x0FA0
STATE_LEN = 7


async def request_inverter_info(
    client: BleakClient, response_queue: asyncio.Queue
) -> InverterInfo:
    read = functools.partial(
        read_modbus_from_device,
        client=client,
        response_queue=response_queue,
        write_characteristic=const.INVERTER_WRITE_CHARACTERISTIC,
        timeout=5.0,
    )
    state_bytes = await read(STATE_START_WORD, STATE_LEN)
    return parse_inverter_info(state_bytes)


def parse_inverter_info(state_bytes: bytes) -> InverterInfo:
    state_slice = functools.partial(
        field_slice, start_word=STATE_START_WORD, bytes=state_bytes
    )

    return InverterInfo(
        battery_voltage=round(int.from_bytes(state_slice(0x0FA5, 2)) * 0.1, 1),
        input_voltage=round(int.from_bytes(state_slice(0x0FA0, 2)) * 0.1, 2),
        input_current=round(int.from_bytes(state_slice(0x0FA1, 2)) * 0.01, 2),
        output_voltage=round(int.from_bytes(state_slice(0x0FA2, 2)) * 0.1, 2),
        output_current=round(
            int.from_bytes(state_slice(0x0FA3, 2), signed=True) * 0.01, 2
        ),
        output_frequency=int.from_bytes(state_slice(0x0FA4, 2)) * 0.01,
        inverter_temperature=int.from_bytes(state_slice(0x0FA6, 2), signed=True) * 0.1,
    )


async def write_to_mqtt(info: InverterInfo) -> None:
    logger.info(f"Writing update to MQTT: {info}")

    async with MqttClient(
        const.MQTT_HOST, identifier=const.MQTT_CLIENT, clean_session=True
    ) as client:
        await client.publish(
            const.INVERTER_MQTT_STATE_TOPIC,
            payload=info.model_dump_json(),
        )


async def run_from_single_ble_connection(client: BleakClient):
    response_queue: asyncio.Queue[bytes] = asyncio.Queue()

    async def on_notification(_, ntf_bytes: bytearray):
        logger.debug("on_notification")
        await response_queue.put(bytes(ntf_bytes))

    logger.debug(f"Starting notifications")
    await client.start_notify(
        const.INVERTER_NOTIFICATION_CHARACTERISTIC, callback=on_notification
    )

    await periodic_task(
        const.INVERTER_PUBLISH_INTERVAL, lambda: run_step(client, response_queue)
    )


async def run_step(client: BleakClient, response_queue: asyncio.Queue[bytes]):
    info = await request_inverter_info(client, response_queue)
    await write_to_mqtt(info)


async def run_inverter(scanner: RenogyScanner):
    while True:
        device = await scanner.inverter_device
        try:
            if device is None:
                logger.debug("Inverter not found during discovery")
                await asyncio.sleep(2.0)
                continue

            async with BleakClient(device) as client:
                logger.info(f"Connected to {device}")
                await run_from_single_ble_connection(client)
        except Exception:
            logger.exception("Exception occurred. Reconnecting...")
            await asyncio.sleep(2.0)
