import asyncio
import functools
from enum import Enum

import annotated_types
from aiomqtt import Client as MqttClient
from bitarray import bitarray
from bleak import BleakClient
from loguru import logger
from pydantic import BaseModel, NonNegativeFloat, NonNegativeInt, Strict
from typing_extensions import Annotated

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

    charging_state: ChargingState

    total_operating_days: NonNegativeInt
    total_overdischarges: NonNegativeInt
    total_full_charges: NonNegativeInt
    total_charging_amp_hours: NonNegativeInt
    total_kwh_generated: NonNegativeFloat

    any_problem_detected: bool
    problem_charge_mosfet_short_circuit: bool # b30
    problem_anti_reverse_mosfet_short_circuit: bool # b29
    problem_solar_panel_reversely_connected: bool # b28
    problem_solar_panel_point_over_voltage: bool # b27
    problem_solar_panel_counter_current: bool # b26
    problem_solar_input_over_voltage: bool # b25
    problem_solar_input_short_circuit: bool # b24
    problem_solar_input_over_power: bool # b23
    problem_ambient_temperature_too_high: bool # b22
    problem_charger_temperature_too_high: bool # b21
    problem_load_over_power: bool # b20
    problem_load_short_circuit: bool # b19
    problem_battery_under_voltage: bool # b18
    problem_battery_over_voltage: bool # b17
    problem_battery_over_discharge: bool # b16


async def run_from_single_ble_connection(client: BleakClient):
    response_queue: asyncio.Queue[bytes] = asyncio.Queue()

    async def on_notification(_, ntf_bytes: bytearray):
        logger.trace(f"Received notification")
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
    fault_bits = bitarray()
    fault_bits.frombytes(status_slice(0x121, 4))

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

        any_problem_detected=fault_bits.any(),
        problem_charge_mosfet_short_circuit=bool(fault_bits[-15]),
        problem_anti_reverse_mosfet_short_circuit=bool(fault_bits[-14]),
        problem_solar_panel_reversely_connected=bool(fault_bits[-13]),
        problem_solar_panel_point_over_voltage=bool(fault_bits[-12]),
        problem_solar_panel_counter_current=bool(fault_bits[-11]),
        problem_solar_input_over_voltage=bool(fault_bits[-10]),
        problem_solar_input_short_circuit=bool(fault_bits[-9]),
        problem_solar_input_over_power=bool(fault_bits[-8]),
        problem_ambient_temperature_too_high=bool(fault_bits[-7]),
        problem_charger_temperature_too_high=bool(fault_bits[-6]),
        problem_load_over_power=bool(fault_bits[-5]),
        problem_load_short_circuit=bool(fault_bits[-4]),
        problem_battery_under_voltage=bool(fault_bits[-3]),
        problem_battery_over_voltage=bool(fault_bits[-2]),
        problem_battery_over_discharge=bool(fault_bits[-1]),

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


async def publish_charger_state(ble_address: str):
    while True:
        try:
            async with BleakClient(ble_address) as client:
                logger.info(f"Connected to {ble_address}")
                await run_from_single_ble_connection(client)
        except ConnectionError:
            logger.debug("Connection error occurred. Reconnecting…")
        except Exception:
            logger.exception("Exception occurred. Reconnecting…")
        finally:
            await asyncio.sleep(2.0)
