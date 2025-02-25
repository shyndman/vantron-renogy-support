import asyncio
from datetime import datetime, timezone
from typing import Optional

from aiomqtt import Client as MqttClient
from bleak import BleakClient
from bleak.backends.device import BLEDevice
from loguru import logger
from pydantic import BaseModel, NonNegativeFloat

from . import const
from .scanner import RenogyScanner
from .util.asyncio_util import periodic_task

# Cheeky cheeky global state
raw_notification = None
notification_count = 0


async def read_from_ble_shunt(
    scanner: RenogyScanner, trigger_ble_reconnect: asyncio.Event
):
    ble_device = await scanner.shunt_device
    try:
        if ble_device is None:
            logger.warning("Shunt not found during discovery")
            raise ConnectionError()
        await read_from_single_shunt_connection(ble_device, trigger_ble_reconnect)
    except Exception:
        logger.exception("Error occurred")
        await asyncio.sleep(3.0)


async def read_from_single_shunt_connection(
    ble_device: BLEDevice, trigger_ble_reconnect: asyncio.Event
):
    async with BleakClient(ble_device) as client:
        logger.info(f"Connected to device at {ble_device}")

        def notification_handler(_, msg_bytes: bytearray):
            logger.trace(f"Notification received, {msg_bytes}")
            global raw_notification, notification_count

            if msg_bytes[0x03] == 0x19:
                raw_notification = (datetime.now(tz=timezone.utc), msg_bytes)
                notification_count += 1

        logger.debug("Starting notifications")
        await client.start_notify(
            const.SHUNT_NOTIFICATION_CHARACTERISTIC, notification_handler
        )
        await trigger_ble_reconnect.wait()
        trigger_ble_reconnect.clear()


class ShuntInfo(BaseModel):
    house_battery_current: float
    house_battery_voltage: NonNegativeFloat
    house_battery_temperature: Optional[float]
    vehicle_battery_voltage: Optional[NonNegativeFloat]
    vehicle_battery_temperature: Optional[float]


def parse_shunt_information(received_ts: datetime, notification_bytes: bytearray):
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
        logger.debug("MQTT: no data to write")
    elif ctx["last_write"] == notification_count:
        logger.debug("MQTT: no new data since last write. Triggering reconnect")
        trigger_ble_reconnect.set()
    else:
        ctx["last_write"] = notification_count

        received_ts, notification_bytes = raw_notification
        info = parse_shunt_information(received_ts, notification_bytes)
        logger.info(f"MQTT: Writing shunt update")
        logger.debug(info)

        async with MqttClient(
            const.MQTT_HOST, identifier=const.MQTT_CLIENT, clean_session=True
        ) as client:
            await client.publish(
                f"{const.SHUNT_MQTT_STATE_TOPIC}",
                payload=info.model_dump_json(),
            )


async def run(scanner: RenogyScanner):
    reconnect_trigger = asyncio.Event()
    async with asyncio.TaskGroup() as tg:
        tg.create_task(read_from_ble_shunt(scanner, reconnect_trigger))
        tg.create_task(mqtt_task(reconnect_trigger))
