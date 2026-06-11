"""Switch platform for IQOS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import IqosCoordinator
from .device import IqosData
from .entity import IqosEntity


@dataclass(frozen=True, kw_only=True)
class IqosSwitchEntityDescription(SwitchEntityDescription):
    """IQOS switch entity description."""

    value_fn: Callable[[IqosData], bool | None]
    set_fn: Callable[[IqosCoordinator, bool], object]
    supported_fn: Callable[[IqosData], bool]


SWITCH_DESCRIPTIONS: tuple[IqosSwitchEntityDescription, ...] = (
    IqosSwitchEntityDescription(
        key="flexpuff",
        translation_key="flexpuff",
        value_fn=lambda data: data.flexpuff,
        set_fn=lambda coordinator, enabled: coordinator.async_set_flexpuff(enabled),
        supported_fn=lambda data: data.model.supports_flexpuff,
        entity_category=EntityCategory.CONFIG,
    ),
    IqosSwitchEntityDescription(
        key="pause_mode",
        translation_key="pause_mode",
        value_fn=lambda data: data.pause_mode,
        set_fn=lambda coordinator, enabled: coordinator.async_set_pause_mode(enabled),
        supported_fn=lambda data: data.model.supports_flexbattery,
        entity_category=EntityCategory.CONFIG,
    ),
    IqosSwitchEntityDescription(
        key="autostart",
        translation_key="autostart",
        value_fn=lambda data: data.autostart,
        set_fn=lambda coordinator, enabled: coordinator.async_set_autostart(enabled),
        supported_fn=lambda data: data.model.supports_autostart,
        entity_category=EntityCategory.CONFIG,
    ),
    IqosSwitchEntityDescription(
        key="smartgesture",
        translation_key="smartgesture",
        value_fn=lambda data: data.smartgesture,
        set_fn=lambda coordinator, enabled: coordinator.async_set_smartgesture(enabled),
        supported_fn=lambda data: data.model.supports_smartgesture,
        entity_category=EntityCategory.CONFIG,
    ),
    IqosSwitchEntityDescription(
        key="vibration_heating_start",
        translation_key="vibration_heating_start",
        value_fn=lambda data: data.vibration_heating_start,
        set_fn=lambda coordinator, enabled: coordinator.async_set_vibration_setting(
            "heating_start", enabled
        ),
        supported_fn=lambda data: data.model.supports_vibration,
        entity_category=EntityCategory.CONFIG,
    ),
    IqosSwitchEntityDescription(
        key="vibration_starting_to_use",
        translation_key="vibration_starting_to_use",
        value_fn=lambda data: data.vibration_starting_to_use,
        set_fn=lambda coordinator, enabled: coordinator.async_set_vibration_setting(
            "starting_to_use", enabled
        ),
        supported_fn=lambda data: data.model.supports_vibration,
        entity_category=EntityCategory.CONFIG,
    ),
    IqosSwitchEntityDescription(
        key="vibration_puff_end",
        translation_key="vibration_puff_end",
        value_fn=lambda data: data.vibration_puff_end,
        set_fn=lambda coordinator, enabled: coordinator.async_set_vibration_setting(
            "puff_end", enabled
        ),
        supported_fn=lambda data: data.model.supports_vibration,
        entity_category=EntityCategory.CONFIG,
    ),
    IqosSwitchEntityDescription(
        key="vibration_manually_terminated",
        translation_key="vibration_manually_terminated",
        value_fn=lambda data: data.vibration_manually_terminated,
        set_fn=lambda coordinator, enabled: coordinator.async_set_vibration_setting(
            "manually_terminated", enabled
        ),
        supported_fn=lambda data: data.model.supports_vibration,
        entity_category=EntityCategory.CONFIG,
    ),
    IqosSwitchEntityDescription(
        key="vibration_charging_start",
        translation_key="vibration_charging_start",
        value_fn=lambda data: data.vibration_charging_start,
        set_fn=lambda coordinator, enabled: coordinator.async_set_vibration_setting(
            "charging_start", enabled
        ),
        supported_fn=lambda data: data.model.supports_charge_start_vibration,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up IQOS switches."""
    coordinator: IqosCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    async_add_entities(
        IqosSwitch(coordinator, description)
        for description in SWITCH_DESCRIPTIONS
        if data and description.supported_fn(data)
    )


class IqosSwitch(IqosEntity, SwitchEntity):
    """IQOS switch entity."""

    entity_description: IqosSwitchEntityDescription

    def __init__(
        self,
        coordinator: IqosCoordinator,
        description: IqosSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return the switch state."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_turn_on(self, **_kwargs: object) -> None:
        """Turn on the setting."""
        await self.entity_description.set_fn(self.coordinator, True)

    async def async_turn_off(self, **_kwargs: object) -> None:
        """Turn off the setting."""
        await self.entity_description.set_fn(self.coordinator, False)
