"""Config flow for the WB2 integration."""

from __future__ import annotations

import asyncio
from ipaddress import IPv4Address, ip_address, ip_network
import json
import logging
from typing import Any

from homeassistant.components.network import async_get_adapters
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .const import (
    CONF_DEVICE_NAME,
    CONF_MAC,
    CONF_TYPE,
    DEVICE_TYPE_SWITCH,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_TYPE,
    DOMAIN,
    MDNS_SERVICE_TYPE,
    SCAN_TIMEOUT,
    short_mac,
)
from .tcp_client import Wb2DeviceInfo, probe_device

_LOGGER = logging.getLogger(__name__)

MANUAL_OPTION = "manual"

MAX_SCAN_HOSTS = 254


async def _candidate_hosts(hass: HomeAssistant) -> list[str]:
    """Build a deduplicated list of candidate IPv4 hosts to probe."""
    hosts: list[str] = []
    seen: set[str] = set()
    try:
        adapters = await async_get_adapters(hass)
    except Exception as err:  # pragma: no cover
        _LOGGER.warning("Unable to read network adapters: %s", err)
        return hosts

    for adapter in adapters:
        if not adapter["enabled"]:
            continue
        for ip_info in adapter["ipv4"]:
            addr = ip_info["address"]
            prefix = ip_info.get("network_prefix", 24)
            try:
                net = ip_network(f"{addr}/{prefix}", strict=False)
            except (ValueError, TypeError):
                continue
            if net.prefixlen < 16:
                net = ip_network(f"{addr}/16", strict=False)
            last_offset = min(net.num_addresses - 2, MAX_SCAN_HOSTS)
            for offset in range(1, last_offset + 1):
                host = str(net[offset])
                if host not in seen:
                    seen.add(host)
                    hosts.append(host)
    return hosts


