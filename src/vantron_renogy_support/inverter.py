import asyncio
import asyncio.staggered
import functools
from enum import Enum
from typing import Callable

from aiomqtt import Client as MqttClient
from bleak import BleakClient
from bleak.backends.device import BLEDevice
from loguru import logger
from pydantic import BaseModel, NonNegativeFloat

from . import const
from .util.asyncio_util import periodic_task
from .util.ble_util import read_modbus_from_device
from .util.modbus_util import GetFieldBytes, field_slice


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

    power_saving_mode: PowerSavingMode  # 115C0001
    beep_switch: bool  # 10050001
    ng_bonding_enable: bool  # 100E0001

    # over_volts_protection: float
    # over_volts_restore: float
    # over_volts_warning: float
    # over_volts_restore: float
    # over_discharge_shutdown


STATE_WORD_START = 0x0FA0
STATE_WORD_LEN = 7

BEEP_SWITCH_WORD_START = 0x1005
BEEP_SWITCH_WORD_LEN = 1

NG_BONDING_WORD_START = 0x100E
NG_BONDING_WORD_LEN = 1

POWER_SAVING_WORD_START = 0x115C
POWER_SAVING_WORD_LEN = 1


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

    return parse_inverter_info(
        functools.partial(
            field_slice,
            start_word=STATE_WORD_START,
            bytes=await read(STATE_WORD_START, STATE_WORD_LEN),
        ),
        functools.partial(
            field_slice,
            start_word=BEEP_SWITCH_WORD_START,
            bytes=await read(BEEP_SWITCH_WORD_START, BEEP_SWITCH_WORD_LEN),
        ),
        functools.partial(
            field_slice,
            start_word=NG_BONDING_WORD_START,
            bytes=await read(NG_BONDING_WORD_START, NG_BONDING_WORD_LEN),
        ),
        functools.partial(
            field_slice,
            start_word=POWER_SAVING_WORD_START,
            bytes=await read(POWER_SAVING_WORD_START, POWER_SAVING_WORD_LEN),
        ),
    )


def parse_inverter_info(
    state_slice: GetFieldBytes,
    beep_switch_slice: GetFieldBytes,
    ng_bonding_slice: GetFieldBytes,
    power_saving_slice: GetFieldBytes,
) -> InverterInfo:
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
        power_saving_mode=BYTES_TO_POWER_SAVING_MODE[
            int.from_bytes(power_saving_slice(0x115E, 2))
        ],
        beep_switch=beep_switch_slice(0x1005, 1) == 1,
        ng_bonding_enable=ng_bonding_slice(0x100E, 1) == 1,
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
        logger.trace("Notification received")
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


async def publish_inverter_state(ble_address: str):
    while True:
        try:
            async with BleakClient(ble_address) as client:
                logger.info(f"Connected to {ble_address}")
                await run_from_single_ble_connection(client)

        except ConnectionError:
            logger.debug(f"Failed to connect to {ble_address}. Reconnecting…")
        except Exception:
            logger.exception("Exception occurred. Reconnecting…")
        finally:
            await asyncio.sleep(30.0)
