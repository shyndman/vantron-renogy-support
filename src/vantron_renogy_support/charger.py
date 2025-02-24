import asyncio
import binascii
import functools
from enum import Enum

import annotated_types
from aiomqtt import Client as MqttClient
from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from pydantic import BaseModel, Strict
from typing_extensions import Annotated

from vantron_renogy_support.util.asyncio_util import periodic_task

from . import const
from .util.modbus_util import field_slice, make_read_request


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
    charge_voltage: float
    charge_current: float
    charge_power: float

    starter_voltage: float
    starter_current: float
    starter_power: float

    solar_voltage: float
    solar_current: float

    charger_temperature: float
    battery_temperature: float

    total_operating_days: int
    total_overdischarges: int
    total_full_charges: int
    total_charging_amp_hours: int
    total_kwh_generated: float

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
    print(f"charger: Requesting 0x{STATE_START_WORD},{STATE_LEN}")
    await client.write_gatt_char(
        const.CHARGER_WRITE_CHARACTERISTIC,
        make_read_request(STATE_START_WORD, STATE_LEN),
    )
    state_bytes = await response_queue.get()
    # print(f"res: {binascii.hexlify(state_bytes, " ")}")

    print(f"charger: Requesting 0x{STATUS_START_WORD},{STATUS_LEN}")
    await client.write_gatt_char(
        const.CHARGER_WRITE_CHARACTERISTIC,
        make_read_request(STATUS_START_WORD, STATUS_LEN),
    )
    status_bytes = await response_queue.get()
    # print(f"res: {binascii.hexlify(status_bytes, " ")}")

    return parse_charger_info(state_bytes[3:], status_bytes[3:])


def parse_charger_info(state_bytes: bytes, status_bytes: bytes) -> ChargerInfo:
    state_slice = functools.partial(field_slice, start_word=STATE_START_WORD)
    status_slice = functools.partial(field_slice, start_word=STATUS_START_WORD)

    return ChargerInfo(
        charge_voltage=round(
            int.from_bytes(state_bytes[state_slice(0x101, 2)]) * 0.1, 2
        ),
        charge_current=int.from_bytes(state_bytes[state_slice(0x102, 2)]) * 0.01,
        charge_power=int.from_bytes(state_bytes[state_slice(0x109, 2)]) * 1.0,
        starter_voltage=int.from_bytes(state_bytes[state_slice(0x104, 2)]) * 0.1,
        starter_current=int.from_bytes(state_bytes[state_slice(0x105, 2)]) * 0.01,
        starter_power=int.from_bytes(state_bytes[state_slice(0x106, 2)]) * 1.0,
        solar_voltage=int.from_bytes(state_bytes[state_slice(0x107, 2)]) * 0.1,
        solar_current=int.from_bytes(state_bytes[state_slice(0x108, 2)]) * 0.01,
        charger_temperature=int.from_bytes(
            [state_bytes[state_slice(0x103, 2)][0]], signed=True
        ),
        battery_temperature=int.from_bytes(
            [state_bytes[state_slice(0x103, 2)][1]], signed=True
        ),
        charging_state=BYTE_TO_CHARGING_STATES[status_bytes[status_slice(0x120, 2)][1]],
        fault_bits=status_bytes[status_slice(0x121, 4)],
        total_operating_days=int.from_bytes(status_bytes[status_slice(0x115, 2)]),
        total_overdischarges=int.from_bytes(status_bytes[status_slice(0x116, 2)]),
        total_full_charges=int.from_bytes(status_bytes[status_slice(0x117, 2)]),
        total_charging_amp_hours=int.from_bytes(status_bytes[status_slice(0x118, 4)]),
        total_kwh_generated=int.from_bytes(status_bytes[status_slice(0x11C, 4)])
        * 0.001,
    )


async def write_to_mqtt(info: ChargerInfo):
    print(f"charger: Writing data to MQTT: {info}")

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
        print("charger: Adding notification to queue")
        await response_queue.put(bytes(ntf_bytes))

    print("charger: Starting notifications")
    await client.start_notify(
        const.CHARGER_NOTIFICATION_CHARACTERISTIC, callback=on_notification
    )

    await periodic_task(
        const.CHARGER_PUBLISH_INTERVAL, lambda: run_step(client, response_queue)
    )


async def run_step(client: BleakClient, response_queue: asyncio.Queue[bytes]):
    info = await request_charger_info(client, response_queue)
    await write_to_mqtt(info)


async def run_charger(ble_device: BLEDevice):
    while True:
        try:
            async with BleakClient(ble_device.address) as client:
                print(f"charger: Connected to {ble_device.address}")
                await run_from_single_ble_connection(client)
        except Exception as err:
            print(f"Error occurred: {err}")
            await asyncio.sleep(2.0)
