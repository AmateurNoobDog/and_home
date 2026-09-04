"""TCP push server for receiving device-initiated reports."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
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

    @classmethod
    def get_instance(cls, hass: HomeAssistant) -> PushServer:
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls(hass)
        return cls._instance

    def register(self, mac: str, coordinator: Wb2Coordinator) -> None:
        """Register a coordinator for push updates by MAC address."""
        self._coordinators[mac.upper()] = coordinator
        _LOGGER.debug("Registered push target: %s", mac)

    def unregister(self, mac: str) -> None:
        """Unregister a coordinator."""
        self._coordinators.pop(mac.upper(), None)

    async def async_start(self) -> None:
        """Start the TCP push server (idempotent)."""
        if self._server is not None:
            return
        self._server = await asyncio.start_server(
            self._handle_client, "0.0.0.0", PUSH_PORT
        )
        _LOGGER.info("Push server listening on port %d", PUSH_PORT)

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle an incoming push connection from a device."""
        addr = writer.get_extra_info("peername")
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=5.0)
            if not line:
                return
            data = json.loads(line.decode())
            mac = data.get("mac", "").upper().replace("-", ":")
            coordinator = self._coordinators.get(mac)
            if coordinator:
                from .tcp_client import Wb2State

                state = Wb2State.from_dict(data)
                coordinator.async_set_updated_data(state)
                _LOGGER.debug(
                    "Push update from %s: motion=%s presence=%s",
                    mac,
                    state.motion,
                    state.presence,
                )
            else:
                _LOGGER.debug("Push from unknown device %s", mac)
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
