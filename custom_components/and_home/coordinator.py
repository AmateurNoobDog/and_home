"""DataUpdateCoordinator for the AND Home integration."""

from __future__ import annotations

from datetime import timedelta
import logging
import time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, POLL_INTERVAL, PUSH_CHECK_INTERVAL
from .tcp_client import Wb2Client, Wb2DeviceInfo, Wb2State

_LOGGER = logging.getLogger(__name__)


class Wb2Coordinator(DataUpdateCoordinator[Wb2State]):
    """Coordinator for the AND Home device.

    Two modes:
    - Poll mode (offline_timeout == 0): polls get_state every POLL_INTERVAL.
    - Push-only mode (offline_timeout > 0): never polls after the initial
      refresh; data freshness is tracked from pushes/set responses. When data
      is older than offline_timeout, raises UpdateFailed so entities become
      unavailable until the next push arrives.
    """

    def __init__(self, hass: HomeAssistant, client: Wb2Client,
                 device_info: Wb2DeviceInfo) -> None:
        self.client = client
        self.device_info = device_info
        self._consecutive_failures: int = 0
        self._push_only = device_info.offline_timeout > 0
        self._last_data_ts: float | None = None

        if self._push_only:
            update_interval = timedelta(seconds=PUSH_CHECK_INTERVAL)
            _LOGGER.debug(
                "Push-only mode for %s (offline_timeout=%ds, check every %ds)",
                client.host, device_info.offline_timeout, PUSH_CHECK_INTERVAL,
            )
        else:
            update_interval = timedelta(seconds=POLL_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=1.0,
                immediate=True,
                function=None,
            ),
        )

    def async_set_updated_data(self, data: Wb2State) -> None:
        """Record freshness whenever new data arrives (push or set response)."""
        self._last_data_ts = time.monotonic()
        super().async_set_updated_data(data)

    async def _async_update_data(self) -> Wb2State:
        if self._push_only:
            return await self._async_update_push_only()
        return await self._async_update_poll()

    async def _async_update_push_only(self) -> Wb2State:
        # First refresh (setup): fetch initial state once.
        if self.data is None:
            try:
                state = await self.client.get_state()
                self._last_data_ts = time.monotonic()
                self._consecutive_failures = 0
                return state
            except Exception as err:
                self._consecutive_failures += 1
                label = self.device_info.name or self.client.host
                if self._consecutive_failures == 1:
                    _LOGGER.warning("Device %s offline: %s", label, err)
                raise UpdateFailed(str(err)) from err

        # Subsequent checks: no I/O, only staleness.
        offline_timeout = self.device_info.offline_timeout
        if self._last_data_ts is not None:
            age = time.monotonic() - self._last_data_ts
            if age < offline_timeout:
                return self.data
            _LOGGER.debug(
                "Device %s stale: no data for %.0fs (timeout %ds)",
                self.device_info.name or self.client.host,
                age, offline_timeout,
            )
        raise UpdateFailed(
            f"no push received for {offline_timeout}s"
        )

    async def _async_update_poll(self) -> Wb2State:
        try:
            state = await self.client.get_state()
            self._last_data_ts = time.monotonic()
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
