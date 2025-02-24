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
    input_volts: float
    input_current: float

    output_volts: float
    output_current: float
    output_frequency: float

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
    print(f"inverter: Requesting 0x{STATE_START_WORD},{STATE_LEN}")
    await client.write_gatt_char(
        const.INVERTER_WRITE_CHARACTERISTIC,
        make_read_request(STATE_START_WORD, STATE_LEN),
    )
    state_bytes = await response_queue.get()
    print(f"res: {binascii.hexlify(state_bytes, " ")}")

    return parse_inverter_info(state_bytes[3:])


def parse_inverter_info(state_bytes: bytes) -> InverterInfo:
    state_slice = functools.partial(field_slice, start_word=STATE_START_WORD)

    return InverterInfo(
        input_volts=int.from_bytes(state_bytes[state_slice(0x0FA0, 2)]) * 0.1,
        input_current=int.from_bytes(state_bytes[state_slice(0x0FA1, 2)]) * 0.01,
        output_volts=int.from_bytes(state_bytes[state_slice(0x0FA2, 2)]) * 0.1,
        output_current=int.from_bytes(state_bytes[state_slice(0x0FA3, 2)], signed=True)
        * 0.01,
        output_frequency=int.from_bytes(state_bytes[state_slice(0x0FA4, 2)]) * 0.01,
        inverter_temperature=int.from_bytes(state_bytes[state_slice(0x0FA6, 2)]) * 1.0,
    )


async def write_to_mqtt(info: InverterInfo):
    print(f"inverter: Writing data to MQTT: {info}")

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
        print("inverter: Adding notification to queue")
        await response_queue.put(bytes(ntf_bytes))

    print("inverter: Starting notifications")
    await client.start_notify(
        const.INVERTER_NOTIFICATION_CHARACTERISTIC, callback=on_notification
    )

    await periodic_task(
        const.INVERTER_PUBLISH_INTERVAL, lambda: run_step(client, response_queue)
    )


async def run_step(client: BleakClient, response_queue: asyncio.Queue[bytes]):
    info = await request_inverter_info(client, response_queue)
    await write_to_mqtt(info)


async def run_inverter(ble_device: BLEDevice):
    while True:
        try:
            async with BleakClient(ble_device.address) as client:
                print(f"inverter: Connected to {ble_device.address}")
                await run_from_single_ble_connection(client)
        except Exception as err:
            print(f"Error occurred: {err}")
            await asyncio.sleep(2.0)
