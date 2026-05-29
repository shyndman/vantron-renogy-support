from collections.abc import Callable
from typing import Any

from paho.mqtt.client import MQTTMessageInfo

from . import DeviceInfo, Discoverable, EntityInfo, Settings

class SensorInfo(EntityInfo):
    device: DeviceInfo | None
    def __init__(self, **kwargs: Any) -> None: ...

class BinarySensorInfo(EntityInfo):
    device: DeviceInfo | None
    def __init__(self, **kwargs: Any) -> None: ...

class Sensor(Discoverable[SensorInfo]):
    state_topic: str
    def __init__(
        self,
        settings: Settings[SensorInfo],
        on_connect: Callable[..., object] | None = ...,
    ) -> None: ...
    def write_config(self) -> MQTTMessageInfo | None: ...

class BinarySensor(Discoverable[BinarySensorInfo]):
    state_topic: str
    def __init__(
        self,
        settings: Settings[BinarySensorInfo],
        on_connect: Callable[..., object] | None = ...,
    ) -> None: ...
    def write_config(self) -> MQTTMessageInfo | None: ...
