import asyncio
import binascii
import math
from datetime import datetime, timezone
from typing import Optional, SupportsIndex

from aiomqtt import Client as MqttClient
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from pydantic import AwareDatetime, BaseModel, NonNegativeFloat, NonNegativeInt

from . import const
from .util.asyncio_util import periodic_task
from .util.datetime_util import seconds_ago

# Cheeky cheeky global state
raw_notification = None
notification_count = 0


async def read_from_ble_shunt(
    ble_device: BLEDevice, trigger_ble_reconnect: asyncio.Event
):
    while True:
        try:
            await read_from_single_shunt_connection(ble_device, trigger_ble_reconnect)
        except Exception as err:
            print(f"Error occurred: {err}")
            await asyncio.sleep(5.0)


async def read_from_single_shunt_connection(
    ble_device: BLEDevice, trigger_ble_reconnect: asyncio.Event
):
    async with BleakClient(ble_device.address) as client:
        print(f"Connected: {ble_device}")

        def notification_handler(_, msg_bytes: bytearray):
            global raw_notification, notification_count

            if msg_bytes[0x03] == 0x19:
                raw_notification = (datetime.now(tz=timezone.utc), msg_bytes)
                notification_count += 1

        print("Starting notifications")
        await client.start_notify(
            const.SHUNT_NOTIFICATION_CHARACTERISTIC, notification_handler
        )
        await trigger_ble_reconnect.wait()
        trigger_ble_reconnect.clear()


class ShuntInfo(BaseModel):
    # elapsed_ticks: NonNegativeInt
    # period_start_ts: AwareDatetime
    house_battery_current: float
    house_battery_voltage: NonNegativeFloat
    house_battery_temperature: Optional[float]
    vehicle_battery_voltage: Optional[NonNegativeFloat]
    vehicle_battery_temperature: Optional[float]
    # raw_hex_bytes: str


def parse_shunt_information(received_ts: datetime, notification_bytes: bytearray):
    # ticks = int.from_bytes(notification_bytes[0x12 : (0x13 + 1)])
    # start_ts = seconds_ago(seconds=ticks, ts=received_ts)
    # We round the calculated start time so that it remains constant during
    # the period
    # rounded_start_ts = start_ts.replace(
    #     minute=math.ceil(start_ts.minute / 10) * 10, second=0
    # )

    vehicle_battery_voltage = (
        int.from_bytes(notification_bytes[0x1E : (0x1F + 1)]) / 1000
    )
    return ShuntInfo(
        house_battery_current=int.from_bytes(
            notification_bytes[0x16 : (0x17 + 1)], signed=True
        )
        / 1000,
        house_battery_voltage=int.from_bytes(notification_bytes[0x1A : (0x1B + 1)])
        / 1000,
        house_battery_temperature=parse_optional_temperature(notification_bytes, 0x42),
        vehicle_battery_voltage=(
            vehicle_battery_voltage if vehicle_battery_voltage != 0.0 else None
        ),
        vehicle_battery_temperature=parse_optional_temperature(
            notification_bytes, 0x46
        ),
        # elapsed_ticks=ticks,
        # raw_hex_bytes=str(binascii.hexlify(notification_bytes)),
        # period_start_ts=rounded_start_ts,
        # another_time=int.from_bytes(notification_bytes[0x6C : (0x6D + 1)]),
    )


def parse_optional_temperature(barr: bytearray, i: int) -> Optional[float]:
    raw = int.from_bytes(barr[i : (i + 2)], signed=True)
    return None if raw == const.MIN_I16 else raw / 10


async def mqtt_task(trigger_ble_reconnect):
    ctx = {
        "last_write": -1,
    }
    await periodic_task(
        const.MQTT_WRITE_INTERVAL,
        write_shunt_data,
        ctx=ctx,
        trigger_ble_reconnect=trigger_ble_reconnect,
    )


async def write_shunt_data(ctx: dict, trigger_ble_reconnect: asyncio.Event):
    global raw_notification, notification_count

    if raw_notification is None:
        print("MQTT: no data to write")
    elif ctx["last_write"] == notification_count:
        print("MQTT: no new data since last write. Triggering reconnect")
        trigger_ble_reconnect.set()
    else:
        print(f"Writing shunt data: {notification_count}")
        ctx["last_write"] = notification_count

        received_ts, notification_bytes = raw_notification
        info = parse_shunt_information(received_ts, notification_bytes)

        async with MqttClient(
            const.MQTT_HOST, identifier=const.MQTT_CLIENT, clean_session=True
        ) as client:
            await client.publish(
                f"{const.MQTT_SHUNT_STATE_TOPIC_PREFIX}/shunt/state",
                payload=info.model_dump_json(),
            )


async def run(ble_device: BLEDevice):
    reconnect_trigger = asyncio.Event()
    async with asyncio.TaskGroup() as tg:
        tg.create_task(read_from_ble_shunt(ble_device, reconnect_trigger))
        tg.create_task(mqtt_task(reconnect_trigger))
