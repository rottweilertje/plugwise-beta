"""DataUpdateCoordinator for Plugwise."""
from datetime import timedelta
from typing import Any, NamedTuple

from plugwise import Smile
from plugwise.exceptions import PlugwiseException, XMLDataMissingError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

# pw-beta - for core compat should import DEFAULT_SCAN_INTERVAL
from .const import DOMAIN, LOGGER


class PlugwiseData(NamedTuple):
    """Plugwise data stored in the DataUpdateCoordinator."""

    gateway: dict[str, Any]
    devices: dict[str, dict[str, Any]]


class PlugwiseDataUpdateCoordinator(DataUpdateCoordinator[PlugwiseData]):
    """Class to manage fetching Plugwise data from single endpoint."""

    def __init__(
        self, hass: HomeAssistant, api: Smile, cooldown: float, interval: timedelta
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=api.smile_name or DOMAIN,
            # Core directly updates from const's DEFAULT_SCAN_INTERVAL
            update_interval=interval,  # pw-beta
            # Don't refresh immediately, give the device time to process
            # the change in state before we query it.
            request_refresh_debouncer=Debouncer(
                hass,
                LOGGER,
                cooldown=cooldown,
                immediate=False,
            ),
        )
        self.api = api

    async def _async_update_data(self) -> PlugwiseData:
        """Fetch data from Plugwise."""
        try:
            data = await self.api.async_update()
            LOGGER.debug("Plugwise %s updated", self.api.smile_name)
        except XMLDataMissingError as err:
            raise UpdateFailed(
                f"No XML data received for: {self.api.smile_name}"
            ) from err
        except PlugwiseException as err:
            raise UpdateFailed(f"Updated failed for: {self.api.smile_name}") from err
        LOGGER.debug("Data: %s", PlugwiseData(*data))
        return PlugwiseData(*data)
