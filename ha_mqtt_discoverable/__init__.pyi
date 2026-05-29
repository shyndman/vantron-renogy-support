from collections.abc import Callable
from typing import Any, Generic, TypeVar

from paho.mqtt.client import Client, MQTTMessageInfo

class DeviceInfo:
    name: str
    def __init__(
        self,
        *,
        name: str,
        model: str | None = ...,
        model_id: str | None = ...,
        manufacturer: str | None = ...,
        sw_version: str | None = ...,
        hw_version: str | None = ...,
        identifiers: list[str] | list[tuple[str, str]] | str | None = ...,
        connections: list[tuple[str, str]] | None = ...,
        configuration_url: str | None = ...,
        via_device: str | None = ...,
        serial_number: str | None = ...,
        suggested_area: str | None = ...,
    ) -> None: ...

class EntityInfo:
    name: str
    unique_id: str | None
    def __init__(self, **kwargs: Any) -> None: ...

EntityT = TypeVar("EntityT", bound=EntityInfo)

class Settings(Generic[EntityT]):
    class MQTT:
        host: str | None
        port: int | None
        client_name: str | None
        state_prefix: str
        def __init__(
            self,
            *,
            host: str | None = ...,
            port: int | None = ...,
            username: str | None = ...,
            password: str | None = ...,
            client_name: str | None = ...,
            use_tls: bool | None = ...,
            tls_key: str | None = ...,
            tls_certfile: str | None = ...,
            tls_ca_cert: str | None = ...,
            discovery_prefix: str = ...,
            state_prefix: str = ...,
            client: Client | None = ...,
        ) -> None: ...

    mqtt: MQTT
    entity: EntityT
    debug: bool
    manual_availability: bool
    def __init__(
        self,
        *,
        mqtt: MQTT,
        entity: EntityT,
        debug: bool = ...,
        manual_availability: bool = ...,
    ) -> None: ...

class Discoverable(Generic[EntityT]):
    state_topic: str
    config_topic: str
    def __init__(
        self,
        settings: Settings[EntityT],
        on_connect: Callable[..., object] | None = ...,
    ) -> None: ...
    def write_config(self) -> MQTTMessageInfo | None: ...

class Subscriber(Discoverable[EntityT], Generic[EntityT]): ...
