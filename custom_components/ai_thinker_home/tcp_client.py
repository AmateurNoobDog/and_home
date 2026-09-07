"""Async TCP client for the WB2 JSON protocol."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import logging
import socket

_LOGGER = logging.getLogger(__name__)


@dataclass
class Wb2State:
    """Device state returned by the device."""

    r: int = 0
    g: int = 0
    b: int = 0
    brightness: int | None = None
    on: int | None = None
    on1: int | None = None
    on2: int | None = None
    motion: int | None = None
    presence: int | None = None
    push: int | None = None
    count: int | None = None
    mac: str | None = None
    type: str | None = None
    name: str | None = None
    model: str | None = None
    sw_version: str | None = None
    names: list[str] | None = None
    # Radar gate energy values (8 gates, 75cm each)
    g0: int | None = None
    g1: int | None = None
    g2: int | None = None
    g3: int | None = None
    g4: int | None = None
    g5: int | None = None
    g6: int | None = None
    g7: int | None = None
    # Debug counters
    scnt: int | None = None
    mcnt: int | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Wb2State":
        names = data.get("names")
        return cls(
            r=int(data.get("r", 0)),
            g=int(data.get("g", 0)),
            b=int(data.get("b", 0)),
            brightness=int(data["brightness"]) if "brightness" in data else None,
            on=int(data["on"]) if "on" in data else None,
            on1=int(data["on1"]) if "on1" in data else None,
            on2=int(data["on2"]) if "on2" in data else None,
            motion=int(data["motion"]) if "motion" in data else None,
            presence=int(data["presence"]) if "presence" in data else None,
            push=int(data["push"]) if "push" in data else None,
            count=int(data["count"]) if "count" in data else None,
            mac=data.get("mac"),
            type=data.get("type"),
            name=data.get("name"),
            model=data.get("model"),
            sw_version=data.get("sw_version"),
            names=names if isinstance(names, list) else None,
            g0=int(data["g0"]) if "g0" in data else None,
            g1=int(data["g1"]) if "g1" in data else None,
            g2=int(data["g2"]) if "g2" in data else None,
            g3=int(data["g3"]) if "g3" in data else None,
            g4=int(data["g4"]) if "g4" in data else None,
            g5=int(data["g5"]) if "g5" in data else None,
            g6=int(data["g6"]) if "g6" in data else None,
            g7=int(data["g7"]) if "g7" in data else None,
            scnt=int(data["scnt"]) if "scnt" in data else None,
            mcnt=int(data["mcnt"]) if "mcnt" in data else None,
        )

    def channel_state(self, channel: int) -> int | None:
        """Return the on/off state (0/1) for a relay channel."""
        if channel == 0:
            return self.on
        return getattr(self, f"on{channel}", None)


class Wb2Client:
    """Small async TCP client talking the WB2 JSON line protocol.

    The device closes idle connections after a few seconds, so every request
    opens a fresh connection instead of reusing a possibly-dead one.
    """

    def __init__(self, host: str, port: int, timeout: float = 3.0,
                 host_ip: str | None = None) -> None:
        self.host = host
        self.host_ip = host_ip
        self.port = port
        self.timeout = timeout
        self._lock = asyncio.Lock()

    async def _open_connection(self):
        """Open TCP connection with DNS fallback to cached IP."""
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

    async def get_state(self) -> Wb2State:
        data = await self._request('{"cmd":"get"}')
        return Wb2State.from_dict(data)

    async def set_state(
        self,
        *,
        r: int | None = None,
        g: int | None = None,
        b: int | None = None,
        brightness: int | None = None,
        on: bool | None = None,
        channel: int = 0,
    ) -> Wb2State:
        cmd: dict = {"cmd": "set"}
        if r is not None:
            cmd["r"] = r
        if g is not None:
            cmd["g"] = g
        if b is not None:
            cmd["b"] = b
        if brightness is not None:
            cmd["brightness"] = brightness
        if on is not None:
            key = "on" if channel == 0 else f"on{channel}"
            cmd[key] = int(on)
        data = await self._request(json.dumps(cmd))
        return Wb2State.from_dict(data)

    async def close(self) -> None:
        """No persistent connection to close; kept for API compatibility."""

    async def calibrate(self) -> dict:
        """Calibrate radar with current environment (no person)."""
        return await self._request('{"cmd":"calibrate"}')

    async def restore_defaults(self) -> dict:
        """Restore radar default parameters."""
        return await self._request('{"cmd":"restore"}')


async def probe_device(
    host: str, port: int, timeout: float = 0.3
) -> Wb2State | None:
    """Probe host for the WB2 JSON protocol, returning the device state."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
    except (OSError, asyncio.TimeoutError):
        return None
    try:
        writer.write(b'{"cmd":"get"}\n')
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        if not line:
            return None
        data = json.loads(line.decode())
        if not (
            isinstance(data, dict)
            and (
                all(k in data for k in ("r", "g", "b"))
                or "on" in data
                or "motion" in data
                or "presence" in data
            )
        ):
            return None
        return Wb2State.from_dict(data)
    except (OSError, asyncio.TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (ConnectionError, OSError):
            pass
