"""Tests for the Plugwise binary_sensor integration."""

from unittest.mock import MagicMock

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

# from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry


async def test_anna_climate_binary_sensor_entities(
    hass: HomeAssistant, mock_smile_anna: MagicMock, init_integration: MockConfigEntry
) -> None:
    """Test creation of climate related binary_sensor entities."""
    entity_id = "binary_sensor.opentherm_secondary_boiler_state"
    # Test disabled_by default entry
    assert hass.states.get(entity_id) is None

    state = hass.states.get("binary_sensor.opentherm_dhw_state")
    assert state
    assert state.state == STATE_OFF

    state = hass.states.get("binary_sensor.opentherm_heating")
    assert state
    assert state.state == STATE_ON

    state = hass.states.get("binary_sensor.opentherm_cooling")
    assert state
    assert state.state == STATE_OFF

    state = hass.states.get("binary_sensor.opentherm_compressor_state")
    assert state
    assert state.state == STATE_ON


async def test_anna_climate_binary_sensor_change(
    hass: HomeAssistant, mock_smile_anna: MagicMock, init_integration: MockConfigEntry
) -> None:
    """Test change of climate related binary_sensor entities."""
    hass.states.async_set("binary_sensor.opentherm_dhw_state", STATE_ON, {})
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.opentherm_dhw_state")
    assert state
    assert state.state == STATE_ON

    await hass.helpers.entity_component.async_update_entity(
        "binary_sensor.opentherm_dhw_state"
    )

    state = hass.states.get("binary_sensor.opentherm_dhw_state")
    assert state
    assert state.state == STATE_OFF


async def test_adam_climate_binary_sensor_change(
    hass: HomeAssistant, mock_smile_adam: MagicMock, init_integration: MockConfigEntry
) -> None:
    """Test change of climate related binary_sensor entities."""
    entity_id = "binary_sensor.adam_plugwise_notification"
    # Test disabled_by default entry
    assert hass.states.get(entity_id) is None

    # Enable entry
    init_integration.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_update_entity(
        "binary_sensor.adam_plugwise_notification", disabled_by=None
    )
    await hass.config_entries.async_reload(init_integration.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state
    assert state.state == STATE_ON
    assert "warning_msg" in state.attributes
    assert "unreachable" in state.attributes["warning_msg"][0]
    assert not state.attributes.get("error_msg")
    assert not state.attributes.get("other_msg")
