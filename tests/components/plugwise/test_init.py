"""Tests for the Plugwise Climate integration."""
import asyncio
from unittest.mock import Mock

from homeassistant.components.plugwise.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from tests.common import AsyncMock, MockConfigEntry
from tests.components.plugwise.common import (
    async_init_integration_gw,
    async_init_integration_usb,
)

from plugwise.exceptions import (
    CirclePlusError,
    NetworkDown,
    PortError,
    StickInitError,
    TimeoutException,
    XMLDataMissingError,
)


async def test_smile_unauthorized(hass, mock_smile_unauth):
    """Test failing unauthorization by Smile."""
    entry = await async_init_integration_gw(hass, mock_smile_unauth)
    assert entry.state == ConfigEntryState.SETUP_ERROR


async def test_smile_error(hass, mock_smile_error):
    """Test server error handling by Smile."""
    entry = await async_init_integration_gw(hass, mock_smile_error)
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_smile_notconnect(hass, mock_smile_notconnect):
    """Connection failure error handling by Smile."""
    mock_smile_notconnect.connect.return_value = False
    entry = await async_init_integration_gw(hass, mock_smile_notconnect)
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_smile_timeout(hass, mock_smile_notconnect):
    """Timeout error handling by Smile."""
    mock_smile_notconnect.connect.side_effect = asyncio.TimeoutError
    entry = await async_init_integration_gw(hass, mock_smile_notconnect)
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_smile_adam_xmlerror(hass, mock_smile_adam):
    """Detect malformed XML by Smile in Adam environment."""
    mock_smile_adam.async_update.side_effect = XMLDataMissingError
    entry = await async_init_integration_gw(hass, mock_smile_adam)
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_unload_entry(hass, mock_smile_adam):
    """Test being able to unload an entry."""
    entry = await async_init_integration_gw(hass, mock_smile_adam)

    mock_smile_adam.async_reset = AsyncMock(return_value=True)
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.NOT_LOADED
    assert not hass.data[DOMAIN]


async def test_async_setup_entry_fail(hass):
    """Test async_setup_entry."""
    entry = MockConfigEntry(domain=DOMAIN, data={})

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.SETUP_ERROR


# USB Stick tests


async def test_stick_porterror(hass, mock_stick):
    """Test porterror failore for Stick."""
    mock_stick.return_value.connect = Mock(side_effect=(PortError))
    entry = await async_init_integration_usb(hass, mock_stick)
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_stick_stick_init_error(hass, mock_stick):
    """Test StickInitError failore for Stick."""
    mock_stick.return_value.initialize_stick = Mock(side_effect=(StickInitError))
    entry = await async_init_integration_usb(hass, mock_stick)
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_stick_network_down(hass, mock_stick):
    """Test NetworkDown failore for Stick."""
    mock_stick.return_value.initialize_stick = Mock(side_effect=(NetworkDown))
    entry = await async_init_integration_usb(hass, mock_stick)
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_stick_timeout_exception(hass, mock_stick):
    """Test NetworkDown failore for Stick."""
    mock_stick.return_value.initialize_stick = Mock(side_effect=(TimeoutException))
    entry = await async_init_integration_usb(hass, mock_stick)
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_stick_circleplus_exception(hass, mock_stick):
    """Test NetworkDown failore for Stick."""
    mock_stick.return_value.initialize_circle_plus = Mock(side_effect=(CirclePlusError))
    entry = await async_init_integration_usb(hass, mock_stick)
    assert entry.state == ConfigEntryState.SETUP_RETRY


async def test_unload_entry_stick(hass, mock_stick):
    """Test being able to unload a stick entry."""
    entry = await async_init_integration_usb(hass, mock_stick)

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.NOT_LOADED
    assert not hass.data[DOMAIN]
