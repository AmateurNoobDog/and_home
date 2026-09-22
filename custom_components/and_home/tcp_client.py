"""Async TCP client for the WB2 JSON protocol (v2 — entity-based)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import logging
import socket

_LOGGER = logging.getLogger(__name__)


@dataclass
class Wb2EntityDef:
    """Entity definition from get_device."""
    id: str
    type: str
    name: str = ""
    icon: str = ""
    action: str = ""
    device_class: str = ""
    unit: str = ""


@dataclass
class Wb2DeviceInfo:
    """Full device description returned by get_device."""
    mac: str = ""
    name: str = ""
    model: str = ""
    manufacturer: str = ""
    sw_version: str = ""
    entities: list[Wb2EntityDef] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Wb2DeviceInfo":
        raw_entities = data.get("entities", [])
        entities = []
        for e in raw_entities:
            if isinstance(e, dict) and "id" in e and "type" in e:
                entities.append(Wb2EntityDef(
                    id=e["id"],
                    type=e["type"],
                    name=e.get("name", ""),
                    icon=e.get("icon", ""),
                    action=e.get("action", ""),
                    device_class=e.get("device_class", ""),
                    unit=e.get("unit", ""),
                ))
        return cls(
            mac=data.get("mac", ""),
            name=data.get("name", ""),
            model=data.get("model", ""),
            manufacturer=data.get("manufacturer", ""),
            sw_version=data.get("sw_version", ""),
            entities=entities,
        )


@dataclass
class Wb2EntityState:
    """Single entity state from get_state or push."""
    id: str
    type: str
    data: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "Wb2EntityState":
        return cls(
            id=d.get("id", ""),
            type=d.get("type", ""),
            data={k: v for k, v in d.items() if k not in ("id", "type")},
        )


@dataclass
class Wb2State:
    """State response from get_state or push."""
    state: str = "online"
    entities: list[Wb2EntityState] = field(default_factory=list)

    def find_entity(self, entity_id: str) -> Wb2EntityState | None:
        for e in self.entities:
            if e.id == entity_id:
                return e
        return None

    @classmethod
    def from_dict(cls, data: dict) -> "Wb2State":
        raw = data.get("entities", [])
        entities = []
        if isinstance(raw, list):
            for e in raw:
                if isinstance(e, dict):
                    entities.append(Wb2EntityState.from_dict(e))
        # Handle single-entity push format (e.g. 433_gateway, key_sensor)
        if not entities and "id" in data and "type" in data:
            entities.append(Wb2EntityState.from_dict(data))
        return cls(
            state=data.get("state", "online"),
            entities=entities,
        )


class Wb2Client:
    """Async TCP client for the WB2 JSON line protocol (v2)."""

    def __init__(self, host: str, port: int, timeout: float = 3.0,
                 host_ip: str | None = None) -> None:
        self.host = host
        self.host_ip = host_ip
        self.port = port
        self.timeout = timeout
        self._lock = asyncio.Lock()

    async def _open_connection(self):
        try:
            return await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port), timeout=self.timeout
            )
        except socket.gaierror:
            if self.host_ip and self.host_ip != self.host:
                _LOGGER.debug("DNS failed for %s, trying fallback %s",
                              self.host, self.host_ip)
                return await asyncio.wait_for(
                    asyncio.open_connection(self.host_ip, self.port),
                    timeout=self.timeout,
                )
            raise

    async def _request(self, payload: str) -> dict:
        async with self._lock:
            reader, writer = await self._open_connection()
            try:
                writer.write((payload + "\n").encode())
                await writer.drain()
                line = await asyncio.wait_for(reader.readline(), timeout=self.timeout)
                if not line:
                    raise ConnectionError("empty response")
                return json.loads(line.decode())
            except (ConnectionError, OSError, asyncio.TimeoutError, json.JSONDecodeError):
                raise
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except (ConnectionError, OSError):
                    pass

    async def get_device(self) -> Wb2DeviceInfo:
        """Discover device info and entity definitions."""
        data = await self._request('{"cmd":"get_device"}')
        return Wb2DeviceInfo.from_dict(data)

    async def get_state(self) -> Wb2State:
        """Poll entity states."""
        data = await self._request('{"cmd":"get_state"}')
        return Wb2State.from_dict(data)

    async def set_state(self, *, entity_id: str, cmd: str = "set",
                        params: dict | None = None) -> Wb2State:
        """Send a command to the device."""
        cmd_dict: dict = {"cmd": cmd, "id": entity_id}
        if params:
            cmd_dict.update(params)
        data = await self._request(json.dumps(cmd_dict))
        return Wb2State.from_dict(data)

    async def send_cmd(self, cmd: str, entity_id: str = "") -> Wb2State:
        """Send a simple command (pair, reset, calibrate, restore)."""
        cmd_dict: dict = {"cmd": cmd}
        if entity_id:
            cmd_dict["id"] = entity_id
        data = await self._request(json.dumps(cmd_dict))
        return Wb2State.from_dict(data)


async def probe_device(
    host: str, port: int, timeout: float = 0.3
) -> Wb2DeviceInfo | None:
    """Probe host with get_device, returning device info + entity definitions."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
    except (OSError, asyncio.TimeoutError):
        return None
    try:
        writer.write(b'{"cmd":"get_device"}\n')
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        if not line:
            return None
        data = json.loads(line.decode())
        if not isinstance(data, dict) or "mac" not in data:
            return None
        return Wb2DeviceInfo.from_dict(data)
    except (OSError, asyncio.TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass
