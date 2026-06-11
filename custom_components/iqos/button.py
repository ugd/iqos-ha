"""Button platform for IQOS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import IqosCoordinator
from .device import IqosData
from .entity import IqosEntity


@dataclass(frozen=True, kw_only=True)
class IqosButtonEntityDescription(ButtonEntityDescription):
    """IQOS button entity description."""

    press_fn: Callable[[IqosCoordinator], object]
    supported_fn: Callable[[IqosData], bool] = lambda _data: True


BUTTON_DESCRIPTIONS: tuple[IqosButtonEntityDescription, ...] = (
    IqosButtonEntityDescription(
        key="find_my_iqos",
        translation_key="find_my_iqos",
        device_class=ButtonDeviceClass.IDENTIFY,
        press_fn=lambda coordinator: coordinator.async_find_my_iqos(),
    ),
    IqosButtonEntityDescription(
        key="lock",
        translation_key="lock",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.async_lock(),
        supported_fn=lambda data: data.model.supports_device_lock,
    ),
    IqosButtonEntityDescription(
        key="unlock",
        translation_key="unlock",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.async_unlock(),
        supported_fn=lambda data: data.model.supports_device_lock,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up IQOS buttons."""
    coordinator: IqosCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    async_add_entities(
        IqosButton(coordinator, description)
        for description in BUTTON_DESCRIPTIONS
        if data and description.supported_fn(data)
    )


class IqosButton(IqosEntity, ButtonEntity):
    """IQOS button entity."""

    entity_description: IqosButtonEntityDescription

    def __init__(
        self,
        coordinator: IqosCoordinator,
        description: IqosButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Press the button."""
        await self.entity_description.press_fn(self.coordinator)

