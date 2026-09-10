"""TCP push server for receiving device-initiated reports."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntry
    from .coordinator import Wb2Coordinator

_LOGGER = logging.getLogger(__name__)

PUSH_PORT = 9101


class PushServer:
    """Singleton TCP server that receives push reports from devices."""

    _instance: PushServer | None = None

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._server: asyncio.Server | None = None
        self._coordinators: dict[str, Wb2Coordinator] = {}
        self._ip_map: dict[str, str] = {}  # ip -> entry_id

    @classmethod
    def get_instance(cls, hass: HomeAssistant) -> PushServer:
        if cls._instance is None:
            cls._instance = cls(hass)
        return cls._instance

    def register(self, entry: ConfigEntry) -> None:
        """Register a config entry for push updates. Maps IP -> coordinator."""
        entry_id = entry.entry_id
        host_ip = entry.data.get("host_ip", entry.data.get("host", ""))
        host = entry.data.get("host", "")
        if host_ip:
            self._ip_map[host_ip] = entry_id
        if host and host != host_ip:
            self._ip_map[host] = entry_id
        _LOGGER.debug("Registered push target: %s (ip=%s)", entry_id, host_ip)

    def unregister(self, entry: ConfigEntry) -> None:
        entry_id = entry.entry_id
        to_remove = [k for k, v in self._ip_map.items() if v == entry_id]
        for k in to_remove:
            del self._ip_map[k]

    def _coordinator_for_ip(self, ip: str) -> Wb2Coordinator | None:
        entry_id = self._ip_map.get(ip)
        if entry_id and entry_id in self.hass.data.get("ai_thinker_home", {}):
            return self.hass.data["ai_thinker_home"][entry_id]
        return None

    async def async_start(self) -> None:
        if self._server is not None:
            return
        try:
            self._server = await asyncio.start_server(
                self._handle_client, "0.0.0.0", PUSH_PORT
            )
            _LOGGER.info("Push server listening on port %d", PUSH_PORT)
        except OSError as err:
            _LOGGER.warning("Push server port %d already in use: %s", PUSH_PORT, err)

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        addr = writer.get_extra_info("peername")
        src_ip = addr[0] if addr else ""
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=5.0)
            if not line:
                return
            data = json.loads(line.decode())

            # Match by TCP source IP
            coordinator = self._coordinator_for_ip(src_ip)
            if coordinator:
                from .tcp_client import Wb2State

                state = Wb2State.from_dict(data)
                coordinator.async_set_updated_data(state)
                _LOGGER.debug("Push update from %s: %d entities",
                              src_ip, len(state.entities))
            else:
                _LOGGER.debug("Push from unknown IP %s", src_ip)
        except asyncio.TimeoutError:
            _LOGGER.debug("Push timeout from %s", addr)
        except Exception as exc:
            _LOGGER.debug("Push handler error from %s: %s", addr, exc)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except (ConnectionError, OSError):
                pass
