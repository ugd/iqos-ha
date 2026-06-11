"""Select platform for IQOS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import IqosCoordinator
from .device import IqosData
from .entity import IqosEntity


@dataclass(frozen=True, kw_only=True)
class IqosSelectEntityDescription(SelectEntityDescription):
    """IQOS select entity description."""

    current_fn: Callable[[IqosData], str | None]
    select_fn: Callable[[IqosCoordinator, str], object]
    supported_fn: Callable[[IqosData], bool]


SELECT_DESCRIPTIONS: tuple[IqosSelectEntityDescription, ...] = (
    IqosSelectEntityDescription(
        key="brightness",
        translation_key="brightness",
        options=["low", "high"],
        current_fn=lambda data: data.brightness,
        select_fn=lambda coordinator, option: coordinator.async_set_brightness(option),
        supported_fn=lambda data: data.model.supports_brightness,
        entity_category=EntityCategory.CONFIG,
    ),
    IqosSelectEntityDescription(
        key="flexbattery_mode",
        translation_key="flexbattery_mode",
        options=["performance", "eco"],
        current_fn=lambda data: data.flexbattery_mode,
        select_fn=lambda coordinator, option: coordinator.async_set_flexbattery_mode(option),
        supported_fn=lambda data: data.model.supports_flexbattery,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up IQOS select entities."""
    coordinator: IqosCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    async_add_entities(
        IqosSelect(coordinator, description)
        for description in SELECT_DESCRIPTIONS
        if data and description.supported_fn(data)
    )


class IqosSelect(IqosEntity, SelectEntity):
    """IQOS select entity."""

    entity_description: IqosSelectEntityDescription

    def __init__(
        self,
        coordinator: IqosCoordinator,
        description: IqosSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_options = list(description.options or [])

    @property
    def current_option(self) -> str | None:
        """Return selected option."""
        if not self.coordinator.data:
            return None
        return self.entity_description.current_fn(self.coordinator.data)

    async def async_select_option(self, option: str) -> None:
        """Set selected option."""
        if option not in self._attr_options:
            raise HomeAssistantError(f"Unsupported IQOS option: {option}")
        await self.entity_description.select_fn(self.coordinator, option)

