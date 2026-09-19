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
        self._consecutive_failures: int = 0

    async def _async_update_data(self) -> Wb2State:
        try:
            state = await self.client.get_state()
            self._consecutive_failures = 0
            return state
        except Exception as err:
            self._consecutive_failures += 1
            label = self.device_info.name or self.client.host
            if self._consecutive_failures == 1:
                _LOGGER.warning("Device %s offline: %s", label, err)
            else:
                _LOGGER.debug(
                    "Device %s still offline (attempt %d)",
                    label, self._consecutive_failures,
                )
            raise UpdateFailed(str(err)) from err
