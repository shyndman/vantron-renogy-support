import asyncio
import uuid

from bleak import BleakClient

from .modbus_util import build_read_request


async def read_modbus_from_device(
    start_word: int,
    word_len: int,
    client: BleakClient,
    write_characteristic: uuid.UUID,
    response_queue: asyncio.Queue[bytes],
    timeout: float = 2.0,
) -> bytes:
    print(f"Requesting 0x{start_word},{word_len}")
    await client.write_gatt_char(
        write_characteristic,
        build_read_request(start_word, word_len),
    )
    return (await asyncio.wait_for(response_queue.get(), timeout))[3:]