class Wb2ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WB2."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow."""
        self._scan_task: asyncio.Task[dict[str, Wb2DeviceInfo]] | None = None
        self._scan_found: dict[str, Wb2DeviceInfo] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step: scan the local network directly."""
        return await self.async_step_scan()

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer to scan the LAN for WB2 devices."""
        hosts = await _candidate_hosts(self.hass)
        if not hosts:
            return self.async_abort(reason="no_network")

        self._scan_task = self.hass.async_create_task(self._scan(hosts))
        return self.async_show_progress(
            step_id="scan_progress",
            progress_action="scanning_lan",
            progress_task=self._scan_task,
        )

    async def _scan(self, hosts: list[str]) -> dict[str, Wb2DeviceInfo]:
        """Probe candidate hosts concurrently, return {host: Wb2DeviceInfo}."""
        semaphore = asyncio.Semaphore(64)

        async def probe(host: str) -> tuple[str, Wb2DeviceInfo] | None:
            async with semaphore:
                info = await probe_device(host, DEFAULT_PORT, timeout=SCAN_TIMEOUT)
                if info is not None:
                    return host, info
            return None

        results = await asyncio.gather(*(probe(h) for h in hosts))
        return {
            host: info
            for host, info in (item for item in results if item is not None)
        }

    async def async_step_scan_progress(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Wait for the scan to finish and hand off to the result step."""
        if self._scan_task is None:
            return self.async_show_progress_done(next_step_id="scan_failed")

        if not self._scan_task.done():
            return self.async_show_progress(
                step_id="scan_progress",
                progress_action="scanning_lan",
                progress_task=self._scan_task,
            )

        if exception := self._scan_task.exception():
            _LOGGER.error("LAN scan failed: %s", exception)
            return self.async_show_progress_done(next_step_id="scan_failed")

        found = self._scan_task.result()
        if not found:
            return self.async_show_progress_done(next_step_id="no_devices_found")

        self._scan_found = found
        return self.async_show_progress_done(next_step_id="pick")

    async def async_step_scan_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Abort when the scan fails."""
        return self.async_abort(reason="scan_failed")

    async def async_step_no_devices_found(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show option to manually enter IP when no devices found."""
        if user_input is not None:
            return await self.async_step_manual()
        return self.async_show_form(
            step_id="no_devices_found",
            data_schema=vol.Schema(
                {
                    vol.Required("next"): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    value="manual",
                                    label="手动输入 IP 地址",
                                )
                            ]
                        )
                    ),
                }
            ),
        )

    async def async_step_pick(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show scan results or create an entry for a scanned device."""
        if CONF_HOST not in (user_input or {}):
            existing_hosts = {
                entry.data.get(CONF_HOST)
                for entry in self._async_current_entries()
            }
            options: list[SelectOptionDict] = [
                SelectOptionDict(
                    value=host,
                    label=f"{info.name} ({short_mac(info.mac) or host})",
                )
                for host, info in sorted((self._scan_found or {}).items())
                if host not in existing_hosts
            ]
            options.append(
                SelectOptionDict(value=MANUAL_OPTION, label="手动输入 IP 地址")
            )
            return self.async_show_form(
                step_id="pick",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_HOST): SelectSelector(
                            SelectSelectorConfig(options=options)
                        ),
                    }
                ),
            )
        host = user_input[CONF_HOST]
        if host == MANUAL_OPTION:
            return await self.async_step_manual()
        info = (self._scan_found or {}).get(host)
        return await self._create_entry(host, DEFAULT_PORT, info)

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manually enter the device address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            try:
                ip = ip_address(host)
                if not isinstance(ip, IPv4Address):
                    raise ValueError
            except ValueError:
                errors[CONF_HOST] = "invalid_ip"
            else:
                info = await probe_device(host, port, timeout=1.0)
                if info is not None:
                    return await self._create_entry(host, port, info)
                errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="manual",
                data_schema=self._manual_schema(host, port),
                errors=errors,
            )
        return self.async_show_form(
            step_id="manual", data_schema=self._manual_schema()
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery."""
        name = discovery_info.name
        host_ip = str(discovery_info.ip_address)
        props = discovery_info.properties
        port = int(props.get("port", DEFAULT_PORT))

        instance = name.split(".")[0]
        parts = instance.split("-", 2)
        dtype = parts[1] if len(parts) > 1 else DEFAULT_TYPE
        mac_suffix = parts[2] if len(parts) > 2 else ""

        for entry in self._async_current_entries():
            entry_host = entry.data.get(CONF_HOST)
            if entry_host == instance:
                return self.async_abort(reason="already_configured")
            entry_mac = entry.data.get(CONF_MAC, "")
            if mac_suffix and entry_mac and entry_mac.endswith(mac_suffix):
                return self.async_abort(reason="already_configured")

        await self.async_set_unique_id(mac_suffix)
        self._abort_if_unique_id_configured()

        self._discovery_info = {
            "host": instance,
            "host_ip": host_ip,
            "port": port,
            "type": dtype,
            "mac_suffix": mac_suffix,
            "instance": instance,
        }

        info = await probe_device(host_ip, port, timeout=1.0)
        if info and info.model and info.name:
            display_name = f"{info.model} {info.name}"
        elif info and info.model:
            display_name = info.model
        else:
            display_name = instance

        self.context["title_placeholders"] = {"name": display_name}
        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={"name": display_name},
        )

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm zeroconf discovery."""
        info_data = self._discovery_info
        if info_data is None:
            return self.async_abort(reason="cannot_connect")

        info = await probe_device(info_data["host_ip"], info_data["port"], timeout=1.0)
        if info is None:
            return self.async_abort(reason="cannot_connect")

        return await self._create_entry(
            info_data["host"], info_data["port"], info, host_ip=info_data["host_ip"]
        )

    @staticmethod
    def _manual_schema(host: str | None = None, port: int = DEFAULT_PORT) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_HOST, default=host or ""): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.TEXT)
                ),
                vol.Required(CONF_PORT, default=port): cv.positive_int,
            }
        )

    async def _create_entry(
        self, host: str, port: int, info: Wb2DeviceInfo | None = None,
        host_ip: str | None = None,
    ) -> ConfigFlowResult:
        for existing in self._async_current_entries():
            if (
                existing.data.get(CONF_HOST) == host
                and existing.data.get(CONF_PORT) == port
            ):
                return self.async_abort(reason="already_configured")
        mac = info.mac if info else None
        short = short_mac(mac)
        model = info.model if info else None
        dev_name = info.name if info and info.name else None
        default_name = DEFAULT_NAME
        if model and dev_name:
            title = f"{model} {dev_name}"
        elif model and short:
            title = f"{model} {short}"
        elif short:
            title = f"AI-Thinker {short}"
        else:
            title = f"AI-Thinker {host}"
        data = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_DEVICE_NAME: dev_name or default_name,
            CONF_MAC: mac,
            CONF_TYPE: DEFAULT_TYPE,
        }
        if host_ip:
            data["host_ip"] = host_ip
        entry = self.async_create_entry(title=title, data=data)
        return entry
