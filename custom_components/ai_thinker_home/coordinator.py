"""DataUpdateCoordinator for the WB2 integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, POLL_INTERVAL
from .tcp_client import Wb2Client, Wb2DeviceInfo, Wb2State

_LOGGER = logging.getLogger(__name__)


class Wb2Coordinator(DataUpdateCoordinator[Wb2State]):
    """Coordinator polling the WB2 device and owning the TCP client."""

    def __init__(self, hass: HomeAssistant, client: Wb2Client,
                 device_info: Wb2DeviceInfo) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=POLL_INTERVAL),
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=1.0,
                immediate=True,
                function=None,
            ),
        )
        self.client = client
        self.device_info = device_info
        self.last_error: str | None = None

    async def _async_update_data(self) -> Wb2State:
        try:
            state = await self.client.get_state()
            self.last_error = None
            return state
        except Exception as err:
            self.last_error = str(err)
            raise UpdateFailed(f"Error communicating with WB2 device: {err}") from err

    def get_entity_def(self, entity_id: str):
        """Find entity definition by id."""
        for e in self.device_info.entities:
            if e.id == entity_id:
                return e
        return None

    async def async_calibrate(self) -> Wb2State:
        return await self.client.calibrate()

    async def async_restore_defaults(self) -> Wb2State:
        return await self.client.restore_defaults()

    async def async_push_update(self, state: Wb2State) -> None:
        """Accept a push update from the PushServer."""
        self.async_set_updated_data(state)
