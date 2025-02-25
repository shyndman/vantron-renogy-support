import asyncio
import functools
from enum import Enum
from loguru import logger

import annotated_types
from aiomqtt import Client as MqttClient
from bleak import BleakClient
from bleak.backends.device import BLEDevice
from pydantic import BaseModel, NonNegativeFloat, NonNegativeInt, Strict
from typing_extensions import Annotated

from vantron_renogy_support.scanner import RenogyScanner

from . import const
from .util.asyncio_util import periodic_task
from .util.ble_util import read_modbus_from_device
from .util.modbus_util import field_slice


class ChargingState(str, Enum):
    not_charging = "not_charging"  # 00
    bulk_stage = "bulk"  # 02
    equalization_stage = "equalization"  # 03
    boost_stage = "boost"  # 04
    float_stage = "float"  # 05
    current_limit = "current_limit"  # 06
    direct = "direct"  # 08


BYTE_TO_CHARGING_STATES = {
    0x0: ChargingState.not_charging,
    0x2: ChargingState.bulk_stage,
    0x3: ChargingState.equalization_stage,
    0x4: ChargingState.boost_stage,
    0x5: ChargingState.float_stage,
    0x6: ChargingState.current_limit,
    0x8: ChargingState.direct,
}


class ChargerInfo(BaseModel):
    charge_voltage: NonNegativeFloat
    charge_current: NonNegativeFloat
    charge_power: NonNegativeFloat

    starter_voltage: NonNegativeFloat
    starter_current: NonNegativeFloat
    starter_power: NonNegativeFloat

    solar_voltage: NonNegativeFloat
    solar_current: NonNegativeFloat

    charger_temperature: float
    battery_temperature: float

    total_operating_days: NonNegativeInt
    total_overdischarges: NonNegativeInt
    total_full_charges: NonNegativeInt
    total_charging_amp_hours: NonNegativeInt
    total_kwh_generated: NonNegativeFloat

    charging_state: ChargingState
    fault_bits: Annotated[
        bytes, Strict(), annotated_types.Len(min_length=4, max_length=4)
    ]


STATE_START_WORD = 0x101
STATE_LEN = 9
STATUS_START_WORD = 0x115
STATUS_LEN = 14


async def request_charger_info(
    client: BleakClient, response_queue: asyncio.Queue
) -> ChargerInfo:
    read = functools.partial(
        read_modbus_from_device,
        client=client,
        response_queue=response_queue,
        write_characteristic=const.CHARGER_WRITE_CHARACTERISTIC,
    )
    return parse_charger_info(
        state_bytes=await read(STATE_START_WORD, STATE_LEN),
        status_bytes=await read(STATUS_START_WORD, STATUS_LEN),
    )


def parse_charger_info(state_bytes: bytes, status_bytes: bytes) -> ChargerInfo:
    state_slice = functools.partial(
        field_slice, start_word=STATE_START_WORD, bytes=state_bytes
    )
    status_slice = functools.partial(
        field_slice, start_word=STATUS_START_WORD, bytes=status_bytes
    )

    return ChargerInfo(
        charge_voltage=round(int.from_bytes(state_slice(0x101, 2)) * 0.1, 2),
        charge_current=int.from_bytes(state_slice(0x102, 2)) * 0.01,
        charge_power=int.from_bytes(state_slice(0x109, 2)) * 1.0,
        starter_voltage=int.from_bytes(state_slice(0x104, 2)) * 0.1,
        starter_current=int.from_bytes(state_slice(0x105, 2)) * 0.01,
        starter_power=int.from_bytes(state_slice(0x106, 2)) * 1.0,
        solar_voltage=int.from_bytes(state_slice(0x107, 2)) * 0.1,
        solar_current=int.from_bytes(state_slice(0x108, 2)) * 0.01,
        charger_temperature=int.from_bytes([state_slice(0x103, 2)[0]], signed=True),
        battery_temperature=int.from_bytes([state_slice(0x103, 2)[1]], signed=True),
        charging_state=BYTE_TO_CHARGING_STATES[status_slice(0x120, 2)[1]],
        fault_bits=status_slice(0x121, 4),
        total_operating_days=int.from_bytes(status_slice(0x115, 2)),
        total_overdischarges=int.from_bytes(status_slice(0x116, 2)),
        total_full_charges=int.from_bytes(status_slice(0x117, 2)),
        total_charging_amp_hours=int.from_bytes(status_slice(0x118, 4)),
        total_kwh_generated=int.from_bytes(status_slice(0x11C, 4)) * 0.001,
    )


async def write_to_mqtt(info: ChargerInfo):
    logger.info(f"Writing data to MQTT: {info}")

    async with MqttClient(
        const.MQTT_HOST, identifier=const.MQTT_CLIENT, clean_session=True
    ) as client:
        await client.publish(
            const.CHARGER_MQTT_STATE_TOPIC,
            payload=info.model_dump_json(),
        )


async def run_from_single_ble_connection(client: BleakClient):
    response_queue: asyncio.Queue[bytes] = asyncio.Queue()

    async def on_notification(_, ntf_bytes: bytearray):
        logger.debug(f"on_notification")
        await response_queue.put(bytes(ntf_bytes))

    logger.debug("Starting notifications")
    await client.start_notify(
        const.CHARGER_NOTIFICATION_CHARACTERISTIC, callback=on_notification
    )

    await periodic_task(
        const.CHARGER_PUBLISH_INTERVAL, lambda: run_step(client, response_queue)
    )


async def run_step(client: BleakClient, response_queue: asyncio.Queue[bytes]):
    info = await request_charger_info(client, response_queue)
    await write_to_mqtt(info)


async def run_charger(scanner: RenogyScanner):
    while True:
        device = await scanner.charger_device
        try:
            if device is None:
                logger.debug("Charger not found during discovery")
                await asyncio.sleep(2.0)
                continue

            async with BleakClient(device) as client:
                logger.info(f"Connected to {device}")
                await run_from_single_ble_connection(client)
        except Exception:
            logger.exception("Exception occurred. Reconnecting...")
            await asyncio.sleep(2.0)
