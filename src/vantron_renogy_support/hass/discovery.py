import os
from itertools import chain

from ha_mqtt_discoverable import DeviceInfo, Settings
from ha_mqtt_discoverable.sensors import (
    BinarySensor,
    BinarySensorInfo,
    Sensor,
)

from .. import const
from .entities import (
    charger_infos,
    charger_problem_infos,
    charger_state_topic,
    inverter_infos,
    inverter_state_topic,
    shunt_infos,
    shunt_state_topic,
)


def add_discovery_topis():
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

    inverter_info = DeviceInfo(
        name="Power Inverter",
        identifiers=["RIV1220PU-126-CA"],
        model="2000W Pure Sine Wave Inverter",
        manufacturer="Renogy",
        connections=[("ble_mac", os.environ[const.ENV_INVERTER_BLE_ADDRESS])],
    )

    for info in shunt_infos(shunt_info):
        # Instantiate the sensor
        sensor = Sensor(settings=Settings(mqtt=mqtt_settings, entity=info))
        sensor.state_topic = shunt_state_topic(info)
        write_info = sensor.write_config()
        if write_info is not None:
            write_info.wait_for_publish()

    charger_and_problem_infos = chain.from_iterable(
        [charger_infos(charger_info), charger_problem_infos(charger_problems_info)]
    )

    for info in charger_and_problem_infos:
        # Instantiate the sensor
        if isinstance(info, BinarySensorInfo):
            sensor = BinarySensor(settings=Settings(mqtt=mqtt_settings, entity=info))
        else:
            sensor = Sensor(settings=Settings(mqtt=mqtt_settings, entity=info))

        sensor.state_topic = charger_state_topic(info)
        write_info = sensor.write_config()
        if write_info is not None:
            write_info.wait_for_publish()

    for info in inverter_infos(inverter_info):
        # Instantiate the sensor
        sensor = Sensor(settings=Settings(mqtt=mqtt_settings, entity=info))
        sensor.state_topic = inverter_state_topic(info)
        write_info = sensor.write_config()
        if write_info is not None:
            write_info.wait_for_publish()
