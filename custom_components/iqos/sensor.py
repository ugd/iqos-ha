"""Sensor platform for IQOS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfElectricPotential,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .coordinator import IqosCoordinator
from .device import IqosData
from .entity import IqosEntity


@dataclass(frozen=True, kw_only=True)
class IqosSensorEntityDescription(SensorEntityDescription):
    """IQOS sensor description."""

    value_fn: Callable[[IqosData], StateType]


SENSOR_DESCRIPTIONS: tuple[IqosSensorEntityDescription, ...] = (
    IqosSensorEntityDescription(
        key="battery_level",
        translation_key="battery_level",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery_level,
    ),
    IqosSensorEntityDescription(
        key="battery_voltage",
        translation_key="battery_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery_voltage,
    ),
    IqosSensorEntityDescription(
        key="total_smoking_count",
        translation_key="total_smoking_count",
        native_unit_of_measurement="puffs",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.total_smoking_count,
    ),
    IqosSensorEntityDescription(
        key="days_used",
        translation_key="days_used",
        native_unit_of_measurement=UnitOfTime.DAYS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.days_used,
    ),
    IqosSensorEntityDescription(
        key="rssi",
        translation_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.rssi,
    ),
    IqosSensorEntityDescription(
        key="product_number",
        translation_key="product_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.product_number,
    ),
    IqosSensorEntityDescription(
        key="holder_product_number",
        translation_key="holder_product_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.holder_product_number,
    ),
    IqosSensorEntityDescription(
        key="stick_firmware",
        translation_key="stick_firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.stick_firmware,
    ),
    IqosSensorEntityDescription(
        key="holder_firmware",
        translation_key="holder_firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.holder_firmware,
    ),
    IqosSensorEntityDescription(
        key="model_number",
        translation_key="model_number",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.device_info.model_number,
    ),
    IqosSensorEntityDescription(
        key="software_revision",
        translation_key="software_revision",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.device_info.software_revision,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up IQOS sensors."""
    coordinator: IqosCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        IqosSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    )


class IqosSensor(IqosEntity, SensorEntity):
    """IQOS sensor entity."""

    entity_description: IqosSensorEntityDescription

    def __init__(
        self,
        coordinator: IqosCoordinator,
        description: IqosSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Return the sensor state."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

