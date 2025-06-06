import os

import stringcase
from ha_mqtt_discoverable import DeviceInfo, Discoverable, Settings
from ha_mqtt_discoverable.sensors import (
    BinarySensor,
    BinarySensorInfo,
    Sensor,
    SensorInfo,
)

from .. import const
from ..charger import ChargingState


def json_field_access(field: str) -> str:
    return f"value_json.{field}"


def json_value(field: str) -> str:
    return f"{{{{{json_field_access(field)}}}}}"


def shunt_state_topic(_) -> str:
    return f"{const.SHUNT_MQTT_STATE_TOPIC}"


def charger_state_topic(_) -> str:
    return const.CHARGER_MQTT_STATE_TOPIC


def inverter_state_topic(_) -> str:
    return const.INVERTER_MQTT_STATE_TOPIC


def run():
    # Configure the required parameters for the MQTT broker
    mqtt_settings = Settings.MQTT(
        host=const.MQTT_HOST,
        client_name=const.MQTT_CLIENT,
        state_prefix=const.MQTT_SHUNT_STATE_TOPIC_PREFIX,
    )

    shunt_info = DeviceInfo(
        name="House Battery Shunt",
        identifiers=["RTMShunt30038000437"],
        model="Shunt 300",
        manufacturer="Renogy",
        connections=[("ble_mac", os.environ[const.ENV_SHUNT_BLE_ADDRESS])],
    )

    def shunt_infos(device_info: DeviceInfo):
        yield SensorInfo(
            name="Battery Current",
            device=device_info,
            device_class="current",
            unique_id=f"{device_info.name}.house_battery_current",
            unit_of_measurement="A",
            value_template=json_value("house_battery_current"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Battery Voltage",
            device=device_info,
            device_class="voltage",
            unique_id=f"{device_info.name}.house_battery_voltage",
            unit_of_measurement="V",
            value_template=json_value("house_battery_voltage"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Battery Power",
            device=device_info,
            device_class="power",
            unique_id=f"{device_info.name}.house_battery_power",
            unit_of_measurement="W",
            value_template=f"{{{{({json_field_access("house_battery_voltage")} | float) * ({json_field_access("house_battery_current")} | float)}}}}",
            suggested_display_precision=3,
            expire_after=60,
            force_update=True,
        )

        yield SensorInfo(
            name="Battery Temperature",
            device=device_info,
            device_class="temperature",
            unique_id=f"{device_info.name}.house_battery_temperature",
            unit_of_measurement="°C",
            value_template=json_value("house_battery_temperature"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Vehicle Battery Voltage",
            device=device_info,
            device_class="voltage",
            unique_id=f"{device_info.name}.alternator_voltage",
            unit_of_measurement="V",
            value_template=json_value("vehicle_battery_voltage"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Vehicle Battery Temperature",
            device=device_info,
            device_class="temperature",
            unique_id=f"{device_info.name}.vehicle_battery_temperature",
            unit_of_measurement="°C",
            value_template=json_value("vehicle_battery_temperature"),
            expire_after=60,
        )

    charger_info = DeviceInfo(
        name="House Battery Charger",
        identifiers=["RBC2125DS-21W"],
        model="IP67 DCDC Charger with MPTT",
        manufacturer="Renogy",
        connections=[("ble_mac", os.environ[const.ENV_CHARGER_BLE_ADDRESS])],
    )

    charger_problems_info = DeviceInfo(
        name="House Battery Charger: Problems Panel",
        identifiers=["RBC2125DS-21W-Problems"],
        model="IP67 DCDC Charger Problems Panel",
        via_device="RBC2125DS-21W",
        manufacturer="Renogy",
    )


    def charger_infos(device_info: DeviceInfo):
        yield SensorInfo(
            name="Charge Voltage",
            device=device_info,
            device_class="voltage",
            unit_of_measurement="V",
            unique_id=f"{device_info.name}.charge_voltage",
            value_template=json_value("charge_voltage"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Charge Current",
            device=device_info,
            device_class="current",
            unit_of_measurement="A",
            unique_id=f"{device_info.name}.charge_current",
            value_template=json_value("charge_current"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Charge Power",
            device=device_info,
            device_class="power",
            unit_of_measurement="W",
            unique_id=f"{device_info.name}.charge_power",
            value_template=json_value("charge_power"),
            force_update=True,
            expire_after=60,
        )

        yield SensorInfo(
            name="Starter Voltage",
            device=device_info,
            device_class="voltage",
            unit_of_measurement="V",
            unique_id=f"{device_info.name}.starter_voltage",
            value_template=json_value("starter_voltage"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Starter Current",
            device=device_info,
            device_class="current",
            unit_of_measurement="A",
            unique_id=f"{device_info.name}.starter_current",
            value_template=json_value("starter_current"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Starter Power",
            device=device_info,
            device_class="power",
            unit_of_measurement="W",
            unique_id=f"{device_info.name}.starter_power",
            value_template=json_value("starter_power"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Solar Voltage",
            device=device_info,
            device_class="voltage",
            unit_of_measurement="V",
            unique_id=f"{device_info.name}.solar_voltage",
            value_template=json_value("solar_voltage"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Solar Current",
            device=device_info,
            device_class="current",
            unit_of_measurement="A",
            unique_id=f"{device_info.name}.solar_current",
            value_template=json_value("solar_current"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Charger Temperature",
            device=device_info,
            device_class="temperature",
            unit_of_measurement="°C",
            unique_id=f"{device_info.name}.charger_temperature",
            value_template=json_value("charger_temperature"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Charging State",
            device=device_info,
            device_class="enum",
            options=[e.value for e in ChargingState],
            unique_id=f"{device_info.name}.charging_state",
            value_template=json_value("charging_state"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Days Operating",
            device=device_info,
            device_class="duration",
            unit_of_measurement="d",
            state_class="total",
            unique_id=f"{device_info.name}.total_operating_days",
            value_template=json_value("total_operating_days"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Total Over-Discharges",
            device=device_info,
            state_class="total",
            unique_id=f"{device_info.name}.total_overdischarges",
            value_template=json_value("total_overdischarges"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Total Full Charges",
            device=device_info,
            state_class="total",
            unique_id=f"{device_info.name}.total_full_charges",
            value_template=json_value("total_full_charges"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Total Full Charges",
            device=device_info,
            state_class="total",
            unique_id=f"{device_info.name}.total_full_charges",
            value_template=json_value("total_full_charges"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Total Charged Capacity",
            device=device_info,
            device_class=None,  # Electric charge
            unit_of_measurement="Ah",
            unique_id=f"{device_info.name}.total_charging_amp_hours",
            value_template=json_value("total_charging_amp_hours"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Total Charged Energy",
            device=device_info,
            device_class="energy",
            unit_of_measurement="kWh",
            unique_id=f"{device_info.name}.total_kwh_generated",
            value_template=json_value("total_kwh_generated"),
            expire_after=60,
        )

    def charger_problem_infos(device_info: DeviceInfo):
        for name in [
            "any_problem_detected",
            "charge_mosfet_short_circuit",
            "anti_reverse_mosfet_short_circuit",
            "solar_panel_reversely_connected",
            "solar_panel_point_over_voltage",
            "solar_panel_counter_current",
            "solar_input_over_voltage",
            "solar_input_short_circuit",
            "solar_input_over_power",
            "ambient_temperature_too_high",
            "charger_temperature_too_high",
            "load_over_power",
            "load_short_circuit",
            "battery_under_voltage",
            "battery_over_voltage",
            "battery_over_discharge",
        ]:
            field_name = name if name == "any_problem_detected" else f"problem_{name}"
            yield BinarySensorInfo(
                name=stringcase.titlecase(name),
                device=device_info,
                device_class="problem",
                unique_id=f"{device_info.name}.{field_name}",
                value_template=f"{{{{{{true: \"on\", false: \"off\"}}[{json_field_access(field_name)}] }}}}",
                expire_after=60,
            )


    inverter_info = DeviceInfo(
        name="Power Inverter",
        identifiers=["RIV1220PU-126-CA"],
        model="2000W Pure Sine Wave Inverter",
        manufacturer="Renogy",
        connections=[("ble_mac", os.environ[const.ENV_INVERTER_BLE_ADDRESS])],
    )

    def inverter_infos(device_info: DeviceInfo):
        yield SensorInfo(
            name="Input Voltage",
            device=device_info,
            device_class="voltage",
            unit_of_measurement="V",
            unique_id=f"{device_info.name}.input_voltage",
            value_template=json_value("input_voltage"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Input Current",
            device=device_info,
            device_class="current",
            unit_of_measurement="A",
            unique_id=f"{device_info.name}.input_current",
            value_template=json_value("input_current"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Output Voltage",
            device=device_info,
            device_class="voltage",
            unit_of_measurement="V",
            unique_id=f"{device_info.name}.output_voltage",
            value_template=json_value("output_voltage"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Output Current",
            device=device_info,
            device_class="current",
            unit_of_measurement="A",
            unique_id=f"{device_info.name}.output_current",
            value_template=json_value("output_current"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Output Frequency",
            device=device_info,
            device_class="frequency",
            unit_of_measurement="Hz",
            unique_id=f"{device_info.name}.output_frequency",
            value_template=json_value("output_frequency"),
            expire_after=60,
        )

        yield SensorInfo(
            name="Inverter Temperature",
            device=device_info,
            device_class="temperature",
            unit_of_measurement="°C",
            unique_id=f"{device_info.name}.inverter_temperature",
            value_template=json_value("inverter_temperature"),
            expire_after=60,
        )

    for info in shunt_infos(shunt_info):
        # Instantiate the sensor
        s = Sensor(
            settings=Settings(mqtt=mqtt_settings, entity=info),
            make_state_topic=shunt_state_topic,
        ).write_config()
        if s is not None:
            s.wait_for_publish()

    from itertools import chain
    charger_and_problem_infos = chain.from_iterable([charger_infos(charger_info), charger_problem_infos(charger_problems_info)])

    for info in charger_and_problem_infos:
        # Instantiate the sensor
        match info:
            case BinarySensorInfo():
                s = BinarySensor(
                    settings=Settings(mqtt=mqtt_settings, entity=info),
                    make_state_topic=charger_state_topic,
                )
            case SensorInfo():
                s = Sensor(
                    settings=Settings(mqtt=mqtt_settings, entity=info),
                    make_state_topic=charger_state_topic,
                )

        write_info = s.write_config()
        if write_info is not None:
            write_info.wait_for_publish()

    for info in inverter_infos(inverter_info):
        # Instantiate the sensor
        s = Sensor(
            settings=Settings(mqtt=mqtt_settings, entity=info),
            make_state_topic=inverter_state_topic,
        ).write_config()
        if s is not None:
            s.wait_for_publish()
