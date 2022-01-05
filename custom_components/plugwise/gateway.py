"""Plugwise network/gateway platform."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import voluptuous as vol
from plugwise.exceptions import InvalidAuthentication, PlugwiseException
from plugwise.smile import Smile

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    API,
    COORDINATOR,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
    GATEWAY,
    GATEWAY_PLATFORMS,
    PW_TYPE,
    SENSOR_PLATFORMS,
    SERVICE_DELETE,
    UNDO_UPDATE_LISTENER,
)
from .coordinator import PWDataUpdateCoordinator
from .models import PlugwiseEntityDescription

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry_gw(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Plugwise Smiles from a config entry."""
    websession = async_get_clientsession(hass, verify_ssl=False)

    # When migrating from Core to beta, add the username to ConfigEntry
    entry_updates = {}
    if CONF_USERNAME not in entry.data:
        data = {**entry.data}
        data.update({CONF_USERNAME: DEFAULT_USERNAME})
        entry_updates["data"] = data

    if entry_updates:
        hass.config_entries.async_update_entry(entry, **entry_updates)

    api = Smile(
        host=entry.data[CONF_HOST],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        timeout=30,
        websession=websession,
    )

    try:
        connected = await api.connect()
        if not connected:
            _LOGGER.error("Unable to connect to the Smile/Stretch")
            raise ConfigEntryNotReady
    except InvalidAuthentication:
        _LOGGER.error("Invalid username or Smile ID")
        return False
    except PlugwiseException as err:
        _LOGGER.error("Error while communicating to the Smile/Stretch")
        raise ConfigEntryNotReady from err
    except asyncio.TimeoutError as err:
        _LOGGER.error("Timeout while connecting to the Smile/Stretch")
        raise ConfigEntryNotReady from err

    # Migrate to a valid unique_id when needed
    if entry.unique_id is None:
        if api.smile_version[0] != "1.8.0":
            hass.config_entries.async_update_entry(entry, unique_id=api.smile_hostname)

    update_interval = timedelta(
        seconds=entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL[api.smile_type]
        )
    )

    coordinator = PWDataUpdateCoordinator(hass, api, update_interval)

    api.get_all_devices()
    await coordinator.async_config_entry_first_refresh()

    undo_listener = entry.add_update_listener(_update_listener)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        API: api,
        COORDINATOR: coordinator,
        PW_TYPE: GATEWAY,
        UNDO_UPDATE_LISTENER: undo_listener,
    }

    _LOGGER.debug("Gateway is %s", coordinator.data[0]["gateway_id"])
    _LOGGER.debug("Gateway software version is %s", api.smile_version[0])
    _LOGGER.debug("Appliances are %s", coordinator.data[1])
    s_m_thermostat = coordinator.data[0]["single_master_thermostat"]
    _LOGGER.debug("Single master thermostat = %s", s_m_thermostat)

    platforms = GATEWAY_PLATFORMS
    if s_m_thermostat is None:
        platforms = SENSOR_PLATFORMS

    async def delete_notification(self):
        """Service: delete the Plugwise Notification."""
        _LOGGER.debug("Service delete PW Notification called for %s", api.smile_name)
        try:
            deleted = await api.delete_notification()
            _LOGGER.debug("PW Notification deleted: %s", deleted)
        except PlugwiseException:
            _LOGGER.debug(
                "Failed to delete the Plugwise Notification for %s", api.smile_name
            )

    for component in platforms:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
        if component == Platform.CLIMATE:
            hass.services.async_register(
                DOMAIN, SERVICE_DELETE, delete_notification, schema=vol.Schema({})
            )

    return True


async def async_unload_entry_gw(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, GATEWAY_PLATFORMS
    )
    if unload_ok:
        hass.data[DOMAIN][entry.entry_id][UNDO_UPDATE_LISTENER]()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


class SmileGateway(CoordinatorEntity):
    """Represent Smile Gateway."""

    def __init__(
        self,
        coordinator,
        description: PlugwiseEntityDescription,
        dev_id,
        model,
        name,
        vendor,
        fw,
    ) -> None:
        """Initialise the gateway."""
        super().__init__(coordinator)

        entry = coordinator.config_entry
        gw_id = coordinator.data[0]["gateway_id"]
        self._attr_available = super().available
        self._attr_device_class = description.device_class
        self._attr_device_info = DeviceInfo(
            configuration_url=f"http://{entry.data[CONF_HOST]}",
            identifiers={(DOMAIN, dev_id)},
            manufacturer=vendor,
            model=model,
            name=f"Smile {coordinator.data[0]['smile_name']}",
            sw_version=fw,
        )
        self.entity_description = description

        if dev_id != gw_id:
            self._attr_device_info.update(
                name=name,
                via_device=(DOMAIN, gw_id),
            )

    async def async_added_to_hass(self):
        """Subscribe to updates."""
        self._async_process_data()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._async_process_data)
        )

    @callback
    def _async_process_data(self):
        """Interpret and process API data."""
        raise NotImplementedError
